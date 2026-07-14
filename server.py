"""
Detailed research web server for the World Cup Predictions page.

For every visit, logs:
- timestamp (UTC)
- real visitor IP (handles reverse proxy via X-Forwarded-For)
- approximate geolocation: city, region, country, ISP/org, lat/long
  (via the free ip-api.com lookup, no key required)
- device/browser/OS info parsed from the User-Agent string
- HTTP method, path requested, referrer

Logs are written to access_log.csv (raw data) and viewable in a clean
HTML table at /logs (no need to open a CSV manually).

This is transparent, server-side logging (disclosed on the page itself)
- the same category of data every web server logs by default - just
enriched with geolocation and device parsing for research purposes.

Usage:
    python3 server.py [port]
    (On Render/Railway/Heroku, the PORT env var is used automatically.)
"""

import csv
import html
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_log.csv")
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

FIELDNAMES = [
    "timestamp_utc", "ip_address", "city", "region", "country",
    "isp_org", "latitude", "longitude", "device_type", "os", "browser",
    "method", "path", "referrer",
]


def ensure_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def is_private_ip(ip):
    return (
        ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("::1")
        or ip == "localhost"
        or ip.startswith("172.16.")
    )


def geolocate(ip):
    """Look up approximate location + ISP for a public IP via ip-api.com."""
    if is_private_ip(ip):
        return {"city": "-", "region": "-", "country": "-", "isp": "local/private IP", "lat": "-", "lon": "-"}
    try:
        url = f"http://ip-api.com/json/{ip}?fields=status,city,regionName,country,isp,lat,lon"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        if data.get("status") == "success":
            return {
                "city": data.get("city", "-"),
                "region": data.get("regionName", "-"),
                "country": data.get("country", "-"),
                "isp": data.get("isp", "-"),
                "lat": data.get("lat", "-"),
                "lon": data.get("lon", "-"),
            }
    except Exception:
        pass
    return {"city": "unknown", "region": "unknown", "country": "unknown", "isp": "unknown", "lat": "-", "lon": "-"}


def parse_user_agent(ua):
    """Lightweight User-Agent parsing - no external dependencies needed."""
    ua_l = ua.lower()

    # Device type
    if "mobile" in ua_l or "iphone" in ua_l or "android" in ua_l:
        device = "Mobile"
    elif "ipad" in ua_l or "tablet" in ua_l:
        device = "Tablet"
    else:
        device = "Desktop"

    # OS
    if "windows" in ua_l:
        os_name = "Windows"
    elif "mac os" in ua_l or "macintosh" in ua_l:
        os_name = "macOS"
    elif "android" in ua_l:
        os_name = "Android"
    elif "iphone" in ua_l or "ipad" in ua_l or "ios" in ua_l:
        os_name = "iOS"
    elif "linux" in ua_l:
        os_name = "Linux"
    else:
        os_name = "Unknown"

    # Browser
    if "edg/" in ua_l:
        browser = "Edge"
    elif "chrome/" in ua_l and "chromium" not in ua_l:
        browser = "Chrome"
    elif "safari/" in ua_l and "chrome" not in ua_l:
        browser = "Safari"
    elif "firefox/" in ua_l:
        browser = "Firefox"
    else:
        browser = "Unknown"

    return device, os_name, browser


class LoggingHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def get_real_ip(self):
        # Render (and most hosts) sit behind a reverse proxy, so the direct
        # TCP connection appears to come from the proxy itself. The real
        # visitor IP is passed in X-Forwarded-For (first entry in the chain).
        forwarded = self.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return self.client_address[0]

    def log_visit(self):
        ip = self.get_real_ip()
        ts = datetime.now(timezone.utc).isoformat()
        user_agent = self.headers.get("User-Agent", "-")
        referrer = self.headers.get("Referer", "-")
        device, os_name, browser = parse_user_agent(user_agent)
        geo = geolocate(ip)

        row = {
            "timestamp_utc": ts,
            "ip_address": ip,
            "city": geo["city"],
            "region": geo["region"],
            "country": geo["country"],
            "isp_org": geo["isp"],
            "latitude": geo["lat"],
            "longitude": geo["lon"],
            "device_type": device,
            "os": os_name,
            "browser": browser,
            "method": self.command,
            "path": self.path,
            "referrer": referrer,
        }

        with open(LOG_FILE, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow(row)

    def do_GET(self):
        if self.path == "/logs":
            self.log_visit()
            self.serve_logs_html()
            return
        if self.path == "/logs.csv":
            self.log_visit()
            self.serve_logs_csv()
            return
        self.log_visit()
        super().do_GET()

    def serve_logs_csv(self):
        """Raw CSV download."""
        try:
            with open(LOG_FILE, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", "attachment; filename=access_log.csv")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"No log file found yet.")

    def serve_logs_html(self):
        """Human-readable table view of all logged visits, newest first."""
        rows = []
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        rows.reverse()

        table_rows = ""
        for r in rows:
            table_rows += "<tr>" + "".join(
                f"<td>{html.escape(str(r.get(k, '-')))}</td>" for k in FIELDNAMES
            ) + "</tr>\n"

        header_cells = "".join(f"<th>{h}</th>" for h in FIELDNAMES)

        page = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><title>Access Logs</title>
<style>
body {{ font-family: monospace; background:#0d1117; color:#c9d1d9; padding:20px; }}
h1 {{ color:#58a6ff; }}
table {{ border-collapse: collapse; width: 100%; font-size: 13px; }}
th, td {{ border: 1px solid #30363d; padding: 6px 10px; text-align: left; white-space: nowrap; }}
th {{ background:#161b22; color:#58a6ff; position: sticky; top: 0; }}
tr:nth-child(even) {{ background:#161b22; }}
.count {{ color:#8b949e; margin-bottom: 15px; }}
a {{ color:#58a6ff; }}
</style></head>
<body>
<h1>Visit Log — World Cup Predictions (Research)</h1>
<p class="count">Total visits logged: {len(rows)} &nbsp;|&nbsp; <a href="/logs.csv">Download raw CSV</a> &nbsp;|&nbsp; <a href="/">Back to site</a></p>
<div style="overflow-x:auto;">
<table>
<thead><tr>{header_cells}</tr></thead>
<tbody>
{table_rows}
</tbody>
</table>
</div>
</body></html>"""

        content = page.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_POST(self):
        self.log_visit()
        super().do_POST()

    def log_message(self, format, *args):
        pass


def main():
    port = int(os.environ.get("PORT", sys.argv[1] if len(sys.argv) > 1 else 8000))
    ensure_log_file()
    server = ThreadingHTTPServer(("0.0.0.0", port), LoggingHandler)
    print(f"Serving World Cup Predictions page on http://0.0.0.0:{port}/")
    print(f"View logs at /logs (HTML) or /logs.csv (raw download)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
