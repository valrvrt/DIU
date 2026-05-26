#!/usr/bin/env python3
"""Start the DUNE: Imperium Uprising web UI.

Usage:
    python3 run_ui.py          # default port 8000
    python3 run_ui.py --port 9000
"""
import sys
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()

    try:
        import uvicorn
    except ImportError:
        print("uvicorn not installed.  Run:  pip install fastapi uvicorn")
        sys.exit(1)

    print(f"\n  DUNE: Imperium Uprising Web UI")
    print(f"  ─────────────────────────────")
    print(f"  Open http://localhost:{args.port} in your browser\n")
    uvicorn.run(
        "ui.api:app",
        host=args.host,
        port=args.port,
        reload=False,
        log_level="warning",
    )

if __name__ == "__main__":
    main()
