#!/usr/bin/env python3
"""Local HTTP server that redirects http://localhost:19280/task/... to pablo://task/..."""

import http.server

PORT = 19280


class PabloRedirectHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/task/"):
            pablo_url = f"pablo://{self.path.lstrip('/')}"
            self.send_response(302)
            self.send_header("Location", pablo_url)
            self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Use /task/Your+Task+Title")

    def log_message(self, format, *args):
        pass  # silent


def main():
    server = http.server.HTTPServer(("127.0.0.1", PORT), PabloRedirectHandler)
    print(f"Pablo redirect server on http://localhost:{PORT}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    server.server_close()


if __name__ == "__main__":
    main()
