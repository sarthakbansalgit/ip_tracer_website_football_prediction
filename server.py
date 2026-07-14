"""
Simple research web server for the World Cup Predictions page.

Serves index.html and logs every incoming request's:
- timestamp
- client IP address
- HTTP method + path requested
- User-Agent string
- Referrer (if any)

Logs are written to access_log.csv in the same folder, one row per request.
This is the standard way web servers (Apache/nginx/etc.) capture visitor
data for traffic analysis - it's transparent (see the notice on the page
itself) and doesn't do any covert fingerprinting or tracking beyond what
every web server does by default.

Usage:
    python3 server.py [port]

Default port is 8000. Then visit http://localhost:8000/ in a browser,
or share the machine's address with others on your network for testing.
"""

import csv
import os
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_log.csv")
DIRECTORY = os.path.dirname(os.path.abspath(__file__))


def ensure_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["timestamp_utc", "ip_address", "method", "path", "user_agent", "referrer"]
            )


class LoggingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def log_visit(self):
        ip = self.client_address[0]
        ts = datetime.now(timezone.utc).isoformat()
        user_agent = self.headers.get("User-Agent", "-")
        referrer = self.headers.get("Referer", "-")

        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([ts, ip, self.command, self.path, user_agent, referrer])

    def do_GET(self):
        self.log_visit()
        super().do_GET()

    def do_POST(self):
        self.log_visit()
        super().do_POST()

    # Quiet down default console logging noise; we log to CSV instead.
    def log_message(self, format, *args):
        pass


def main():
    # Render/Railway/Heroku-style hosts inject the port via the PORT env var.
    # Falls back to a command-line arg (for local testing) or 8000 by default.
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))
    ensure_log_file()
    server = ThreadingHTTPServer(("0.0.0.0", port), LoggingHandler)
    print(f"Serving World Cup Predictions page on http://0.0.0.0:{port}/")
    print(f"Logging visits to: {LOG_FILE}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
