from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(prog="d2rhelper")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")

    args = parser.parse_args()

    import uvicorn

    host = os.environ.get("D2RHELPER_HOST", args.host)
    port = int(os.environ.get("D2RHELPER_PORT", str(args.port)))

    if args.reload:
        uvicorn.run("d2rhelper.api:app", host=host, port=port, reload=True)
    else:
        uvicorn.run("d2rhelper.api:app", host=host, port=port)
