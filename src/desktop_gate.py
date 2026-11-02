"""Access gate for the órama desktop app.

When órama runs as a desktop app, the engine listens on a random 127.0.0.1
port. Any program on the machine could reach that port, so this ASGI wrapper
only lets through:

- the órama window: the desktop shell opens ``/__orama/open?token=<T>`` once
  with the one-time launch token. That sets a session cookie and redirects to
  ``/``. The token can't be used again.
- the engine's own loopback calls (agent tools) that carry the internal tool
  header, same rule as app.py's AuthMiddleware.
- ``/__orama/ping``, which only answers "ok" so the shell knows the engine is
  up. It reveals nothing else.

Everything else gets 403. The normal Odysseus login still applies on top.
"""

from __future__ import annotations

import secrets
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

COOKIE_NAME = "orama_desktop"
OPEN_PATH = "/__orama/open"
PING_PATH = "/__orama/ping"
_LOOPBACK = ("127.0.0.1", "::1")


class DesktopGate:
    def __init__(self, app, launch_token: str, internal_token: str | None = None,
                 internal_header: str = "x-odysseus-internal-token"):
        if not launch_token:
            raise ValueError("launch_token is required")
        self.app = app
        self._launch_token = launch_token
        self._launch_used = False
        self._session = secrets.token_urlsafe(32)
        self._internal_token = internal_token
        self._internal_header = internal_header.lower().encode("latin-1")

    # ── helpers ──

    @staticmethod
    def _header(scope, name: bytes) -> str:
        for k, v in scope.get("headers") or ():
            if k == name:
                return v.decode("latin-1")
        return ""

    def _has_session(self, scope) -> bool:
        raw = self._header(scope, b"cookie")
        if not raw:
            return False
        try:
            jar = SimpleCookie()
            jar.load(raw)
        except Exception:
            return False
        morsel = jar.get(COOKIE_NAME)
        return bool(morsel) and secrets.compare_digest(morsel.value, self._session)

    def _is_internal(self, scope) -> bool:
        if not self._internal_token:
            return False
        client = scope.get("client") or ("", 0)
        if client[0] not in _LOOPBACK:
            return False
        hdr = ""
        for k, v in scope.get("headers") or ():
            if k == self._internal_header:
                hdr = v.decode("latin-1")
                break
        return bool(hdr) and secrets.compare_digest(hdr, self._internal_token)

    @staticmethod
    async def _plain(send, status: int, body: bytes, extra=()):
        headers = [(b"content-type", b"text/plain; charset=utf-8"),
                   (b"cache-control", b"no-store")] + list(extra)
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    # ── ASGI ──

    async def __call__(self, scope, receive, send):
        kind = scope.get("type")
        if kind not in ("http", "websocket"):
            return await self.app(scope, receive, send)

        path = scope.get("path", "")

        if kind == "http" and path == PING_PATH:
            return await self._plain(send, 200, b"ok")

        if kind == "http" and path == OPEN_PATH:
            qs = parse_qs((scope.get("query_string") or b"").decode("latin-1"))
            token = (qs.get("token") or [""])[0]
            if (not self._launch_used and token
                    and secrets.compare_digest(token, self._launch_token)):
                self._launch_used = True
                cookie = (f"{COOKIE_NAME}={self._session}; Path=/; HttpOnly; "
                          f"SameSite=Strict")
                await send({"type": "http.response.start", "status": 302, "headers": [
                    (b"location", b"/"),
                    (b"set-cookie", cookie.encode("latin-1")),
                    (b"cache-control", b"no-store"),
                ]})
                await send({"type": "http.response.body", "body": b""})
                return
            return await self._plain(send, 403, b"Forbidden")

        if self._has_session(scope) or self._is_internal(scope):
            return await self.app(scope, receive, send)

        if kind == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        return await self._plain(send, 403, b"This engine only talks to the \xc3\xb3rama app.")
