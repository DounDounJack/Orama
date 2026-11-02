"""The órama desktop gate: only the app window (and the engine's own loopback
calls) may reach the engine."""
import asyncio

from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from src.desktop_gate import COOKIE_NAME, DesktopGate


def _inner():
    return Starlette(routes=[Route("/", lambda r: PlainTextResponse("home"))])


def _client(**kw):
    return TestClient(DesktopGate(_inner(), launch_token="launch-123", **kw),
                      follow_redirects=False)


def test_blocks_requests_without_session():
    c = _client()
    assert c.get("/").status_code == 403


def test_ping_is_open():
    c = _client()
    r = c.get("/__orama/ping")
    assert r.status_code == 200 and r.text == "ok"


def test_launch_token_opens_once():
    c = _client()
    r = c.get("/__orama/open?token=launch-123")
    assert r.status_code == 302 and r.headers["location"] == "/"
    assert COOKIE_NAME in r.headers["set-cookie"]
    assert "HttpOnly" in r.headers["set-cookie"]
    assert c.get("/").text == "home"
    # second use of the same token is refused
    other = _client()
    assert c.get("/__orama/open?token=launch-123").status_code == 403
    assert other.get("/").status_code == 403


def test_wrong_token_refused():
    c = _client()
    assert c.get("/__orama/open?token=nope").status_code == 403
    assert c.get("/__orama/open").status_code == 403
    # a wrong guess must not burn the real token
    assert c.get("/__orama/open?token=launch-123").status_code == 302


def test_forged_cookie_refused():
    c = _client()
    c.cookies.set(COOKIE_NAME, "guess")
    assert c.get("/").status_code == 403


def _call(gate, client_host, headers):
    sent = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(msg):
        sent.append(msg)

    scope = {"type": "http", "method": "GET", "path": "/", "query_string": b"",
             "headers": headers, "client": (client_host, 5000), "server": ("127.0.0.1", 1),
             "scheme": "http", "root_path": "", "http_version": "1.1", "raw_path": b"/"}
    asyncio.run(gate(scope, receive, send))
    return sent[0]["status"]


def test_internal_tool_header_from_loopback_only():
    gate = DesktopGate(_inner(), launch_token="t", internal_token="secret",
                       internal_header="X-Odysseus-Internal-Token")
    hdr = [(b"x-odysseus-internal-token", b"secret")]
    assert _call(gate, "127.0.0.1", hdr) == 200
    assert _call(gate, "10.0.0.5", hdr) == 403
    assert _call(gate, "127.0.0.1", [(b"x-odysseus-internal-token", b"bad")]) == 403
