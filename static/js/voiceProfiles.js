// static/js/voiceProfiles.js
//
// órama voice assistant: the "Voice" tab in the persona window.
// A voice profile adds a speaking style (name, how it addresses you,
// formal/casual, short/chatty, humour, favourite phrases, words to avoid)
// and a voice + speed to a persona. The style settings are written into the
// persona's system prompt by the server (/api/voice/prompt).

let API_BASE = '';
let _enabled = false;        // does the persona in the form have a voice profile?
let _starters = [];
let _startersLoaded = false;
let _provider = 'disabled';
let _promptTimer = null;
let _promptSeq = 0;
let _phrases = [];
let _avoid = [];

const DEFAULTS = {
  address: '', formality: 50, length: 40, humour: 30,
  phrases: [], avoid: [], voice: '', speed: 1.0, auto_prompt: true, starter: '',
};

const $ = (id) => document.getElementById(id);

// ── reading / writing the form ──

function _readForm() {
  return {
    address: ($('voice-address')?.value || '').trim(),
    formality: parseInt($('voice-formality')?.value ?? 50, 10),
    length: parseInt($('voice-length')?.value ?? 40, 10),
    humour: parseInt($('voice-humour')?.value ?? 30, 10),
    phrases: [..._phrases],
    avoid: [..._avoid],
    voice: $('voice-voice')?.value || '',
    speed: parseFloat($('voice-speed')?.value || '1') || 1.0,
    auto_prompt: $('voice-auto-prompt') ? $('voice-auto-prompt').checked : true,
    starter: $('voice-starter')?.dataset.applied || '',
  };
}

function _writeForm(p) {
  const v = { ...DEFAULTS, ...(p || {}) };
  if ($('voice-address')) $('voice-address').value = v.address || '';
  if ($('voice-formality')) $('voice-formality').value = v.formality;
  if ($('voice-length')) $('voice-length').value = v.length;
  if ($('voice-humour')) $('voice-humour').value = v.humour;
  _phrases = [...(v.phrases || [])];
  _avoid = [...(v.avoid || [])];
  _renderChips('voice-phrases', _phrases);
  _renderChips('voice-avoid', _avoid);
  _setVoiceValue(v.voice || '');
  if ($('voice-speed')) $('voice-speed').value = String(v.speed || 1);
  _syncSpeedLabel();
  if ($('voice-auto-prompt')) $('voice-auto-prompt').checked = v.auto_prompt !== false;
  const starterSel = $('voice-starter');
  if (starterSel) {
    starterSel.dataset.applied = v.starter || '';
    starterSel.value = '';
  }
}

function _syncEnabledUI() {
  const panel = document.querySelector('[data-chartab-panel="voice"]');
  if (panel) panel.classList.toggle('voice-off', !_enabled);
  const off = $('voice-off-btn');
  if (off) off.style.display = _enabled ? '' : 'none';
}

function _syncSpeedLabel() {
  const s = $('voice-speed');
  const l = $('voice-speed-value');
  if (s && l) l.textContent = parseFloat(s.value).toFixed(2).replace(/0$/, '') + '×';
}

// ── chips (favourite phrases / words to avoid) ──

function _renderChips(containerId, list) {
  const box = $(containerId);
  if (!box) return;
  box.querySelectorAll('.voice-chip').forEach(c => c.remove());
  const input = box.querySelector('input');
  list.forEach((text, i) => {
    const chip = document.createElement('span');
    chip.className = 'voice-chip';
    chip.textContent = text;
    const x = document.createElement('button');
    x.type = 'button';
    x.className = 'voice-chip-x';
    x.setAttribute('aria-label', `Remove ${text}`);
    x.textContent = '×';
    x.addEventListener('click', () => {
      list.splice(i, 1);
      _renderChips(containerId, list);
      _changed();
    });
    chip.appendChild(x);
    box.insertBefore(chip, input);
  });
}

function _bindChipInput(containerId, getList, limit) {
  const box = $(containerId);
  const input = box?.querySelector('input');
  if (!input) return;
  const add = () => {
    const text = input.value.replace(/\s+/g, ' ').trim();
    if (!text) return;
    const list = getList();
    if (list.length >= limit) { input.value = ''; return; }
    if (!list.some(t => t.toLowerCase() === text.toLowerCase())) list.push(text);
    input.value = '';
    _renderChips(containerId, list);
    _changed();
  };
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || (e.key === ',' && containerId === 'voice-avoid')) {
      e.preventDefault();
      add();
    } else if (e.key === 'Backspace' && !input.value) {
      const list = getList();
      if (list.length) { list.pop(); _renderChips(containerId, list); _changed(); }
    }
  });
  input.addEventListener('blur', add);
  box.addEventListener('click', (e) => { if (e.target === box) input.focus(); });
}

// ── voices ──

function _setVoiceValue(value) {
  const sel = $('voice-voice');
  if (!sel) return;
  if (value && ![...sel.options].some(o => o.value === value)) {
    const opt = document.createElement('option');
    opt.value = value;
    opt.textContent = value;
    sel.appendChild(opt);
  }
  sel.value = value;
}

function _browserVoices() {
  return new Promise((resolve) => {
    if (!('speechSynthesis' in window)) { resolve([]); return; }
    const got = window.speechSynthesis.getVoices();
    if (got.length) { resolve(got); return; }
    const done = () => resolve(window.speechSynthesis.getVoices());
    window.speechSynthesis.addEventListener('voiceschanged', done, { once: true });
    setTimeout(done, 1500);
  });
}

async function _loadVoices() {
  const sel = $('voice-voice');
  const note = $('voice-tts-note');
  if (!sel) return;
  const keep = sel.value;
  let names = [];
  try {
    const res = await fetch(`${API_BASE}/api/voice/voices`, { credentials: 'same-origin' });
    const data = await res.json();
    _provider = data.provider || 'disabled';
    if (Array.isArray(data.voices)) {
      names = data.voices.map(v => ({ value: v, label: v }));
    } else {
      const voices = await _browserVoices();
      const lang = (navigator.language || 'en').slice(0, 2);
      voices.sort((a, b) => {
        const am = a.lang.startsWith(lang) ? 0 : 1;
        const bm = b.lang.startsWith(lang) ? 0 : 1;
        return am - bm || a.name.localeCompare(b.name);
      });
      names = voices.map(v => ({ value: v.name, label: `${v.name} (${v.lang})` }));
    }
  } catch (e) {
    console.warn('voice list failed', e);
  }
  sel.innerHTML = '';
  const def = document.createElement('option');
  def.value = '';
  def.textContent = 'Default voice (from Settings)';
  sel.appendChild(def);
  for (const n of names) {
    const opt = document.createElement('option');
    opt.value = n.value;
    opt.textContent = n.label;
    sel.appendChild(opt);
  }
  _setVoiceValue(keep);
  if (note) {
    note.textContent = _provider === 'disabled'
      ? 'Speech is off. Turn it on in Settings → Speech to hear this persona.'
      : '';
    note.style.display = note.textContent ? '' : 'none';
  }
}

// ── starter styles ──

async function _loadStarters() {
  const sel = $('voice-starter');
  if (!sel) return;
  try {
    const res = await fetch(`${API_BASE}/api/voice/starters`, { credentials: 'same-origin' });
    const data = await res.json();
    _starters = data.starters || [];
  } catch (e) {
    console.warn('voice starters failed', e);
    _starters = [];
  }
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = '';
  ph.textContent = 'Pick a starter style…';
  sel.appendChild(ph);
  for (const s of _starters) {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = `${s.name}: ${s.description}`;
    sel.appendChild(opt);
  }
  _startersLoaded = true;
}

function _applyStarter(id) {
  const s = _starters.find(x => x.id === id);
  if (!s) return;
  const nameInput = $('custom-character-name');
  const starterNames = _starters.map(x => x.name);
  if (nameInput && (!nameInput.value.trim() || starterNames.includes(nameInput.value.trim()))) {
    nameInput.value = s.name;
    nameInput.dispatchEvent(new Event('input', { bubbles: true }));
  }
  if ($('voice-name')) $('voice-name').value = nameInput ? nameInput.value : s.name;
  _writeForm(s.profile);
  const sel = $('voice-starter');
  if (sel) sel.dataset.applied = s.id;
  const temp = $('custom-temperature');
  if (temp && s.temperature != null) {
    temp.value = s.temperature;
    temp.dispatchEvent(new Event('input'));
  }
  _enabled = true;
  _syncEnabledUI();
  _refreshPrompt(true);
}

// ── prompt ──

function _changed() {
  _enabled = true;
  _syncEnabledUI();
  _refreshPrompt(false);
}

function _refreshPrompt(immediate) {
  clearTimeout(_promptTimer);
  _promptTimer = setTimeout(_writePrompt, immediate ? 0 : 250);
}

async function _writePrompt() {
  const preview = $('voice-prompt-preview');
  const profile = _readForm();
  const name = ($('custom-character-name')?.value || '').trim();
  const seq = ++_promptSeq;
  try {
    const res = await fetch(`${API_BASE}/api/voice/prompt`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, profile }),
    });
    if (!res.ok) return;
    const { prompt } = await res.json();
    if (seq !== _promptSeq) return;
    if (preview) preview.textContent = prompt;
    if (_enabled && profile.auto_prompt) {
      const promptInput = $('custom-system-prompt');
      if (promptInput) promptInput.value = prompt;
    }
  } catch (e) {
    console.warn('voice prompt failed', e);
  }
}

// ── sample ──

async function _playSample() {
  const btn = $('voice-sample');
  const tts = window.aiTTSManager;
  if (!tts) return;
  if (tts.checkAvailability) await tts.checkAvailability();
  if (!tts.available) {
    if (window.uiModule?.showError) window.uiModule.showError('Speech is off. Turn it on in Settings → Speech.');
    return;
  }
  const p = _readForm();
  const name = ($('custom-character-name')?.value || '').trim();
  const hello = p.address ? `Hello, ${p.address}.` : 'Hello.';
  const intro = name ? ` I'm ${name}.` : '';
  const line = p.phrases[0] ? ` ${p.phrases[0]}` : ' This is how I sound.';
  if (btn) btn.disabled = true;
  try {
    await tts.speakWithVoice(`${hello}${intro}${line}`, { voice: p.voice, speed: p.speed });
  } catch (e) {
    if (window.uiModule?.showError) window.uiModule.showError('Could not play the sample: ' + e.message);
  } finally {
    if (btn) btn.disabled = false;
  }
}

// ── public ──

/** Voice profile for the persona in the form, or null if it has none. */
export function getProfile() {
  return _enabled ? _readForm() : null;
}

/** Fill the Voice tab from a persona's saved profile (null = no voice). */
export function setProfile(profile) {
  _enabled = !!profile;
  _writeForm(profile || DEFAULTS);
  const name = $('custom-character-name')?.value || '';
  if ($('voice-name')) $('voice-name').value = name;
  _syncEnabledUI();
  const preview = $('voice-prompt-preview');
  if (preview) preview.textContent = '';
  if (_enabled) _refreshPrompt(true);
}

function _onTabOpen() {
  if (!_startersLoaded) _loadStarters();
  _loadVoices(); // cheap; picks up Speech settings changes
  const name = $('custom-character-name')?.value || '';
  if ($('voice-name')) $('voice-name').value = name;
  _refreshPrompt(true);
}

export function init(apiBase) {
  API_BASE = apiBase || '';
  if (!$('voice-address')) return;

  document.querySelector('.preset-tab[data-chartab="voice"]')
    ?.addEventListener('click', _onTabOpen);

  $('voice-starter')?.addEventListener('change', (e) => {
    if (e.target.value) _applyStarter(e.target.value);
  });

  // The Name field here mirrors the one on the Persona tab.
  $('voice-name')?.addEventListener('input', (e) => {
    const main = $('custom-character-name');
    if (main) main.value = e.target.value;
    _changed();
  });

  ['voice-address', 'voice-formality', 'voice-length', 'voice-humour']
    .forEach(id => $(id)?.addEventListener('input', _changed));
  $('voice-voice')?.addEventListener('change', () => { _enabled = true; _syncEnabledUI(); });
  $('voice-speed')?.addEventListener('input', () => { _syncSpeedLabel(); _enabled = true; _syncEnabledUI(); });
  $('voice-auto-prompt')?.addEventListener('change', () => _changed());
  $('voice-sample')?.addEventListener('click', _playSample);
  $('voice-off-btn')?.addEventListener('click', () => {
    _enabled = false;
    _syncEnabledUI();
  });

  _bindChipInput('voice-phrases', () => _phrases, 10);
  _bindChipInput('voice-avoid', () => _avoid, 20);
  _syncEnabledUI();
}

const voiceProfilesModule = { init, getProfile, setProfile };
export default voiceProfilesModule;
