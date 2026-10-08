"""RAMPulse - Memory Dashboard & Process Monitor Launcher.

Usage:
    python run.py
    python run.py --port 8080 --no-browser
"""

import argparse
import socket
import sys
import threading
import time
import webbrowser

import uvicorn


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if the specified port is open for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def find_available_port(start_port: int = 8000, max_attempts: int = 20) -> int:
    """Find the next free port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if is_port_available(p):
            return p
    return start_port


def open_browser_delayed(url: str, delay_seconds: float = 1.2):
    """Open default web browser after server initializes."""
    def _open():
        time.sleep(delay_seconds)
        try:
            webbrowser.open(url)
        except Exception:
            pass

    threading.Thread(target=_open, daemon=True).start()


def main():
    parser = argparse.ArgumentParser(description="RAMPulse - Real-Time Memory Dashboard & Monitor")
    parser.add_argument("--host", default="127.0.0.1", help="Host interface to bind (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port to listen on (default: 8000)")
    parser.add_argument("--no-browser", action="store_true", help="Do not automatically launch web browser")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")

    args = parser.parse_args()

    port = args.port
    if not is_port_available(port, args.host):
        alt_port = find_available_port(port)
        print(f"[!] Port {port} is occupied. Using available port {alt_port} instead.")
        port = alt_port

    url = f"http://{args.host}:{port}"

    print("=" * 64)
    print(r"""
  ____      _    __  __ ____        _          
 |  _ \    / \  |  \/  |  _ \ _   _| |___  ___ 
 | |_) |  / _ \ | |\/| | |_) | | | | / __|/ _ \
 |  _ <  / ___ \| |  | |  __/| |_| | \__ \  __/
 |_| \_\/_/   \_\_|  |_|_|    \__,_|_|___/\___|
    """)
    print("  Real-Time Memory Dashboard & Process Monitor")
    print("=" * 64)
    print(f"  * Web Dashboard:   {url}")
    print(f"  * API Docs (OpenAPI): {url}/docs")
    print(f"  * Live WebSocket:  ws://{args.host}:{port}/ws/live")
    print("=" * 64)
    print("  Press CTRL+C in this terminal to stop the monitor.")
    print("=" * 64 + "\n")

    if not args.no_browser:
        open_browser_delayed(url)

    try:
        uvicorn.run(
            "src.app:app",
            host=args.host,
            port=port,
            reload=args.reload,
            log_level="info",
        )
    except KeyboardInterrupt:
        print("\n[+] RAMPulse server shut down gracefully.")
        sys.exit(0)


if __name__ == "__main__":
    main()
