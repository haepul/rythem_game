/* Download and decode before the count-in; schedule against the audio clock. */
(() => {
  class RhythmAudio {
    constructor() {
      this.status = 'idle'; this.error = ''; this.progress = 0;
      this.context = null; this.buffer = null; this.source = null;
      this.position = 0; this.startedAt = 0; this._paused = true;
      this._volume = 0.8; this.generation = 0; this.url = '';
      this.inputEnabled = false; this.inputEvents = []; this.heldKeys = new Set();
      this.pointers = new Map(); this.inputCanvas = null; this.savedTouchAction = '';
    }
    unlock() {
      const Context = window.AudioContext || window.webkitAudioContext;
      if (!this.context) {
        this.context = new Context({latencyHint: 'interactive'});
        this.gain = this.context.createGain();
        this.gain.connect(this.context.destination);
        this.gain.gain.value = this._volume;
      }
      this.context.resume().catch(error => { this.error = error.message; });
    }
    async prepare(url) {
      const generation = ++this.generation;
      this.pause(); this.position = 0; this.error = ''; this.progress = 0;
      this.controller?.abort();
      const controller = new AbortController();
      this.controller = controller;
      this.status = 'loading';
      const timeout = setTimeout(() => controller.abort(), 120000);
      try {
        this.unlock();
        if (this.url !== url || !this.buffer) {
          this.buffer = null;
          const response = await fetch(url, {signal: controller.signal});
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const size = Number(response.headers.get('content-length'));
          const reader = response.body.getReader();
          const chunks = []; let loaded = 0;
          while (true) {
            const {done, value} = await reader.read();
            if (done) break;
            if (generation !== this.generation) return;
            chunks.push(value); loaded += value.byteLength;
            this.progress = size > 0 ? Math.min(0.85, loaded / size * 0.85) : 0;
          }
          if (generation !== this.generation) return;
          const data = new Uint8Array(loaded); let cursor = 0;
          for (const chunk of chunks) { data.set(chunk, cursor); cursor += chunk.byteLength; }
          this.status = 'decoding'; this.progress = 0.9;
          const buffer = await this.context.decodeAudioData(data.buffer);
          if (generation !== this.generation) return;
          this.buffer = buffer; this.url = url;
        }
        if (generation !== this.generation) return;
        this.progress = 1; this.status = 'ready';
      } catch (error) {
        if (generation === this.generation) {
          this.error = error.name === 'AbortError' ? '다운로드 시간이 초과되었습니다' : error.message;
          this.status = 'error';
        }
      } finally { clearTimeout(timeout); }
    }
    get duration() { return this.buffer?.duration || 0; }
    get paused() { return this._paused; }
    get currentTime() {
      if (this._paused) return this.position;
      // currentTime is the render head, ahead of the sound at the output device.
      // Use the output timestamp to put the judgement line on the audible beat.
      let audible = this.context.currentTime;
      if (this.context.state === 'running') {
        const stamp = this.context.getOutputTimestamp?.();
        if (stamp && stamp.performanceTime > 0 && stamp.contextTime > 0) {
          audible = Math.min(audible, stamp.contextTime +
            Math.max(0, performance.now() - stamp.performanceTime) / 1000);
        } else {
          audible -= this.context.outputLatency || this.context.baseLatency || 0;
        }
      }
      return audible - this.startedAt;
    }
    inputClock() { return {now: performance.now(), song: this.currentTime}; }
    eventTime(event, clock = this.inputClock()) {
      let stamp = Number(event.timeStamp);
      // Older WebKit versions may expose epoch timestamps instead of DOM high-resolution time.
      if (stamp > 1e12 && Number.isFinite(performance.timeOrigin)) stamp -= performance.timeOrigin;
      const age = Number.isFinite(stamp) ? Math.max(0, clock.now - stamp) / 1000 : 0;
      return clock.song - (this._paused ? 0 : age);
    }
    queueInput(event) {
      this.inputEvents.push(event);
      // Preserve release/cancel edges even if a suspended tab accumulates pointer motion.
      if (this.inputEvents.length > 4096) {
        const oldMotion = this.inputEvents.findIndex(item => item[0] === 'pointer' && item[1] === 'move');
        if (oldMotion >= 0) this.inputEvents.splice(oldMotion, 1);
      }
    }
    setInputCanvas(canvas) {
      if (canvas === this.inputCanvas) return;
      if (this.inputCanvas) this.inputCanvas.style.touchAction = this.savedTouchAction;
      this.inputCanvas = canvas;
      if (canvas) {
        this.savedTouchAction = canvas.style.touchAction;
        canvas.style.touchAction = 'none';
      }
    }
    setInputEnabled(enabled) {
      enabled = Boolean(enabled);
      if (enabled === this.inputEnabled) return;
      this.clearInput();
      this.inputEnabled = enabled;
      this.setInputCanvas(enabled ? document.getElementById('canvas') : null);
    }
    recordKey(event, down) {
      if (!this.inputEnabled || !['KeyD', 'KeyF', 'KeyJ', 'KeyK', 'Space'].includes(event.code)) return;
      if (event.code === 'Space' && event.cancelable) event.preventDefault();
      if (down && (event.repeat || this.heldKeys.has(event.code))) return;
      if (!down && !this.heldKeys.has(event.code)) return;
      if (down) this.heldKeys.add(event.code); else this.heldKeys.delete(event.code);
      this.queueInput(['key', down ? 'down' : 'up', event.code, this.eventTime(event)]);
    }
    pointerPosition(event, canvas) {
      const rect = canvas.getBoundingClientRect();
      if (!(rect.width > 0 && rect.height > 0)) return null;
      return [(event.clientX - rect.left) * 800 / rect.width,
              (event.clientY - rect.top) * 480 / rect.height];
    }
    recordPointer(event, action) {
      if (!this.inputEnabled || !['touch', 'pen'].includes(event.pointerType)) return;
      let pointer = this.pointers.get(event.pointerId);
      if (action === 'down') {
        if (pointer) return;
        const canvas = document.getElementById('canvas');
        if (!canvas || !(event.target === canvas || event.composedPath?.().includes(canvas))) return;
        const position = this.pointerPosition(event, canvas);
        if (!position) return;
        this.setInputCanvas(canvas);
        pointer = {canvas, x: position[0], y: position[1]};
        this.pointers.set(event.pointerId, pointer);
        try { canvas.setPointerCapture(event.pointerId); } catch (_) { /* Window listeners still track it. */ }
      }
      if (!pointer) return;
      if (event.cancelable) event.preventDefault();
      const clock = this.inputClock();
      let samples = action === 'move' ? Array.from(event.getCoalescedEvents?.() || []) : [];
      const last = samples[samples.length - 1];
      if (!last || last.timeStamp !== event.timeStamp || last.clientX !== event.clientX || last.clientY !== event.clientY) {
        samples.push(event);
      }
      for (const sample of samples) {
        const position = this.pointerPosition(sample, pointer.canvas);
        if (position && Number.isFinite(position[0]) && Number.isFinite(position[1])) {
          [pointer.x, pointer.y] = position;
        }
        this.queueInput(['pointer', action, event.pointerId, pointer.x, pointer.y, this.eventTime(sample, clock)]);
      }
      if (action === 'up' || action === 'cancel') {
        this.pointers.delete(event.pointerId);
        this.releasePointer(pointer.canvas, event.pointerId);
      }
    }
    releasePointer(canvas, id) {
      try { canvas.releasePointerCapture(id); } catch (_) { /* It may already have been released. */ }
    }
    cancelPointer(id) {
      const pointer = this.pointers.get(id);
      if (!pointer) return;
      this.queueInput(['pointer', 'cancel', id, pointer.x, pointer.y, this.currentTime]);
      this.pointers.delete(id);
      this.releasePointer(pointer.canvas, id);
    }
    cancelHeldInput() {
      const when = this.currentTime;
      for (const code of this.heldKeys) this.queueInput(['key', 'up', code, when]);
      this.heldKeys.clear();
      for (const id of Array.from(this.pointers.keys())) this.cancelPointer(id);
    }
    drainInput() {
      const events = this.inputEvents;
      this.inputEvents = [];
      // Keyboard and coalesced pointer samples can arrive in separate, delayed batches.
      events.sort((a, b) => a[a.length - 1] - b[b.length - 1]);
      return JSON.stringify(events);
    }
    drainKeys() {
      // Legacy lane-event shape for callers that have enabled the input bridge.
      const lanes = {KeyD: 0, KeyF: 1, KeyJ: 2, KeyK: 3};
      return JSON.stringify(JSON.parse(this.drainInput())
        .filter(event => event[0] === 'key' && lanes[event[2]] !== undefined)
        .map(event => [event[1], lanes[event[2]], event[3]]));
    }
    clearInput() {
      this.inputEvents = []; this.heldKeys.clear();
      const pointers = Array.from(this.pointers.entries());
      this.pointers.clear();
      for (const [id, pointer] of pointers) this.releasePointer(pointer.canvas, id);
    }
    clearKeys() { this.clearInput(); }
    get ended() { return !!this.buffer && this.currentTime >= this.duration; }
    get volume() { return this._volume; }
    set volume(value) {
      this._volume = Math.max(0, Math.min(1, value));
      if (this.gain) this.gain.gain.value = this._volume;
    }
    get unlocked() { return this.context?.state === 'running'; }
    play(delay = 0) {
      if (!this.buffer || !this._paused || !this.unlocked) return false;
      const position = this.position;
      const wait = Math.max(delay, -position, 0);
      const offset = Math.max(0, position);
      if (offset >= this.duration) return false;
      this.source = this.context.createBufferSource();
      this.source.buffer = this.buffer;
      this.source.connect(this.gain);
      const startAt = this.context.currentTime + wait;
      this.startedAt = startAt - offset;
      this.source.start(startAt, offset);
      this._paused = false;
      return true;
    }
    pause() {
      this.position = this.currentTime;
      this._paused = true;
      if (this.source) {
        try { this.source.stop(); } catch (_) { /* already stopped */ }
        this.source.disconnect(); this.source = null;
      }
    }
    cancel() {
      ++this.generation; this.controller?.abort(); this.pause();
      this.status = 'idle';
    }
  }
  window.rhythmAudio = new RhythmAudio();
  window.addEventListener('keydown', event => window.rhythmAudio.recordKey(event, true));
  window.addEventListener('keyup', event => window.rhythmAudio.recordKey(event, false));
  window.addEventListener('blur', () => window.rhythmAudio.cancelHeldInput());
  for (const action of ['down', 'move', 'up', 'cancel']) {
    window.addEventListener(`pointer${action}`, event => window.rhythmAudio.recordPointer(event, action), {passive: false});
  }
  window.addEventListener('lostpointercapture', event => window.rhythmAudio.cancelPointer(event.pointerId));
  // Native DOM gestures unlock audio even when Python handles the click later.
  for (const event of ['pointerdown', 'touchend', 'keydown']) {
    window.addEventListener(event, () => window.rhythmAudio.unlock(), {passive: true});
  }
})();
