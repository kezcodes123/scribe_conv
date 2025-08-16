#!/usr/bin/env python3
"""
Unified launcher for the Scribe optimizer UI.

Tries to start the Tkinter desktop GUI first; if that fails (e.g., macOS Tk not available),
falls back to starting the local web UI and opens it in a browser.

Run: python -m scribe_tools.app
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser


def _try_tk_subprocess() -> bool:
    # Run the Tkinter GUI in a child process; if it aborts due to Tk issues,
    # we can still fall back to the web UI here.
    try:
        cmd = [sys.executable, "-m", "scribe_tools.gui"]
        res = subprocess.run(cmd)
        return res.returncode == 0
    except Exception:
        return False


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _start_web() -> None:
    from . import web_ui

    port = _free_port()

    def run():
        web_ui.run(host="127.0.0.1", port=port, debug=False)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    time.sleep(0.6)
    webbrowser.open(f"http://127.0.0.1:{port}")
    t.join()


def main() -> None:
    if os.environ.get("SCRIBE_UI_FORCE_WEB") == "1":
        _start_web()
        return
    ok = _try_tk_subprocess()
    if not ok:
        _start_web()


if __name__ == "__main__":
    main()
