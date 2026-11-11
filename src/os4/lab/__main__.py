"""Run the Model Lab: ``uv run python -m os4.lab`` then open http://127.0.0.1:8411 (``--open`` opens it for you).

The standalone executable starts it with ``--open`` when launched with no arguments (e.g. double-clicked).
"""

import argparse
import os
import threading
import webbrowser
from pathlib import Path

import os4.tradespace as ts
from os4.lab.server import serve

DEFAULT_CACHE = Path.home() / ".cache" / "os4-lab"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m os4.lab", description="OS4 Model Lab: presets, custom "
                                     "scenarios and live tradespace runs in the browser.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="address to listen on (default 127.0.0.1; use a password if others can reach it)")
    parser.add_argument("--port", type=int, default=8411, help="port (default 8411)")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help=f"result cache (default {DEFAULT_CACHE})")
    parser.add_argument("--no-cache", action="store_true", help="recompute every run")
    parser.add_argument("--cache-max-mb", type=float, default=250,
                        help="cap on the result cache; least recently used results go first (default 250 MB)")
    parser.add_argument("--max-queue", type=int, default=4, help="runs allowed to wait behind the current one (default 4)")
    parser.add_argument("--password", default=None,
                        help="require this password (default: the OS4_LAB_PASSWORD environment variable; none if unset)")
    parser.add_argument("--open", action="store_true",
                        help="open the Lab in the default browser; if the port is taken, use a free one")
    args = parser.parse_args(argv)
    ts.SHOW_PROGRESS = False  # the page shows progress instead
    cache_dir = None if args.no_cache else args.cache_dir
    try:
        server = serve(args.host, args.port, cache_dir, args.password, args.max_queue, args.cache_max_mb)
    except OSError:
        if not args.open:
            raise
        # e.g. a second double-click while the first copy is still running
        server = serve(args.host, 0, cache_dir, args.password, args.max_queue, args.cache_max_mb)
    host, port = server.server_address[:2]
    url = f"http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}"
    locked = bool(args.password or os.environ.get("OS4_LAB_PASSWORD"))
    print(f"OS4 Model Lab on {url}  ({'password required' if locked else 'no password'}; "
          f"close this window or press Ctrl+C to stop)", flush=True)
    if args.open:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
