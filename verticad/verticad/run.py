#!/usr/bin/env python3
"""VERTICAD one-command launcher: sets everything up and runs backend + frontend together.

    python run.py            (Windows: py run.py)

First run creates .venv, installs Python + npm dependencies (needs internet). Later runs skip
anything already installed. Press Ctrl+C once to stop both servers.
"""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
BACKEND = ROOT / "backend"
VENV = ROOT / ".venv"
IS_WIN = os.name == "nt"
VENV_PY = VENV / ("Scripts/python.exe" if IS_WIN else "bin/python")
PY_REQS = [ROOT / "pipeline/src/Schependomlaan/requirements.txt", BACKEND / "requirements.txt"]
API_PORT, WEB_PORT = 8000, 5173


def say(msg: str) -> None:
    print(f"\n[verticad] {msg}", flush=True)


def fail(msg: str) -> None:
    print(f"\n[verticad] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def digest(paths: list[Path]) -> str:
    h = hashlib.sha256()
    for p in paths:
        h.update(p.read_bytes() if p.is_file() else b"")
    return h.hexdigest()


def run(cmd: list[str], cwd: Path) -> None:
    if subprocess.call(cmd, cwd=cwd) != 0:
        fail(f"command failed: {' '.join(cmd)}")


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if IS_WIN:  # npm.cmd spawns node; kill the whole tree
        subprocess.call(["taskkill", "/T", "/F", "/PID", str(proc.pid)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        proc.terminate()


def port_in_use(port: int) -> bool:
    import socket
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    if sys.version_info < (3, 10):
        fail("Python 3.10+ is required.")
    npm = shutil.which("npm")
    if not npm or not shutil.which("node"):
        fail("Node.js (with npm) is required. Install it from https://nodejs.org and re-run.")
    for port in (API_PORT, WEB_PORT):
        if port_in_use(port):
            fail(f"port {port} is already in use. Close whatever is using it (an old run of this script?) and retry.")

    # 1) Python environment
    if not VENV_PY.exists():
        say("Creating Python virtual environment (.venv) ...")
        run([sys.executable, "-m", "venv", str(VENV)], ROOT)
    stamp = VENV / ".reqs.sha"
    want = digest(PY_REQS)
    if not stamp.exists() or stamp.read_text() != want:
        say("Installing Python dependencies ...")
        run([str(VENV_PY), "-m", "pip", "install", "-q", *[a for p in PY_REQS for a in ("-r", str(p))]], ROOT)
        stamp.write_text(want)

    # 2) Web dependencies
    nstamp = WEB / "node_modules" / ".pkg.sha"
    nwant = digest([WEB / "package.json"])
    if not (WEB / "node_modules").is_dir() or not nstamp.exists() or nstamp.read_text() != nwant:
        say("Installing web dependencies (npm install) ...")
        run([npm, "install"], WEB)
        nstamp.write_text(nwant)

    # 3) Start both servers
    env = {**os.environ, "VERTICAD_API": f"http://127.0.0.1:{API_PORT}"}
    say("Starting backend ...")
    api = subprocess.Popen([str(VENV_PY), "-m", "uvicorn", "app.main:app", "--reload",
                            "--host", "127.0.0.1", "--port", str(API_PORT)], cwd=BACKEND, env=env)
    say("Starting frontend ...")
    web = subprocess.Popen([npm, "run", "dev", "--", "--host", "127.0.0.1", "--port", str(WEB_PORT), "--strictPort"], cwd=WEB, env=env)

    try:
        deadline = time.time() + 90
        ready = False
        while time.time() < deadline and api.poll() is None and web.poll() is None:
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{API_PORT}/api/health", timeout=1).read()
                ready = True
                break
            except Exception:
                time.sleep(1)
        if ready:
            say(f"READY  ->  open http://localhost:{WEB_PORT}   (API docs: http://localhost:{API_PORT}/docs)\n"
                "           Use 'localhost', not 0.0.0.0.  Press Ctrl+C to stop.")
            webbrowser.open(f"http://localhost:{WEB_PORT}")
        while api.poll() is None and web.poll() is None:
            time.sleep(1)
        say("A server exited - shutting down.")
    except KeyboardInterrupt:
        say("Stopping ...")
    finally:
        kill_tree(api)
        kill_tree(web)


if __name__ == "__main__":
    main()
