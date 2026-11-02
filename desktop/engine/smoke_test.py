"""Quick check that a built órama engine starts and answers.

    python desktop/engine/smoke_test.py path/to/orama-engine[.exe]

Starts the engine the way the desktop app does (random port, one-time token,
a throwaway data folder), waits for /__orama/ping to say "ok", checks that the
access gate turns away a request without the token, then that the token opens
the app. Exits 0 on success; prints the engine log and exits 1 otherwise.
Used by the GitHub Actions build (.github/workflows/desktop.yml).
"""
import http.client
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time

TIMEOUT = 300  # first start unpacks and indexes a lot; CI machines are slow


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def get(port: int, path: str, headers=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=10)
    try:
        conn.request("GET", path, headers=headers or {})
        r = conn.getresponse()
        return r.status, dict(r.getheaders()), r.read().decode("utf-8", "replace")
    finally:
        conn.close()


def main() -> int:
    exe = os.path.abspath(sys.argv[1])
    if not os.path.isfile(exe):
        print(f"FAIL: no engine at {exe}")
        return 1
    port = free_port()
    token = secrets.token_hex(32)
    data = tempfile.mkdtemp(prefix="orama-smoke-")
    log_path = os.path.join(data, "engine-smoke.log")
    env = dict(os.environ,
               ORAMA_PORT=str(port),
               ORAMA_LAUNCH_TOKEN=token,
               ORAMA_DATA_DIR=data,
               ORAMA_PARENT_PID=str(os.getpid()))
    print(f"Starting {exe} on port {port}, data in {data}")
    log = open(log_path, "wb")
    proc = subprocess.Popen([exe], env=env, cwd=data, stdin=subprocess.DEVNULL,
                            stdout=log, stderr=subprocess.STDOUT)
    ok = False
    try:
        started = time.time()
        while time.time() - started < TIMEOUT:
            if proc.poll() is not None:
                print(f"FAIL: engine exited early with code {proc.returncode}")
                break
            try:
                status, _, body = get(port, "/__orama/ping")
                if status == 200 and "ok" in body:
                    print(f"Engine answered after {time.time() - started:.0f}s")
                    ok = True
                    break
            except OSError:
                pass
            time.sleep(1)
        else:
            print(f"FAIL: engine didn't answer within {TIMEOUT}s")

        if ok:
            status, _, _ = get(port, "/")
            if status != 403:
                print(f"FAIL: request without the token got {status}, expected 403")
                ok = False
        if ok:
            status, headers, _ = get(port, f"/__orama/open?token={token}")
            cookie = headers.get("set-cookie") or headers.get("Set-Cookie") or ""
            if status not in (302, 303, 307) or "orama_desktop=" not in cookie:
                print(f"FAIL: opening with the token got {status}")
                ok = False
            else:
                jar = {"Cookie": cookie.split(";")[0]}
                status, headers, body = get(port, "/", jar)
                if status in (302, 303, 307):  # first run: off to the login page
                    loc = headers.get("location") or headers.get("Location") or "/login"
                    if "://" in loc:
                        loc = "/" + loc.split("://", 1)[1].split("/", 1)[-1]
                    print(f"/ redirects to {loc}")
                    status, _, body = get(port, loc, jar)
                # The login page or the app itself, either is fine.
                if status != 200 or "<html" not in body.lower():
                    print(f"FAIL: app page got {status}")
                    ok = False
        if ok:
            print("PASS: engine starts, answers, and the access gate works")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        log.close()
        if not ok:
            print("----- engine log (last 200 lines) -----")
            with open(log_path, "rb") as f:
                lines = f.read().decode("utf-8", "replace").splitlines()
            print("\n".join(lines[-200:]))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
