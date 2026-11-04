"""Model Lab HTTP server (standard library only).

Routes:
    GET  /                     the lab page (static/lab.html)
    GET  /static/<file>        the lab's own JS and CSS
    GET  /assets/<file>        the explorer's shared assets (common.js, style.css) from site_template
    GET  /api/session          {"auth_required", "ok"}
    POST /api/login            {"password"} -> sets the session cookie
    GET  /api/presets          preset configs
    GET  /api/schema           editable fields, weight sets, the baseline config, run limits
    GET  /api/meta             column labels and components, for the explorer's helpers
    POST /api/estimate         {"config", "limit"} -> architectures the run would score, and any trimming
    POST /api/jobs             start a run: {"config", "tags", "limit"} (or a bare config) -> {"job_id"}
    GET  /api/jobs/<id>        {"status", "progress", "position", "result" | "error"}

When the server has a password (``--password`` or ``OS4_LAB_PASSWORD``), every ``/api`` route except
session and login needs the session cookie. Runs go through one worker thread (a full tradespace uses up to
about 1 GB) with at most ``max_queue`` waiting, and results are cached on disk up to ``cache_max_mb``.
"""

import hmac
import json
import mimetypes
import os
import secrets
import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from os4.lab.config import FIELDS, GRID_MAX, GRID_MAX_SIZES, from_scenario, validate
from os4.lab.presets import presets
from os4.lab.run import DEFAULT_LIMIT, HARD_LIMIT, calculate, estimate, evaluate_tags, limit_grid
from os4.scenario import primary_scenario
from os4.site import COLUMN_LABELS, components_payload
from os4.utility import ATTRIBUTES, WEIGHT_SETS, load_weights

STATIC = Path(__file__).resolve().parent / "static"
ASSETS = Path(__file__).resolve().parents[1] / "site_template" / "assets"
MAX_BODY = 1 << 20
COOKIE = "os4lab"
JOB_TTL_S = 15 * 60
OPEN_API = ("/api/session", "/api/login")


class Busy(Exception):
    """The run queue is full."""


class Lab:
    """Shared state: presets, sessions, the job queue and the worker."""

    def __init__(self, cache_dir: Path | None, password: str | None = None, max_queue: int = 4,
                 cache_max_mb: float = 250):
        self.cache_dir = cache_dir
        self.password = password or None
        self.max_queue = max_queue
        self.cache_max_bytes = int(cache_max_mb * 1024 * 1024)
        self.presets = presets()
        self.sessions: set[str] = set()
        self.jobs: dict[str, dict] = {}
        self.waiting: list[str] = []  # queued job ids, oldest first
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)

    # ---- auth ----
    def login(self, password: str) -> str | None:
        if not self.password or not hmac.compare_digest(str(password).encode(), self.password.encode()):
            time.sleep(1.0)  # slow down guessing
            return None
        token = secrets.token_urlsafe(24)
        with self.lock:
            self.sessions.add(token)
        return token

    def authorized(self, token: str | None) -> bool:
        return not self.password or (token is not None and token in self.sessions)

    # ---- api ----
    def schema(self) -> dict:
        return {
            "fields": FIELDS,
            "attributes": list(ATTRIBUTES),
            "weight_sets": {name: load_weights(name) for name in WEIGHT_SETS},
            "baseline": from_scenario(primary_scenario()),
            "limits": {"default": DEFAULT_LIMIT, "hard": HARD_LIMIT, "grid_max": GRID_MAX,
                       "grid_max_sizes": GRID_MAX_SIZES, "max_queue": self.max_queue},
        }

    def plan(self, config: dict, limit: bool) -> tuple[dict, dict | None, int]:
        """The config to run (grid trimmed to the 2 M default if ``limit``), the trimming note, and its size."""
        cfg = validate(config)
        if limit:
            cfg, note = limit_grid(cfg, DEFAULT_LIMIT)
        else:
            note = None
        size = estimate(cfg)["architectures"]
        if size > HARD_LIMIT:
            raise ValueError(f"this run would score {size:,} architectures; the most allowed is {HARD_LIMIT:,}. "
                             "Use fewer or smaller fleet sizes, or turn the 2 million limit back on.")
        return cfg, note, size

    def submit(self, config: dict, tags: list | None = None, limit: bool = True) -> str:
        cfg, note, size = self.plan(config, limit)
        tags = [t for t in (tags or []) if isinstance(t, dict) and t.get("id")][:50]
        job_id = uuid.uuid4().hex[:12]
        job = {"status": "queued", "progress": 0.0, "size": size, "limited": note, "created": time.time()}
        with self.lock:
            self._expire()
            if len(self.waiting) >= self.max_queue:
                raise Busy(f"The lab is busy: {len(self.waiting)} runs are already waiting. Try again in a minute.")
            self.jobs[job_id] = job
            self.waiting.append(job_id)

        def progress(done, total):
            job["progress"] = done / total if total else 1.0

        def work():
            with self.lock:
                if job_id in self.waiting:
                    self.waiting.remove(job_id)
            job["status"] = "running"
            try:
                result = calculate(cfg, progress, self.cache_dir)
                result["tags"] = evaluate_tags(cfg, tags, result.get("front", []))
                result["limited"] = note
                job["result"] = result
                job["progress"], job["status"] = 1.0, "done"
                self._trim_cache()
            except Exception as e:  # report to the page instead of killing the worker
                job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"
                traceback.print_exc()

        self.pool.submit(work)
        return job_id

    def job(self, job_id: str) -> dict | None:
        with self.lock:
            job = self.jobs.get(job_id)
            if job is None:
                return None
            out = {k: v for k, v in job.items() if k != "created"}
            if job["status"] == "queued" and job_id in self.waiting:
                out["position"] = self.waiting.index(job_id) + 1
            if job["status"] in ("done", "error"):  # hand the result over once, then forget the job
                self.jobs.pop(job_id, None)
        return out

    def _expire(self) -> None:
        """Forget finished jobs nobody collected (call with the lock held)."""
        now = time.time()
        for jid in [j for j, job in self.jobs.items() if job["status"] in ("done", "error")
                    and now - job["created"] > JOB_TTL_S]:
            self.jobs.pop(jid, None)

    def _trim_cache(self) -> None:
        """Keep the result cache under ``cache_max_bytes``, deleting the least recently used results first."""
        if not self.cache_dir or not self.cache_dir.exists():
            return
        files = sorted(self.cache_dir.glob("*.json"), key=lambda p: p.stat().st_mtime)
        total = sum(p.stat().st_size for p in files)
        for p in files:
            if total <= self.cache_max_bytes:
                break
            total -= p.stat().st_size
            p.unlink(missing_ok=True)


def make_handler(lab: Lab):
    class Handler(BaseHTTPRequestHandler):
        server_version = "os4-lab"

        def log_message(self, fmt, *args):  # keep the console quiet except for errors
            if not str(args[1] if len(args) > 1 else "").startswith(("2", "3")):
                super().log_message(fmt, *args)

        def _send(self, status: int, body: bytes, ctype: str, headers: dict | None = None) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, status: int = 200, headers: dict | None = None) -> None:
            body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
            self._send(status, body, "application/json", headers)

        def _file(self, root: Path, name: str) -> None:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text/") or
                                                         ctype.endswith("javascript") else ""))

        def _token(self) -> str | None:
            jar = SimpleCookie(self.headers.get("Cookie") or "")
            return jar[COOKIE].value if COOKIE in jar else None

        def _body(self) -> dict:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                raise ValueError("bad request body")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("expected a JSON object")
            return body

        def _guard(self, path: str) -> bool:
            """True if the request may go on; otherwise answers 401."""
            if not path.startswith("/api/") or path in OPEN_API or lab.authorized(self._token()):
                return True
            self._json({"error": "password required", "auth": True}, 401)
            return False

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if not self._guard(path):
                return
            if path in ("/", "/index.html"):
                return self._file(STATIC, "lab.html")
            if path.startswith("/static/"):
                return self._file(STATIC, path[len("/static/"):])
            if path.startswith("/assets/"):
                return self._file(ASSETS, path[len("/assets/"):])
            if path == "/api/session":
                return self._json({"auth_required": bool(lab.password), "ok": lab.authorized(self._token())})
            if path == "/api/presets":
                return self._json(lab.presets)
            if path == "/api/schema":
                return self._json(lab.schema())
            if path == "/api/meta":
                return self._json({"labels": COLUMN_LABELS, "components": components_payload()})
            if path.startswith("/api/jobs/"):
                job = lab.job(path.rsplit("/", 1)[1])
                if job is None:
                    return self._json({"error": "unknown job"}, 404)
                return self._json(job)
            return self._json({"error": "not found"}, 404)

        def do_POST(self):
            path = self.path.split("?", 1)[0]
            if not self._guard(path):
                return
            try:
                body = self._body()
                if path == "/api/login":
                    token = lab.login(body.get("password", ""))
                    if not token:
                        return self._json({"error": "wrong password"}, 403)
                    return self._json({"ok": True}, 200, {"Set-Cookie": f"{COOKIE}={token}; Path=/; HttpOnly; "
                                                                         "SameSite=Lax; Max-Age=2592000"})
                # {"config", "tags", "limit"}, or a bare config
                config = body["config"] if "config" in body else body
                limit = bool(body.get("limit", True)) if "config" in body else True
                if path == "/api/estimate":
                    cfg, note, size = lab.plan(config, limit)
                    return self._json({"architectures": size, "limited": note})
                if path == "/api/jobs":
                    return self._json({"job_id": lab.submit(config, body.get("tags") if "config" in body else None,
                                                            limit)}, 202)
                return self._json({"error": "not found"}, 404)
            except Busy as e:
                return self._json({"error": str(e), "busy": True}, 429)
            except (ValueError, TypeError, KeyError) as e:
                return self._json({"error": str(e).strip("'\"")}, 400)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8411, cache_dir: Path | None = None, password: str | None = None,
          max_queue: int = 4, cache_max_mb: float = 250) -> ThreadingHTTPServer:
    """Build the server (call ``serve_forever()`` on it); port 0 picks a free port."""
    lab = Lab(cache_dir, password if password is not None else os.environ.get("OS4_LAB_PASSWORD"), max_queue,
              cache_max_mb)
    return ThreadingHTTPServer((host, port), make_handler(lab))
