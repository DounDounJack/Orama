"""órama voice assistant: the Voice tab and talk mode stay wired into the UI."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "static/index.html").read_text(encoding="utf-8")
SW = (ROOT / "static/sw.js").read_text(encoding="utf-8")
PRESETS = (ROOT / "static/js/presets.js").read_text(encoding="utf-8")
TTS = (ROOT / "static/js/tts-ai.js").read_text(encoding="utf-8")
TALK = (ROOT / "static/js/talkMode.js").read_text(encoding="utf-8")
VOICE = (ROOT / "static/js/voiceProfiles.js").read_text(encoding="utf-8")


def test_voice_tab_markup():
    assert 'data-chartab="voice"' in INDEX
    assert 'data-chartab-panel="voice"' in INDEX
    for el_id in ("voice-starter", "voice-name", "voice-address", "voice-formality",
                  "voice-length", "voice-humour", "voice-phrases", "voice-avoid",
                  "voice-voice", "voice-speed", "voice-sample", "voice-auto-prompt",
                  "voice-prompt-preview"):
        assert f'id="{el_id}"' in INDEX, el_id
        assert f"'{el_id}'" in VOICE, el_id


def test_talk_mode_button_and_module_loaded():
    assert 'id="talk-mode-btn"' in INDEX
    assert '<script type="module" src="/static/js/talkMode.js"></script>' in INDEX
    assert "$('talk-mode-btn')" in TALK


def test_new_modules_precached():
    assert "'/static/js/talkMode.js'" in SW
    assert "'/static/js/voiceProfiles.js'" in SW


def test_presets_saves_and_loads_voice():
    assert "import voiceProfiles from './voiceProfiles.js';" in PRESETS
    assert "voice: _isInjectStart ? null : voiceProfiles.getProfile()" in PRESETS
    assert "voiceProfiles.setProfile(tmpl.voice || null)" in PRESETS
    assert "voice: tmpl.voice || null" in PRESETS  # persistent chat restore
    assert "export function getActiveVoice()" in PRESETS
    assert "window.oramaGetActiveVoice = getActiveVoice" in PRESETS


def test_presets_imports_share_one_version():
    versions = set()
    for path in (ROOT / "static").rglob("*.js"):
        versions.update(re.findall(r"presets\.js\?v=([\w-]+)", path.read_text(encoding="utf-8")))
    versions.update(re.findall(r"presets\.js\?v=([\w-]+)", INDEX))
    assert len(versions) == 1, versions


def test_tts_sends_persona_voice():
    assert "window.oramaGetActiveVoice" in TTS
    assert "voice: _v.voice" in TTS
    assert "speakWithVoice" in TTS and "speakWithVoice" in VOICE


def test_talk_mode_restores_autoplay_and_releases_mic():
    assert "tts.autoPlay = true" in TALK
    assert "window.aiTTSManager.autoPlay = _prevAutoPlay" in TALK
    assert "_releaseMic()" in TALK
