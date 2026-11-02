"""órama voice assistant: profiles, prompt builder, starter styles, voice
per persona, and per-request TTS voice/speed."""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from routes.tts_routes import setup_tts_routes
from routes.voice_routes import setup_voice_routes
from services.tts.tts_service import TTSService
from src.preset_manager import PresetManager
from src.request_models import PresetUpdateRequest
from src.voice_profiles import (
    STARTERS, VoiceProfile, build_prompt, starters_for, voices_for,
)


# ── profile model ──

def test_profile_defaults_and_cleaning():
    p = VoiceProfile(
        address="  my   lord ",
        phrases=["Very good.", "very good.", "  ", "Right away."] + [f"p{i}" for i in range(20)],
        avoid=["awesome", "AWESOME", "x" * 100],
    )
    assert p.address == "my lord"
    assert p.phrases[:2] == ["Very good.", "Right away."]
    assert len(p.phrases) == 10
    assert p.avoid == ["awesome", "x" * 40]
    assert p.speed == 1.0 and p.auto_prompt is True


@pytest.mark.parametrize("field,value", [
    ("formality", 101), ("length", -1), ("humour", 200), ("speed", 0.1), ("speed", 3),
    ("voice", "bad;voice"), ("voice", "<script>"),
])
def test_profile_rejects_out_of_range(field, value):
    with pytest.raises(ValidationError):
        VoiceProfile(**{field: value})


def test_profile_accepts_system_voice_names():
    assert VoiceProfile(voice="Daniel (Enhanced)").voice == "Daniel (Enhanced)"
    assert VoiceProfile(voice="bm_george").voice == "bm_george"


# ── prompt builder ──

def test_prompt_formal_short_no_humour():
    p = VoiceProfile(address="sir", formality=0, length=0, humour=0,
                     phrases=["Very good."], avoid=["awesome"])
    text = build_prompt("Steward", p)
    assert text.startswith("You are Steward, a voice assistant.")
    assert 'Address the user as "sir"' in text
    assert "Speak formally" in text
    assert "Keep replies short" in text
    assert "Don't joke" in text
    assert '"Very good."' in text
    assert 'Never say these words or phrases: "awesome".' in text
    assert "read aloud" in text


def test_prompt_casual_chatty_funny():
    text = build_prompt("Sunny", VoiceProfile(formality=100, length=100, humour=100))
    assert "Speak casually" in text
    assert "chatty" in text
    assert "playful" in text
    assert "Address the user" not in text
    assert "Never say" not in text


def test_prompt_middle_settings_and_no_name():
    text = build_prompt("", VoiceProfile(formality=50, length=50, humour=50))
    assert text.startswith("You are a voice assistant.")
    assert "friendly but professional" in text
    assert "reasonably brief" in text
    assert "light humour" in text


# ── starter styles ──

def test_starters_are_original_and_include_a_butler():
    names = [s["name"] for s in STARTERS]
    assert names == ["Steward", "Sunny", "Brief", "Mentor"]
    steward = STARTERS[0]
    assert steward["profile"]["address"] == "sir"
    assert steward["profile"]["formality"] <= 10
    # Guard against film/TV character names creeping in.
    banned = {"jarvis", "alfred", "hal", "c-3po", "samantha os", "friday", "karen ai"}
    for s in STARTERS:
        assert s["name"].lower() not in banned
        assert s["id"] == s["name"].lower()


@pytest.mark.parametrize("provider,kind", [
    ("endpoint:abc", "endpoint"), ("local", "local"), ("browser", "browser"),
])
def test_starters_pick_voice_for_provider(provider, kind):
    out = starters_for(provider)
    assert [s["id"] for s in out] == ["steward", "sunny", "brief", "mentor"]
    for s, src in zip(out, STARTERS):
        assert s["profile"]["voice"] == src["voices"][kind]
        assert s["profile"]["starter"] == src["id"]
        assert s["system_prompt"].startswith(f"You are {src['name']}")
        VoiceProfile(**s["profile"])  # valid


def test_voices_for_provider():
    assert voices_for("browser") is None
    assert "bm_george" in voices_for("local")
    assert "alloy" in voices_for("endpoint:x")


# ── routes ──

class _FakeTTS:
    def __init__(self, provider="browser", enabled=True):
        self.provider, self.enabled = provider, enabled
        self.calls = []

    def _load_settings(self):
        return {"tts_provider": self.provider, "tts_enabled": self.enabled}

    available = True

    def synthesize(self, text, use_cache=True, voice=None, speed=None):
        self.calls.append((text, voice, speed))
        return b"ID3fake"


def _client(tts):
    app = FastAPI()
    app.include_router(setup_voice_routes(tts))
    app.include_router(setup_tts_routes(tts))
    return TestClient(app)


def test_voice_routes():
    c = _client(_FakeTTS("local"))
    r = c.get("/api/voice/starters").json()
    assert r["provider"] == "local"
    assert r["starters"][0]["profile"]["voice"] == "bm_george"
    assert c.get("/api/voice/voices").json()["voices"][0] == "af_heart"
    r = c.post("/api/voice/prompt", json={"name": "Max", "profile": {"address": "boss", "humour": 0}})
    assert r.status_code == 200 and 'Address the user as "boss"' in r.json()["prompt"]
    assert c.post("/api/voice/prompt", json={"profile": {"humour": 900}}).status_code == 422


def test_voice_routes_when_tts_off():
    c = _client(_FakeTTS("endpoint:x", enabled=False))
    assert c.get("/api/voice/voices").json()["provider"] == "disabled"


def test_tts_route_passes_voice_and_speed():
    tts = _FakeTTS("endpoint:x")
    c = _client(tts)
    r = c.post("/api/tts/synthesize", json={"text": "hi", "voice": "fable", "speed": 0.9})
    assert r.status_code == 200
    assert tts.calls[-1] == ("hi", "fable", 0.9)
    c.post("/api/tts/synthesize", json={"text": "hi"})
    assert tts.calls[-1] == ("hi", None, None)
    assert c.post("/api/tts/synthesize", json={"text": "hi", "voice": "a;b"}).status_code == 422
    assert c.post("/api/tts/synthesize", json={"text": "hi", "speed": 9}).status_code == 422


# ── TTS service override ──

def test_tts_service_uses_override_voice_and_speed(monkeypatch, tmp_path):
    svc = TTSService(cache_dir=str(tmp_path))
    monkeypatch.setattr(svc, "_load_settings", lambda: {
        "tts_enabled": True, "tts_provider": "endpoint:e1", "tts_model": "tts-1",
        "tts_voice": "alloy", "tts_speed": "1"})
    seen = []
    monkeypatch.setattr(svc, "_synthesize_api",
                        lambda text, ep, model, voice, speed: seen.append((voice, speed)) or b"x")
    svc.synthesize("hello", use_cache=False, voice="fable", speed=0.9)
    svc.synthesize("hello", use_cache=False)
    assert seen == [("fable", 0.9), ("alloy", 1.0)]


def test_tts_cache_separates_voices(monkeypatch, tmp_path):
    svc = TTSService(cache_dir=str(tmp_path))
    monkeypatch.setattr(svc, "_load_settings", lambda: {
        "tts_enabled": True, "tts_provider": "endpoint:e1", "tts_model": "tts-1",
        "tts_voice": "alloy", "tts_speed": "1"})
    monkeypatch.setattr(svc, "_synthesize_api",
                        lambda text, ep, model, voice, speed: voice.encode())
    assert svc.synthesize("same", voice="fable") == b"fable"
    assert svc.synthesize("same", voice="onyx") == b"onyx"
    assert svc.synthesize("same", voice="fable") == b"fable"


# ── persona storage ──

def test_active_persona_keeps_voice(tmp_path):
    pm = PresetManager(str(tmp_path))
    req = PresetUpdateRequest(name="Steward", system_prompt="x",
                              voice={"address": "sir", "voice": "Daniel", "speed": 0.95})
    pm.update_custom(req.temperature, req.max_tokens, req.system_prompt, req.name,
                     voice=req.voice.model_dump())
    again = PresetManager(str(tmp_path))
    assert again.get("custom")["voice"]["voice"] == "Daniel"
    assert again.get("custom")["voice"]["speed"] == 0.95


def test_plain_persona_has_no_voice(tmp_path):
    pm = PresetManager(str(tmp_path))
    pm.update_custom(1.0, 0, "x", "Plain")
    assert pm.get("custom")["voice"] is None


def test_template_route_keeps_voice(tmp_path):
    from routes.preset_routes import setup_preset_routes
    from core.middleware import require_admin

    pm = PresetManager(str(tmp_path))
    app = FastAPI()
    app.include_router(setup_preset_routes(pm))
    app.dependency_overrides[require_admin] = lambda: None
    c = TestClient(app)
    r = c.post("/api/presets/templates", json={
        "name": "Steward", "system_prompt": "x",
        "voice": {"address": "sir", "phrases": ["Very good."], "voice": "fable"}})
    assert r.status_code == 200 and r.json()["success"]
    saved = c.get("/api/presets/templates").json()[0]
    assert saved["voice"]["address"] == "sir"
    assert saved["voice"]["phrases"] == ["Very good."]
    # older clients that send no voice still work
    r = c.post("/api/presets/templates", json={"name": "Old", "system_prompt": "y"})
    assert r.json()["template"]["voice"] is None
