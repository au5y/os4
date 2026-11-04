"""Model Lab HTTP server (standard library only).

Routes:
    GET  /                     the lab page (static/lab.html)
    GET  /static/<file>        the lab's own JS and CSS
    GET  /assets/<file>        the explorer's shared assets (common.js, style.css) from site_template
    GET  /api/presets          preset configs
    GET  /api/schema           editable fields, weight sets, the baseline config
    GET  /api/meta             column labels and components, for the explorer's helpers
    POST /api/jobs             start a run for the posted config -> {"job_id"}
    GET  /api/jobs/<id>        {"status", "progress", "result" | "error"}

Runs go through one worker thread (a full tradespace uses up to about 1 GB), and results are cached on disk.
"""

import json
import mimetypes
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from os4.lab.config import FIELDS, from_scenario, validate
from os4.lab.presets import presets
from os4.lab.run import calculate, config_key
from os4.scenario import primary_scenario
from os4.site import COLUMN_LABELS, components_payload
from os4.utility import ATTRIBUTES, WEIGHT_SETS, load_weights

STATIC = Path(__file__).resolve().parent / "static"
ASSETS = Path(__file__).resolve().parents[1] / "site_template" / "assets"
MAX_BODY = 1 << 20


class Lab:
    """Shared state: presets, the job table and the worker."""

    def __init__(self, cache_dir: Path | None):
        self.cache_dir = cache_dir
        self.presets = presets()
        self.jobs: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.pool = ThreadPoolExecutor(max_workers=1)

    def schema(self) -> dict:
        return {
            "fields": FIELDS,
            "attributes": list(ATTRIBUTES),
            "weight_sets": {name: load_weights(name) for name in WEIGHT_SETS},
            "baseline": from_scenario(primary_scenario()),
        }

    def submit(self, config: dict) -> str:
        cfg = validate(config)
        job_id = uuid.uuid4().hex[:12]
        job = {"status": "queued", "progress": 0.0, "key": config_key(cfg)}
        with self.lock:
            self.jobs[job_id] = job

        def progress(done, total):
            job["progress"] = done / total if total else 1.0

        def work():
            job["status"] = "running"
            try:
                job["result"] = calculate(cfg, progress, self.cache_dir)
                job["progress"], job["status"] = 1.0, "done"
            except Exception as e:  # report to the page instead of killing the worker
                job["status"], job["error"] = "error", f"{type(e).__name__}: {e}"
                traceback.print_exc()

        self.pool.submit(work)
        return job_id

    def job(self, job_id: str) -> dict | None:
        with self.lock:
            job = self.jobs.get(job_id)
        if job and job["status"] in ("done", "error"):  # hand the result over once, then forget the job
            with self.lock:
                self.jobs.pop(job_id, None)
        return job


def make_handler(lab: Lab):
    class Handler(BaseHTTPRequestHandler):
        server_version = "os4-lab"

        def log_message(self, fmt, *args):  # keep the console quiet except for errors
            if not str(args[1] if len(args) > 1 else "").startswith(("2", "3")):
                super().log_message(fmt, *args)

        def _send(self, status: int, body: bytes, ctype: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, payload, status: int = 200) -> None:
            body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode()
            self._send(status, body, "application/json")

        def _file(self, root: Path, name: str) -> None:
            path = (root / name).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                return self._json({"error": "not found"}, 404)
            ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            self._send(200, path.read_bytes(), ctype + ("; charset=utf-8" if ctype.startswith("text/") or
                                                         ctype.endswith("javascript") else ""))

        def do_GET(self):
            path = self.path.split("?", 1)[0]
            if path in ("/", "/index.html"):
                return self._file(STATIC, "lab.html")
            if path.startswith("/static/"):
                return self._file(STATIC, path[len("/static/"):])
            if path.startswith("/assets/"):
                return self._file(ASSETS, path[len("/assets/"):])
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
            if self.path != "/api/jobs":
                return self._json({"error": "not found"}, 404)
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > MAX_BODY:
                return self._json({"error": "bad request body"}, 400)
            try:
                config = json.loads(self.rfile.read(length))
                return self._json({"job_id": lab.submit(config)}, 202)
            except (ValueError, TypeError, KeyError) as e:
                return self._json({"error": str(e)}, 400)

    return Handler


def serve(host: str = "127.0.0.1", port: int = 8411, cache_dir: Path | None = None) -> ThreadingHTTPServer:
    """Build the server (call ``serve_forever()`` on it); port 0 picks a free port."""
    return ThreadingHTTPServer((host, port), make_handler(Lab(cache_dir)))
