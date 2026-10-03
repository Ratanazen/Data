#!/usr/bin/env python3
"""
Cross-Platform Web Server for Log File Analysis Dashboard
=========================================================
Runs identically on Windows, macOS, and Linux.

Usage:
    python serve.py [port] [--open]
"""

import sys
import os
import socket
import webbrowser
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 8080
BASE_DIR = Path(__file__).resolve().parent

class CrossPlatformHandler(SimpleHTTPRequestHandler):
    # Explicit MIME types map to prevent Windows Registry MIME misconfigurations
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        '.svg': 'image/svg+xml',
        '.json': 'application/json',
        '.js': 'application/javascript',
        '.css': 'text/css',
        '.html': 'text/html; charset=utf-8',
        '.csv': 'text/csv; charset=utf-8',
        '.png': 'image/png',
        '.ico': 'image/x-icon',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        # Enable CORS and disable caching during interactive development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) != 0

def find_open_port(start_port=DEFAULT_PORT):
    port = start_port
    while port < start_port + 100:
        if is_port_available(port):
            return port
        port += 1
    return start_port

def run_server(port=None, auto_open=False):
    os.chdir(BASE_DIR)
    
    # Parse CLI flags
    args = sys.argv[1:]
    for arg in args:
        if arg.isdigit():
            port = int(arg)
        elif arg in ('--open', '-o'):
            auto_open = True
        elif arg.startswith('--port='):
            port = int(arg.split('=')[1])

    if port is None:
        port = find_open_port(DEFAULT_PORT)

    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, CrossPlatformHandler)
    httpd.timeout = 0.5  # Allows responsive KeyboardInterrupt on Windows

    local_url = f"http://localhost:{port}/"
    print("=" * 70)
    print("  🚀 LOG FILE ANALYSIS — INTERACTIVE WEB DASHBOARD")
    print("=" * 70)
    print(f"  Local URL    : {local_url}")
    print(f"  Network URL  : http://127.0.0.1:{port}/")
    print(f"  Serving Dir  : {BASE_DIR}")
    print("  Platform     :", sys.platform.title())
    print("  Press Ctrl+C to stop the server.")
    print("=" * 70)

    if auto_open:
        try:
            webbrowser.open(local_url)
        except Exception:
            pass

    try:
        while True:
            httpd.handle_request()
    except KeyboardInterrupt:
        print("\n[*] Server shutdown cleanly.")
    finally:
        httpd.server_close()

def main():
    run_server()

if __name__ == '__main__':
    main()
