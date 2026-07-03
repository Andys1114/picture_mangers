#!/usr/bin/env python3
"""One-shot dev launcher: starts the FastAPI backend and the Next.js frontend
together, prints their logs interleaved with prefixes, and tears both down on
Ctrl+C or either process exiting.

Usage:
    python dev.py            # default: backend :8000, frontend :3000
    python dev.py --no-seed  # skip the dev-seed step

Requirements (checked before launch):
- Backend deps installed (run from a venv with fastapi/uvicorn/apscheduler/...).
- Frontend deps installed (frontend/node_modules present; run `npm install` if not).

The frontend's next.config.ts rewrites /api/* and /media/* to the backend, so
once both are up the gallery is reachable at http://localhost:3000.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

# Respect BACKEND_URL's port if customized, but default to 8000/3000.
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("PORT", "3000")
PYTHON = sys.executable


def _run(cmd: list[str], cwd: Path, label: str) -> subprocess.Popen:
    """Start a subprocess streaming stdout/stderr through a [label] prefix."""
    print(f"[{label}] $ {' '.join(cmd)}  (cwd: {cwd})", flush=True)

    def _prefix_stream(stream, tag: str) -> None:
        for line in iter(stream.readline, ""):
            sys.stdout.write(f"[{tag}] {line}")
            sys.stdout.flush()

    # stdout=PIPE so we can prefix; stderr merged into stdout.
    proc = subprocess.Popen(
        cmd, cwd=str(cwd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1, encoding="utf-8", errors="replace",
        # New process group on POSIX / CREATE_NEW_PROCESS_GROUP on Windows so
        # we can signal the whole tree, not just the parent shell.
        preexec_fn=os.setsid if os.name == "posix" else None,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )
    import threading
    t = threading.Thread(target=_prefix_stream, args=(proc.stdout, label), daemon=True)
    t.start()
    return proc


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the process and its children (whole group on POSIX, taskkill on Windows)."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        else:
            subprocess.run(
                ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                capture_output=True,
            )
    except (ProcessLookupError, PermissionError):
        pass


def _wait_ready(proc: subprocess.Popen, label: str, timeout: float = 30.0) -> bool:
    """Best-effort readiness: return True if the process is still alive after
    a short grace period (we don't health-poll to keep this dependency-free)."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        rc = proc.poll()
        if rc is not None:
            print(f"[{label}] exited early (code {rc})", flush=True)
            return False
        time.sleep(0.5)
    return proc.poll() is None


def main() -> int:
    no_seed = "--no-seed" in sys.argv

    # Pre-flight checks.
    if not (BACKEND / "app" / "main.py").exists():
        print("ERROR: backend/app/main.py not found — run dev.py from the repo root.", file=sys.stderr)
        return 1
    if not (FRONTEND / "node_modules").is_dir():
        print("ERROR: frontend/node_modules missing — run `npm install` in frontend/ first.", file=sys.stderr)
        return 1

    # 1. Migrate + (optionally) seed the backend DB so the gallery has data.
    if not no_seed:
        print("[backend] migrating + seeding dev data...", flush=True)
        subprocess.run([PYTHON, "-m", "alembic", "upgrade", "head"], cwd=str(BACKEND), check=True)
        subprocess.run([PYTHON, "-m", "scripts.seed_dev"], cwd=str(BACKEND), check=False)

    # 2. Start both processes.
    backend = _run(
        [PYTHON, "-m", "uvicorn", "app.main:app", "--reload", "--port", BACKEND_PORT],
        BACKEND, "backend",
    )
    frontend = _run(
        ["npm", "run", "dev"] if os.name != "nt" else ["npm.cmd", "run", "dev"],
        FRONTEND, "frontend",
    )

    print(
        f"\n  Backend  → http://localhost:{BACKEND_PORT}  (docs: /docs, health: /api/health)\n"
        f"  Frontend → http://localhost:{FRONTEND_PORT}   (gallery home; /api & /media proxied to backend)\n"
        f"  Ctrl+C stops both.\n",
        flush=True,
    )

    procs = [("backend", backend), ("frontend", frontend)]

    # 3. Wait for either to exit, then tear the other down.
    try:
        while True:
            for label, p in procs:
                rc = p.poll()
                if rc is not None:
                    print(f"[{label}] exited (code {rc}) — stopping the other.", flush=True)
                    raise SystemExit(0)
            time.sleep(0.5)
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        for label, p in procs:
            print(f"[{label}] stopping...", flush=True)
            _kill_tree(p)
        for _, p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
