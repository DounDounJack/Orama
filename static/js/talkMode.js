// static/js/talkMode.js
//
// órama voice assistant: talk mode. A full-window voice screen for the
// current chat. You speak, it's turned into text (the speech-to-text set in
// Settings → Speech), sent as a normal chat message, and the reply is read
// aloud in the active persona's voice as it streams in. Then it listens
// again.
//
//   Hold Space (or hold the circle) to talk. Tap Space while it's thinking or
//   speaking to cut it off. "Hands-free" listens on its own and notices when
//   you stop talking. Esc closes.

const $ = (id) => document.getElementById(id);

const MIME_TYPES = ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus', 'audio/ogg'];
const HF_START_LEVEL = 0.035;   // hands-free: loudness that counts as speech
const HF_START_MS = 160;        // ...for this long
const HF_SILENCE_MS = 1100;     // stop after this much quiet
const MAX_TURN_MS = 30000;      // never record longer than this
const MIN_TURN_MS = 350;        // ignore taps shorter than this

let _open = false;
let _state = 'idle';            // idle | listening | transcribing | thinking | speaking
let _handsFree = false;
let _sttProvider = 'disabled';
let _stream = null;
let _recorder = null;
let _chunks = [];
let _mime = '';
let _recStart = 0;
let _recognition = null;
let _browserText = '';
let _audioCtx = null;
let _analyser = null;
let _vadTimer = null;
let _prevAutoPlay = null;
let _turnToken = 0;
let _maxTimer = null;

// ── UI ──

function _ensureUI() {
  if ($('talk-mode')) return;
  const el = document.createElement('div');
  el.id = 'talk-mode';
  el.className = 'talk-mode hidden';
  el.setAttribute('role', 'dialog');
  el.setAttribute('aria-modal', 'true');
  el.setAttribute('aria-label', 'Talk mode');
  el.innerHTML = `
    <button type="button" class="talk-close" id="talk-close" aria-label="Close talk mode">&#x2716;</button>
    <div class="talk-center">
      <button type="button" class="talk-orb" id="talk-orb" aria-label="Hold to talk"><span class="talk-orb-core"></span></button>
      <div class="talk-status" id="talk-status" aria-live="polite">Hold Space to talk</div>
      <div class="talk-heard" id="talk-heard"></div>
      <div class="talk-persona" id="talk-persona"></div>
    </div>
    <div class="talk-controls" role="group" aria-label="How to talk">
      <button type="button" class="talk-mode-btn active" id="talk-ptt" aria-pressed="true">Hold Space to talk</button>
      <button type="button" class="talk-mode-btn" id="talk-hf" aria-pressed="false">Hands-free</button>
    </div>`;
  document.body.appendChild(el);

  $('talk-close').addEventListener('click', close);
  $('talk-ptt').addEventListener('click', () => _setHandsFree(false));
  $('talk-hf').addEventListener('click', () => _setHandsFree(true));

  const orb = $('talk-orb');
  orb.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    if (_interruptIfBusy()) { if (!_handsFree) _startListening(); return; }
    if (!_handsFree) _startListening();
  });
  orb.addEventListener('pointerup', () => { if (!_handsFree && _state === 'listening') _stopListening(); });
  orb.addEventListener('pointerleave', () => { if (!_handsFree && _state === 'listening') _stopListening(); });
}

function _setState(state, text) {
  _state = state;
  const root = $('talk-mode');
  if (root) root.dataset.state = state;
  if (text !== undefined) _status(text);
}

function _status(text) {
  const s = $('talk-status');
  if (s) s.textContent = text;
}

function _idleText() {
  return _handsFree ? 'Listening… just start talking' : 'Hold Space to talk';
}

function _syncPersona() {
  const p = $('talk-persona');
  if (!p) return;
  let v = null;
  try { v = window.oramaGetActiveVoice ? window.oramaGetActiveVoice() : null; } catch (_) {}
  let name = '';
  try { name = window.presetsModule?.getCharacterName?.() || ''; } catch (_) {}
  const who = (v && v.name) || name;
  const parts = [];
  if (who) parts.push(who);
  if (v && v.voice) parts.push(v.voice);
  p.textContent = parts.join(' · ');
}

function _setHandsFree(on) {
  _handsFree = !!on;
  $('talk-ptt')?.classList.toggle('active', !_handsFree);
  $('talk-hf')?.classList.toggle('active', _handsFree);
  $('talk-ptt')?.setAttribute('aria-pressed', String(!_handsFree));
  $('talk-hf')?.setAttribute('aria-pressed', String(_handsFree));
  $('talk-orb')?.setAttribute('aria-label', _handsFree ? 'Tap to interrupt' : 'Hold to talk');
  try { localStorage.setItem('orama-talk-handsfree', _handsFree ? '1' : '0'); } catch (_) {}
  if (_state === 'listening' && !_handsFree) _cancelListening();
  if (_state === 'idle') {
    _status(_idleText());
    if (_handsFree) _startVad(); else _stopVad();
  }
}

// ── speech-to-text ──

async function _refreshStt() {
  try {
    const res = await fetch('/api/stt/stats', { credentials: 'same-origin' });
    const data = await res.json();
    _sttProvider = data.provider || 'disabled';
  } catch (_) {
    _sttProvider = 'disabled';
  }
  return _sttProvider;
}

function _sttProblem() {
  if (_sttProvider === 'disabled') {
    return 'Speech-to-text is off. Turn it on in Settings → Speech.';
  }
  if (_sttProvider === 'browser' && !(window.SpeechRecognition || window.webkitSpeechRecognition)) {
    return "This window can't use the browser's speech recognition. In Settings → Speech, set speech-to-text to Local (Whisper).";
  }
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    return 'The microphone is not available here.';
  }
  return '';
}

async function _ensureMic() {
  if (_stream && _stream.getAudioTracks().some(t => t.readyState === 'live')) return _stream;
  _stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
  });
  try {
    const Ctx = window.AudioContext || window.webkitAudioContext;
    _audioCtx = new Ctx();
    const src = _audioCtx.createMediaStreamSource(_stream);
    _analyser = _audioCtx.createAnalyser();
    _analyser.fftSize = 1024;
    src.connect(_analyser);
  } catch (_) {
    _analyser = null;
  }
  return _stream;
}

function _releaseMic() {
  _stopVad();
  if (_stream) _stream.getTracks().forEach(t => t.stop());
  _stream = null;
  if (_audioCtx) { try { _audioCtx.close(); } catch (_) {} }
  _audioCtx = null;
  _analyser = null;
}

function _level() {
  if (!_analyser) return 0;
  const buf = new Float32Array(_analyser.fftSize);
  _analyser.getFloatTimeDomainData(buf);
  let sum = 0;
  for (let i = 0; i < buf.length; i++) sum += buf[i] * buf[i];
  return Math.sqrt(sum / buf.length);
}

function _pickMime() {
  if (typeof MediaRecorder === 'undefined') return '';
  for (const m of MIME_TYPES) {
    try { if (MediaRecorder.isTypeSupported(m)) return m; } catch (_) {}
  }
  return '';
}

function _ext(mime) {
  if (mime.includes('mp4')) return 'm4a';
  if (mime.includes('ogg')) return 'ogg';
  return 'webm';
}

async function _startListening() {
  if (!_open || _state === 'listening') return;
  const problem = _sttProblem();
  if (problem) { _setState('idle', problem); return; }
  try {
    await _ensureMic();
  } catch (e) {
    const msg = e && e.name === 'NotAllowedError'
      ? 'Microphone access was blocked. Allow it for órama, then try again.'
      : (e && e.name === 'NotFoundError' ? 'No microphone found.' : 'Microphone error: ' + (e?.message || e));
    _setState('idle', msg);
    return;
  }
  if (!_open) return;

  $('talk-heard').textContent = '';
  _recStart = Date.now();
  clearTimeout(_maxTimer);
  _maxTimer = setTimeout(() => { if (_state === 'listening') _stopListening(); }, MAX_TURN_MS);

  if (_sttProvider === 'browser') {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    _browserText = '';
    _recognition = new SR();
    _recognition.continuous = true;
    _recognition.interimResults = true;
    _recognition.lang = navigator.language || '';
    _recognition.onresult = (ev) => {
      let finalText = '';
      let interim = '';
      for (let i = 0; i < ev.results.length; i++) {
        if (ev.results[i].isFinal) finalText += ev.results[i][0].transcript + ' ';
        else interim += ev.results[i][0].transcript;
      }
      _browserText = finalText;
      $('talk-heard').textContent = (finalText + interim).trim();
    };
    _recognition.onerror = (ev) => console.warn('talk mode speech recognition:', ev.error);
    try { _recognition.start(); } catch (_) {}
    _setState('listening', 'Listening…');
    return;
  }

  _mime = _pickMime();
  _chunks = [];
  try {
    _recorder = _mime ? new MediaRecorder(_stream, { mimeType: _mime }) : new MediaRecorder(_stream);
    _mime = _recorder.mimeType || _mime || 'audio/webm';
  } catch (e) {
    _setState('idle', 'Recording is not supported here: ' + (e?.message || e));
    return;
  }
  _recorder.ondataavailable = (ev) => { if (ev.data && ev.data.size) _chunks.push(ev.data); };
  _recorder.start();
  _setState('listening', 'Listening…');
}

function _cancelListening() {
  clearTimeout(_maxTimer);
  if (_recognition) { try { _recognition.abort(); } catch (_) {} _recognition = null; }
  if (_recorder && _recorder.state !== 'inactive') {
    _recorder.ondataavailable = null;
    _recorder.onstop = null;
    try { _recorder.stop(); } catch (_) {}
  }
  _recorder = null;
  _chunks = [];
  _setState('idle', _idleText());
}

async function _stopListening() {
  if (_state !== 'listening') return;
  clearTimeout(_maxTimer);
  const tooShort = Date.now() - _recStart < MIN_TURN_MS;

  if (_sttProvider === 'browser') {
    const rec = _recognition;
    _recognition = null;
    _setState('transcribing', 'Got it…');
    await new Promise((resolve) => {
      if (!rec) return resolve();
      rec.onend = resolve;
      try { rec.stop(); } catch (_) { resolve(); }
      setTimeout(resolve, 1500);
    });
    const text = (_browserText || $('talk-heard').textContent || '').trim();
    return _handleTranscript(tooShort ? '' : text);
  }

  const rec = _recorder;
  _recorder = null;
  if (!rec) return _setState('idle', _idleText());
  const blob = await new Promise((resolve) => {
    rec.onstop = () => resolve(new Blob(_chunks, { type: _mime }));
    try { rec.stop(); } catch (_) { resolve(new Blob(_chunks, { type: _mime })); }
  });
  _chunks = [];
  if (tooShort || !blob.size) return _handleTranscript('');

  _setState('transcribing', 'Got it…');
  try {
    const fd = new FormData();
    fd.append('file', blob, `talk.${_ext(_mime)}`);
    const res = await fetch('/api/stt/transcribe', { method: 'POST', credentials: 'same-origin', body: fd });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail?.message || `HTTP ${res.status}`);
    }
    const data = await res.json();
    _handleTranscript((data.text || '').trim());
  } catch (e) {
    console.error('talk mode transcription failed', e);
    _setState('idle', "Couldn't turn that into text: " + e.message);
    if (_handsFree) setTimeout(() => { if (_open && _state === 'idle') _startVad(); }, 1500);
  }
}

// ── hands-free: notice speech and silence ──

function _startVad() {
  _stopVad();
  if (!_open || !_handsFree) return;
  if (_sttProblem()) { _status(_sttProblem()); return; }
  _ensureMic().then(() => {
    if (!_open || !_handsFree) return;
    let loudSince = 0;
    let quietSince = 0;
    _status(_idleText());
    _vadTimer = setInterval(() => {
      if (!_open || !_handsFree) return _stopVad();
      const lvl = _level();
      const now = Date.now();
      if (_state === 'idle') {
        if (lvl > HF_START_LEVEL) {
          if (!loudSince) loudSince = now;
          if (now - loudSince > HF_START_MS) { loudSince = 0; quietSince = 0; _startListening(); }
        } else {
          loudSince = 0;
        }
      } else if (_state === 'listening') {
        if (lvl < HF_START_LEVEL * 0.7) {
          if (!quietSince) quietSince = now;
          if (now - quietSince > HF_SILENCE_MS) { quietSince = 0; _stopListening(); }
        } else {
          quietSince = 0;
        }
      }
    }, 50);
  }).catch((e) => {
    _status(e && e.name === 'NotAllowedError'
      ? 'Microphone access was blocked. Allow it for órama, then try again.'
      : 'Microphone error: ' + (e?.message || e));
  });
}

function _stopVad() {
  if (_vadTimer) clearInterval(_vadTimer);
  _vadTimer = null;
}

// ── sending and the reply ──

function _chatBusy() {
  return !!window.__odysseusChatBusy;
}

function _ttsBusy() {
  const t = window.aiTTSManager;
  return !!(t && (t.isPlaying || t._processing || (t._queue && t._queue.length)));
}

function _waitFor(check, timeoutMs, everyMs = 150) {
  return new Promise((resolve) => {
    const start = Date.now();
    const tick = () => {
      if (!_open) return resolve(false);
      if (check()) return resolve(true);
      if (Date.now() - start > timeoutMs) return resolve(false);
      setTimeout(tick, everyMs);
    };
    tick();
  });
}

async function _handleTranscript(text) {
  if (!_open) return;
  if (!text) {
    _setState('idle', _handsFree ? _idleText() : "Didn't catch that. Hold Space and try again.");
    return;
  }
  $('talk-heard').textContent = `“${text}”`;
  const token = ++_turnToken;

  const input = $('message');
  const send = document.querySelector('.send-btn');
  if (!input || !send) { _setState('idle', "Couldn't find the chat box."); return; }

  // Let any earlier reply finish first.
  if (_chatBusy()) await _waitFor(() => !_chatBusy(), 60000);
  if (!_open || token !== _turnToken) return;

  input.value = text;
  input.dispatchEvent(new Event('input', { bubbles: true }));
  _setState('thinking', 'Thinking…');
  send.click();

  const started = await _waitFor(() => _chatBusy(), 4000, 100);
  if (!_open || token !== _turnToken) return;
  if (!started && input.value.trim() === text) {
    _setState('idle', "Couldn't send. Check that a model is picked for this chat.");
    return;
  }

  // While the reply streams in, chat.js reads it aloud sentence by sentence
  // (TTS auto-play is switched on while talk mode is open).
  let spoke = false;
  await _waitFor(() => {
    if (_ttsBusy() && !spoke) { spoke = true; _setState('speaking', 'Speaking… (Space to interrupt)'); }
    return !_chatBusy();
  }, 300000);
  if (!_open || token !== _turnToken) return;

  // Give the last sentence a moment to be queued, then wait for it to finish.
  await _waitFor(() => _ttsBusy(), 1200, 100);
  if (_ttsBusy()) {
    _setState('speaking', 'Speaking… (Space to interrupt)');
    await _waitFor(() => !_ttsBusy(), 300000, 200);
  }
  if (!_open || token !== _turnToken) return;

  const ttsOn = !!window.aiTTSManager?.available;
  _setState('idle', ttsOn ? _idleText() : `${_idleText()} (speech is off, so the reply is in the chat)`);
  if (_handsFree) setTimeout(() => { if (_open && _state === 'idle') _startVad(); }, 300);
}

/** Stop speaking / generating. Returns true if something was interrupted. */
function _interruptIfBusy() {
  if (_state !== 'thinking' && _state !== 'speaking' && !_ttsBusy()) return false;
  _turnToken++;
  try { window.aiTTSManager?.stop(); } catch (_) {}
  if (_chatBusy()) {
    const send = document.querySelector('.send-btn');
    const input = $('message');
    // In streaming mode an empty box turns the send button into Stop.
    if (send && send.dataset.mode === 'streaming' && input && !input.value.trim()) send.click();
  }
  _setState('idle', _idleText());
  if (_handsFree) setTimeout(() => { if (_open && _state === 'idle') _startVad(); }, 400);
  return true;
}

// ── keyboard ──

function _onKeyDown(e) {
  if (!_open) return;
  if (e.key === 'Escape') { e.preventDefault(); e.stopPropagation(); close(); return; }
  if (e.code !== 'Space' && e.key !== ' ') return;
  e.preventDefault();
  e.stopPropagation();
  if (e.repeat) return;
  if (_interruptIfBusy()) { if (!_handsFree) _startListening(); return; }
  if (!_handsFree && _state === 'idle') _startListening();
}

function _onKeyUp(e) {
  if (!_open) return;
  if (e.code !== 'Space' && e.key !== ' ') return;
  e.preventDefault();
  e.stopPropagation();
  if (!_handsFree && _state === 'listening') _stopListening();
}

// ── open / close ──

export async function open() {
  _ensureUI();
  if (_open) return;
  _open = true;
  const root = $('talk-mode');
  root.classList.remove('hidden');
  document.addEventListener('keydown', _onKeyDown, true);
  document.addEventListener('keyup', _onKeyUp, true);
  try { document.activeElement?.blur?.(); } catch (_) {}

  const tts = window.aiTTSManager;
  if (tts) {
    _prevAutoPlay = tts.autoPlay;
    try { await tts.checkAvailability(); } catch (_) {}
    tts.autoPlay = true;
  }

  let hf = false;
  try { hf = localStorage.getItem('orama-talk-handsfree') === '1'; } catch (_) {}
  _handsFree = hf;
  _setHandsFree(hf);
  _syncPersona();
  $('talk-heard').textContent = '';
  _setState('idle', 'Getting ready…');
  await _refreshStt();
  if (!_open) return;
  const problem = _sttProblem();
  _setState('idle', problem || _idleText());
  if (!problem && _handsFree) _startVad();
}

export function close() {
  if (!_open) return;
  _open = false;
  _turnToken++;
  _cancelListening();
  _releaseMic();
  try { window.aiTTSManager?.stop(); } catch (_) {}
  if (window.aiTTSManager && _prevAutoPlay !== null) window.aiTTSManager.autoPlay = _prevAutoPlay;
  _prevAutoPlay = null;
  document.removeEventListener('keydown', _onKeyDown, true);
  document.removeEventListener('keyup', _onKeyUp, true);
  $('talk-mode')?.classList.add('hidden');
  $('message')?.focus();
}

export function isOpen() { return _open; }

function _init() {
  const btn = $('talk-mode-btn');
  if (btn) btn.addEventListener('click', () => open());
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', _init);
else _init();

const talkModeModule = { open, close, isOpen };
try { window.talkModeModule = talkModeModule; } catch (_) {}
export default talkModeModule;
