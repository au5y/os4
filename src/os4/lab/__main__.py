"""Run the Model Lab: ``uv run python -m os4.lab`` then open http://127.0.0.1:8411."""

import argparse
from pathlib import Path

import os4.tradespace as ts
from os4.lab.server import serve

DEFAULT_CACHE = Path.home() / ".cache" / "os4-lab"


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m os4.lab", description="OS4 Model Lab: presets, custom "
                                     "scenarios and live tradespace runs in the browser.")
    parser.add_argument("--host", default="127.0.0.1",
                        help="address to listen on (default 127.0.0.1; 0.0.0.0 to self-host, no auth)")
    parser.add_argument("--port", type=int, default=8411, help="port (default 8411)")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help=f"result cache (default {DEFAULT_CACHE})")
    parser.add_argument("--no-cache", action="store_true", help="recompute every run")
    args = parser.parse_args(argv)
    ts.SHOW_PROGRESS = False  # the page shows progress instead
    server = serve(args.host, args.port, None if args.no_cache else args.cache_dir)
    host, port = server.server_address[:2]
    print(f"OS4 Model Lab on http://{'127.0.0.1' if host == '0.0.0.0' else host}:{port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
