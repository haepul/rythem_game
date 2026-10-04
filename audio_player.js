/* Download and decode before the count-in; schedule against the audio clock. */
(() => {
  class RhythmAudio {
    constructor() {
      this.status = 'idle'; this.error = ''; this.progress = 0;
      this.context = null; this.buffer = null; this.source = null;
      this.position = 0; this.startedAt = 0; this._paused = true;
      this._volume = 0.8; this.generation = 0; this.url = '';
      this.keyEvents = []; this.heldKeys = new Set();
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
    recordKey(event, down) {
      const lane = {KeyD: 0, KeyF: 1, KeyJ: 2, KeyK: 3}[event.code];
      if (lane === undefined || (down && (event.repeat || this.heldKeys.has(event.code)))) return;
      if (down) this.heldKeys.add(event.code); else this.heldKeys.delete(event.code);
      const age = Math.max(0, Math.min(1, (performance.now() - event.timeStamp) / 1000));
      const when = this.currentTime - (this._paused ? 0 : age);
      this.keyEvents.push([down ? 'down' : 'up', lane, when]);
      if (this.keyEvents.length > 256) this.keyEvents.shift();
    }
    drainKeys() {
      const events = this.keyEvents;
      this.keyEvents = [];
      return JSON.stringify(events);
    }
    clearKeys() { this.keyEvents = []; this.heldKeys.clear(); }
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
  window.addEventListener('blur', () => window.rhythmAudio.clearKeys());
  // Native DOM gestures unlock audio even when Python handles the click later.
  for (const event of ['pointerdown', 'touchend', 'keydown']) {
    window.addEventListener(event, () => window.rhythmAudio.unlock(), {passive: true});
  }
})();
