// Browser input contract tests; run with: node --test tests/test_browser_input.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const source = fs.readFileSync(path.join(__dirname, '..', 'audio_player.js'), 'utf8');

function assertEvents(actual, expected) {
  assert.equal(actual.length, expected.length);
  actual.forEach((event, index) => {
    assert.deepEqual(event.slice(0, -1), expected[index].slice(0, -1));
    assert.ok(Math.abs(event.at(-1) - expected[index].at(-1)) < 1e-9);
  });
}

function harness() {
  let now = 10000;
  const listeners = new Map();
  const captured = new Set();
  const canvas = {
    style: {touchAction: 'pan-y'},
    getBoundingClientRect: () => ({left: 100, top: 20, width: 400, height: 240}),
    setPointerCapture: id => captured.add(id),
    releasePointerCapture(id) {
      captured.delete(id);
      dispatch('lostpointercapture', {pointerId: id});
    },
  };
  class AudioContext {
    constructor() { this.state = 'running'; this.currentTime = now / 1000; }
    createGain() { return {gain: {value: 0}, connect() {}}; }
    resume() { return Promise.resolve(); }
    getOutputTimestamp() { return {performanceTime: now, contextTime: this.currentTime}; }
    createBufferSource() {
      return {connect() {}, disconnect() {}, stop() {}, start(...args) { this.started = args; }};
    }
  }
  const window = {
    AudioContext,
    addEventListener(type, listener) {
      if (!listeners.has(type)) listeners.set(type, []);
      listeners.get(type).push(listener);
    },
  };
  function dispatch(type, properties = {}) {
    const event = {
      timeStamp: now, cancelable: true, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; },
      ...properties,
    };
    for (const listener of listeners.get(type) || []) listener(event);
    return event;
  }
  vm.runInNewContext(source, {
    window,
    document: {getElementById: id => id === 'canvas' ? canvas : null},
    performance: {now: () => now, timeOrigin: 1700000000000},
    setTimeout, clearTimeout, AbortController,
  });
  const audio = window.rhythmAudio;
  audio.unlock();
  audio.buffer = {duration: 300};
  audio.startedAt = 5;
  audio._paused = false;
  function pointer(action, id, x, y, extra = {}) {
    return dispatch(`pointer${action}`, {
      pointerId: id, pointerType: 'touch', target: canvas,
      clientX: x, clientY: y, ...extra,
    });
  }
  return {
    audio, canvas, captured, dispatch, pointer,
    enable() { audio.setInputEnabled(true); },
    drain() { return JSON.parse(audio.drainInput()); },
    advance(ms) { now += ms; audio.context.currentTime = now / 1000; },
  };
}

test('lane and Space edges retain timestamps, suppress repeat, and preserve simultaneous chords', () => {
  const h = harness(); h.enable();
  h.dispatch('keydown', {code: 'KeyD', timeStamp: 9900});
  h.dispatch('keydown', {code: 'KeyD', timeStamp: 9901, repeat: true});
  h.dispatch('keydown', {code: 'KeyD', timeStamp: 9902});
  h.dispatch('keydown', {code: 'KeyK', timeStamp: 9900});
  const space = h.dispatch('keydown', {code: 'Space', timeStamp: 9920});
  const spaceRepeat = h.dispatch('keydown', {code: 'Space', timeStamp: 9921, repeat: true});
  h.dispatch('keyup', {code: 'KeyD', timeStamp: 9960});
  h.dispatch('keyup', {code: 'KeyD', timeStamp: 9961});
  assert.equal(space.defaultPrevented, true);
  assert.equal(spaceRepeat.defaultPrevented, true);
  assert.deepEqual(h.drain(), [
    ['key', 'down', 'KeyD', 4.9], ['key', 'down', 'KeyK', 4.9],
    ['key', 'down', 'Space', 4.92], ['key', 'up', 'KeyD', 4.96],
  ]);
  assert.deepEqual(h.drain(), []);
});

test('menu input is untouched; enabling and disabling update only the game canvas', () => {
  const h = harness();
  assert.equal(h.dispatch('keydown', {code: 'Space'}).defaultPrevented, false);
  assert.equal(h.pointer('down', 1, 200, 100).defaultPrevented, false);
  assert.deepEqual(h.drain(), []);
  assert.equal(h.canvas.style.touchAction, 'pan-y');
  h.enable();
  assert.equal(h.canvas.style.touchAction, 'none');
  const otherCanvas = {id: 'canvas3d'};
  assert.equal(h.pointer('down', 2, 200, 100, {target: otherCanvas}).defaultPrevented, false);
  assert.deepEqual(h.drain(), []);
  h.audio.setInputEnabled(false);
  assert.equal(h.canvas.style.touchAction, 'pan-y');
  assert.equal(h.dispatch('keydown', {code: 'Space'}).defaultPrevented, false);
});

test('multitouch keeps independent ids, scaled coordinates, capture, and out-of-canvas motion', () => {
  const h = harness(); h.enable();
  h.pointer('down', 7, 150, 200, {timeStamp: 9970});
  h.pointer('down', 8, 450, 200, {timeStamp: 9975});
  assert.deepEqual([...h.captured], [7, 8]);
  const move = h.pointer('move', 7, 80, 80, {target: {}, timeStamp: 9990});
  h.pointer('up', 8, 450, 200, {target: {}, timeStamp: 9995});
  assert.equal(move.defaultPrevented, true);
  assert.deepEqual([...h.captured], [7]);
  assert.deepEqual(h.drain(), [
    ['pointer', 'down', 7, 100, 360, 4.97],
    ['pointer', 'down', 8, 700, 360, 4.975],
    ['pointer', 'move', 7, -40, 120, 4.99],
    ['pointer', 'up', 8, 700, 360, 4.995],
  ]);
});

test('coalesced motion and separate keyboard batches drain in original event-time order', () => {
  const h = harness(); h.enable();
  h.pointer('down', 1, 200, 230, {timeStamp: 9000});
  h.dispatch('keydown', {code: 'KeyF', timeStamp: 9060});
  h.pointer('move', 1, 200, 180, {
    timeStamp: 9100,
    getCoalescedEvents: () => [
      {clientX: 200, clientY: 220, timeStamp: 9040},
      {clientX: 200, clientY: 200, timeStamp: 9070},
      {clientX: 200, clientY: 180, timeStamp: 9100},
    ],
  });
  assertEvents(h.drain(), [
    ['pointer', 'down', 1, 200, 420, 4],
    ['pointer', 'move', 1, 200, 400, 4.04],
    ['key', 'down', 'KeyF', 4.06],
    ['pointer', 'move', 1, 200, 360, 4.07],
    ['pointer', 'move', 1, 200, 320, 4.1],
  ]);
});

test('delayed and epoch events keep their true timestamps instead of being clamped to a frame', () => {
  const h = harness(); h.enable();
  h.dispatch('keydown', {code: 'KeyD', timeStamp: 8000});
  h.dispatch('keydown', {code: 'KeyF', timeStamp: 1700000009000});
  assert.deepEqual(h.drain(), [['key', 'down', 'KeyD', 3], ['key', 'down', 'KeyF', 4]]);
});

test('input timestamps follow the audible output clock instead of the render head', () => {
  const h = harness(); h.enable();
  h.audio.context.getOutputTimestamp = () => ({performanceTime: 9950, contextTime: 9.8});
  h.dispatch('keydown', {code: 'KeyD', timeStamp: 9950});
  h.pointer('down', 1, 200, 200, {timeStamp: 9975});
  assertEvents(h.drain(), [
    ['key', 'down', 'KeyD', 4.8],
    ['pointer', 'down', 1, 200, 360, 4.825],
  ]);
});

test('unchanged enable calls preserve the queue; disabling clears held and stale input', () => {
  const h = harness(); h.enable();
  h.dispatch('keydown', {code: 'Space'});
  h.pointer('down', 1, 200, 200);
  h.audio.setInputEnabled(true);
  assert.equal(h.audio.inputEvents.length, 2);
  h.audio.setInputEnabled(false);
  assert.deepEqual(h.drain(), []);
  assert.equal(h.audio.heldKeys.size, 0);
  assert.equal(h.audio.pointers.size, 0);
  assert.equal(h.captured.size, 0);
  h.enable();
  h.pointer('move', 1, 200, 100);
  h.dispatch('keyup', {code: 'Space'});
  assert.deepEqual(h.drain(), []);
  h.dispatch('keydown', {code: 'Space'});
  assert.deepEqual(h.drain(), [['key', 'down', 'Space', 5]]);
});

test('pointercancel and lost capture end only the affected finger without ghost motion', () => {
  const h = harness(); h.enable();
  h.pointer('down', 1, 200, 200);
  h.pointer('down', 2, 300, 200);
  h.drain();
  h.pointer('cancel', 1, 200, 180);
  h.pointer('move', 1, 200, 100);
  h.dispatch('lostpointercapture', {pointerId: 2});
  h.pointer('up', 2, 300, 200);
  assert.deepEqual(h.drain(), [
    ['pointer', 'cancel', 1, 200, 320, 5],
    ['pointer', 'cancel', 2, 400, 360, 5],
  ]);
  assert.equal(h.audio.pointers.size, 0);
  assert.equal(h.captured.size, 0);
});

test('blur releases held keys and cancels all fingers so a later input is fresh', () => {
  const h = harness(); h.enable();
  h.dispatch('keydown', {code: 'KeyJ'});
  h.dispatch('keydown', {code: 'Space'});
  h.pointer('down', 3, 300, 200);
  h.drain();
  h.advance(50);
  h.dispatch('blur');
  assertEvents(h.drain(), [
    ['key', 'up', 'KeyJ', 5.05],
    ['key', 'up', 'Space', 5.05],
    ['pointer', 'cancel', 3, 400, 360, 5.05],
  ]);
  assert.equal(h.audio.heldKeys.size, 0);
  assert.equal(h.captured.size, 0);
  h.dispatch('keydown', {code: 'KeyJ'});
  assert.equal(h.drain().length, 1);
});

test('mouse pointers are never duplicated into the touch queue', () => {
  const h = harness(); h.enable();
  for (const action of ['down', 'move', 'up']) {
    const event = h.pointer(action, 1, 200, 200, {pointerType: 'mouse'});
    assert.equal(event.defaultPrevented, false);
  }
  assert.deepEqual(h.drain(), []);
  assert.equal(h.captured.size, 0);
});

test('pen motion uses the same timestamped input path as touch', () => {
  const h = harness(); h.enable();
  h.pointer('down', 10, 300, 200, {pointerType: 'pen'});
  h.pointer('move', 10, 300, 150, {pointerType: 'pen'});
  h.pointer('up', 10, 300, 150, {pointerType: 'pen'});
  assert.deepEqual(h.drain().map(event => event.slice(0, 3)), [
    ['pointer', 'down', 10], ['pointer', 'move', 10], ['pointer', 'up', 10],
  ]);
});

test('clearKeys compatibility alias clears new pointer state and legacy lane drain remains usable', () => {
  const h = harness(); h.enable();
  h.dispatch('keydown', {code: 'KeyK'});
  assert.deepEqual(JSON.parse(h.audio.drainKeys()), [['down', 3, 5]]);
  h.pointer('down', 1, 200, 200);
  h.audio.clearKeys();
  assert.deepEqual(h.drain(), []);
  assert.equal(h.audio.pointers.size, 0);
});

test('atomic audio source scheduling still starts at the requested future audio-clock time', () => {
  const h = harness();
  h.audio._paused = true;
  h.audio.position = -1.1;
  assert.equal(h.audio.play(), true);
  assert.deepEqual(Array.from(h.audio.source.started), [11.1, 0]);
  assert.equal(h.audio.startedAt, 11.1);
  assert.equal(h.audio.paused, false);
});
