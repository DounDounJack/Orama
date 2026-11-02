"""Voice assistant personalities (órama).

A voice profile sits on top of a persona (character): who the assistant calls
you, how formal, how long-winded, how funny, phrases it likes and words it
won't use, plus the voice and speed it speaks with. The text settings are
turned into the persona's system prompt by ``build_prompt``; the voice and
speed go to text-to-speech.

Starter styles are original. Don't add ones named after, or copying, a film,
TV or book character.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

MAX_PHRASES = 10
MAX_AVOID = 20
_VOICE_RE = re.compile(r"^[\w .()'\-]{0,80}$", re.UNICODE)


def _clean_list(items, limit: int, max_len: int) -> List[str]:
    out: List[str] = []
    seen = set()
    for raw in items or []:
        item = " ".join(str(raw).split())[:max_len]
        key = item.lower()
        if item and key not in seen:
            seen.add(key)
            out.append(item)
        if len(out) >= limit:
            break
    return out


class VoiceProfile(BaseModel):
    """The voice part of a persona. Sliders run 0-100."""

    address: str = Field("", max_length=40, description="What it calls the user, e.g. 'sir'")
    formality: int = Field(50, ge=0, le=100, description="0 = very formal, 100 = very casual")
    length: int = Field(40, ge=0, le=100, description="0 = very short, 100 = chatty")
    humour: int = Field(30, ge=0, le=100, description="0 = none, 100 = lots")
    phrases: List[str] = Field(default_factory=list, description="Favourite phrases")
    avoid: List[str] = Field(default_factory=list, description="Words and phrases to never use")
    voice: str = Field("", max_length=80, description="TTS voice id or system voice name")
    speed: float = Field(1.0, ge=0.5, le=2.0, description="Speaking speed")
    auto_prompt: bool = Field(True, description="Write the system prompt from these settings")
    starter: str = Field("", max_length=40, description="Starter style it was made from")

    @field_validator("address", mode="before")
    @classmethod
    def _address(cls, v):
        return " ".join(str(v or "").split())

    @field_validator("phrases", mode="before")
    @classmethod
    def _phrases(cls, v):
        return _clean_list(v, MAX_PHRASES, 80)

    @field_validator("avoid", mode="before")
    @classmethod
    def _avoid(cls, v):
        return _clean_list(v, MAX_AVOID, 40)

    @field_validator("voice")
    @classmethod
    def _voice(cls, v):
        v = (v or "").strip()
        if not _VOICE_RE.match(v):
            raise ValueError("voice name has unsupported characters")
        return v


# ── Prompt builder ──

def _band(value: int, low: str, mid: str, high: str) -> str:
    if value <= 33:
        return low
    if value >= 67:
        return high
    return mid


def _quote_list(items: List[str]) -> str:
    return ", ".join(f'"{i}"' for i in items)


def build_prompt(name: str, profile: VoiceProfile) -> str:
    """Turn a voice profile into a system prompt."""
    name = " ".join((name or "").split())
    lines: List[str] = []

    lines.append(
        f"You are {name}, a voice assistant." if name else "You are a voice assistant."
    )

    if profile.address:
        lines.append(
            f'Address the user as "{profile.address}". Use it naturally, '
            "not in every sentence."
        )

    lines.append(_band(
        profile.formality,
        "Speak formally: complete sentences, polite and precise wording, no slang "
        "or contractions.",
        "Speak in a friendly but professional way: plain words, contractions are fine.",
        "Speak casually, like a friend: relaxed, everyday words, contractions and "
        "light slang are fine.",
    ))

    lines.append(_band(
        profile.length,
        "Keep replies short: usually one to three sentences. Give more only when "
        "asked or when the task truly needs it.",
        "Keep replies reasonably brief: answer first, then add only useful detail.",
        "Be chatty and expansive: explain your thinking, add context and a little "
        "conversation, while staying on topic.",
    ))

    if profile.humour <= 10:
        lines.append("Don't joke. Stay matter-of-fact.")
    else:
        lines.append(_band(
            profile.humour,
            "Allow an occasional touch of very dry understatement, never at the "
            "expense of being helpful.",
            "Use light humour now and then when the moment allows.",
            "Be playful and witty; jokes are welcome, but never when the user is "
            "stressed or the topic is serious.",
        ))

    if profile.phrases:
        lines.append(
            "Phrases you like to use, now and then, where they fit: "
            f"{_quote_list(profile.phrases)}. Don't force them in."
        )

    if profile.avoid:
        lines.append(f"Never say these words or phrases: {_quote_list(profile.avoid)}.")

    lines.append(
        "Your replies may be read aloud, so write so it sounds natural spoken: "
        "plain sentences, no tables, no emoji, and only short lists when they "
        "really help."
    )
    lines.append("Stay helpful and honest. If you don't know something, say so.")
    return "\n".join(lines)


# ── Starter styles ──
# Voices are suggestions per text-to-speech provider kind:
#   endpoint = OpenAI-style API voices, local = Kokoro voices,
#   browser  = system voices (names from macOS; other systems fall back to
#              their default voice when the name isn't found).

STARTERS: List[Dict] = [
    {
        "id": "steward",
        "name": "Steward",
        "description": "Formal butler. Calm, precise, very dry understatement.",
        "temperature": 0.7,
        "profile": {
            "address": "sir",
            "formality": 5,
            "length": 25,
            "humour": 25,
            "phrases": ["Very good.", "Right away.", "If I may,", "Consider it done."],
            "avoid": ["awesome", "no worries", "hey", "cool", "lol"],
            "speed": 0.95,
        },
        "voices": {"endpoint": "fable", "local": "bm_george", "browser": "Daniel"},
    },
    {
        "id": "sunny",
        "name": "Sunny",
        "description": "Casual and upbeat, chatty, quick to joke.",
        "temperature": 1.0,
        "profile": {
            "address": "",
            "formality": 90,
            "length": 75,
            "humour": 75,
            "phrases": ["Ooh, good one.", "Let's do it!", "Here's the fun part:"],
            "avoid": ["per my last message", "kindly"],
            "speed": 1.05,
        },
        "voices": {"endpoint": "nova", "local": "af_heart", "browser": "Samantha"},
    },
    {
        "id": "brief",
        "name": "Brief",
        "description": "Only what's needed. Short replies, no small talk.",
        "temperature": 0.5,
        "profile": {
            "address": "",
            "formality": 45,
            "length": 0,
            "humour": 0,
            "phrases": ["Done.", "Next?"],
            "avoid": ["great question", "I hope this helps", "certainly", "absolutely"],
            "speed": 1.1,
        },
        "voices": {"endpoint": "ash", "local": "am_michael", "browser": "Alex"},
    },
    {
        "id": "mentor",
        "name": "Mentor",
        "description": "Warm and patient. Explains step by step and checks you followed.",
        "temperature": 0.8,
        "profile": {
            "address": "",
            "formality": 55,
            "length": 65,
            "humour": 35,
            "phrases": ["Let's take it one step at a time.", "Does that make sense so far?",
                        "Good thinking."],
            "avoid": ["obviously", "simply", "just do"],
            "speed": 0.95,
        },
        "voices": {"endpoint": "sage", "local": "af_bella", "browser": "Karen"},
    },
]


def provider_kind(provider: str) -> str:
    provider = (provider or "").strip()
    if provider.startswith("endpoint:"):
        return "endpoint"
    if provider in ("local", "browser"):
        return provider
    return "endpoint"


def starters_for(provider: str) -> List[Dict]:
    """Starter styles with the voice picked for the current TTS provider."""
    kind = provider_kind(provider)
    out = []
    for s in STARTERS:
        profile = VoiceProfile(**{**s["profile"], "voice": s["voices"].get(kind, ""),
                                  "starter": s["id"]})
        out.append({
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "temperature": s["temperature"],
            "profile": profile.model_dump(),
            "system_prompt": build_prompt(s["name"], profile),
        })
    return out


# ── Voice lists per provider ──

ENDPOINT_VOICES = ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx",
                   "sage", "shimmer", "verse"]

KOKORO_VOICES = [
    "af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
    "am_adam", "am_michael", "am_eric", "am_liam",
    "bf_emma", "bf_isabella", "bf_alice", "bf_lily",
    "bm_george", "bm_lewis", "bm_daniel", "bm_fable",
]


def voices_for(provider: str) -> Optional[List[str]]:
    """Voices the server knows for a provider. None = ask the browser."""
    kind = provider_kind(provider)
    if provider == "browser":
        return None
    if kind == "local":
        return list(KOKORO_VOICES)
    return list(ENDPOINT_VOICES)
