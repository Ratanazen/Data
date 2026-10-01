#!/usr/bin/env python3
"""
Web Server for Log File Analysis Dashboard
==========================================
Usage:
    python3 serve.py [port]

Default port: 8080 (automatically finds an available port if busy)
"""

import sys
import os
import socket
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_PORT = 8080

class CustomHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS and disable aggressive caching for live development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

def is_port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) != 0

def find_open_port(start_port=DEFAULT_PORT):
    port = start_port
    while port < start_port + 100:
        if is_port_available(port):
            return port
        port += 1
    return start_port

def run_server(port=None):
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if port is None:
        if len(sys.argv) > 1 and sys.argv[1].isdigit():
            port = int(sys.argv[1])
        else:
            port = find_open_port(DEFAULT_PORT)

    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, CustomHandler)

    print("=" * 68)
    print("  🚀 LOG FILE ANALYSIS — INTERACTIVE WEB DASHBOARD")
    print("=" * 68)
    print(f"  Local URL    : http://localhost:{port}/")
    print(f"  Network URL  : http://127.0.0.1:{port}/")
    print("  Serving Dir  :", os.getcwd())
    print("  Press Ctrl+C to stop the server.")
    print("=" * 68)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Server stopped.")

if __name__ == '__main__':
    run_server()
