"""Voice assistant routes (órama): starter styles, prompt preview, voice list."""

import logging
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from src.voice_profiles import VoiceProfile, build_prompt, starters_for, voices_for

logger = logging.getLogger(__name__)


class PromptPreviewRequest(BaseModel):
    name: str = Field("", max_length=50)
    profile: VoiceProfile


def setup_voice_routes(tts_service) -> APIRouter:
    router = APIRouter(prefix="/api/voice", tags=["voice"])

    def _provider() -> str:
        try:
            settings = tts_service._load_settings()
            if settings.get("tts_enabled") is False:
                return "disabled"
            return settings.get("tts_provider") or "disabled"
        except Exception:
            return "disabled"

    @router.get("/starters")
    async def get_starters() -> Dict[str, Any]:
        return {"provider": _provider(), "starters": starters_for(_provider())}

    @router.post("/prompt")
    async def preview_prompt(req: PromptPreviewRequest) -> Dict[str, Any]:
        return {"prompt": build_prompt(req.name, req.profile)}

    @router.get("/voices")
    async def get_voices() -> Dict[str, Any]:
        provider = _provider()
        voices = voices_for(provider)
        return {
            "provider": provider,
            # null means "list the system voices in the browser"
            "voices": voices,
        }

    return router
