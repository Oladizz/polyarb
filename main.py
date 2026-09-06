"""
Main application entrypoint for PolyArb.
Runs the web dashboard and REST server by default.
"""
import sys

from app.api.server import app
from app.core.config import PORT

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("--scan", "--research", "--paper", "--daemon"):
        from cli import main as cli_main
        cli_main()
    else:
        print(f"🦅 PolyArb Server starting on port {PORT}...")
        app.run(host="0.0.0.0", port=PORT)
