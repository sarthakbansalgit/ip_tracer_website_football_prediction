"""
Analyze access_log.csv produced by server.py.

Prints summary statistics useful for a research writeup:
- total requests
- unique visitors (by IP)
- visits per IP (sorted, most frequent first)
- visits over time (per hour)
- top user agents / browsers
- approximate geolocation per unique IP (uses the free ip-api.com API,
  requires internet access; skips private/local IPs automatically)

Usage:
    python3 analyze_log.py [path_to_access_log.csv]
"""

import csv
import sys
import os
import json
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

DEFAULT_LOG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_log.csv")


def is_private_ip(ip):
    return (
        ip.startswith("127.")
        or ip.startswith("10.")
        or ip.startswith("192.168.")
        or ip.startswith("::1")
        or ip == "localhost"
    )


def geolocate(ip):
    """Look up approximate location for a public IP using ip-api.com (free, no key)."""
    if is_private_ip(ip):
        return {"status": "skipped", "reason": "private/local IP"}
    try:
        url = f"http://ip-api.com/json/{ip}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        return {"status": "error", "reason": str(e)}


def main():
    log_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_LOG

    if not os.path.exists(log_path):
        print(f"No log file found at {log_path}. Run server.py first and get some visits.")
        return

    rows = []
    with open(log_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        print("Log file is empty — no visits recorded yet.")
        return

    total_requests = len(rows)
    ip_counter = Counter(r["ip_address"] for r in rows)
    unique_ips = len(ip_counter)
    ua_counter = Counter(r["user_agent"] for r in rows)
    hourly = defaultdict(int)
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["timestamp_utc"])
            hourly[ts.strftime("%Y-%m-%d %H:00")] += 1
        except Exception:
            pass

    print("=" * 60)
    print("WORLD CUP PREDICTIONS PAGE — ACCESS LOG SUMMARY")
    print("=" * 60)
    print(f"Total requests logged : {total_requests}")
    print(f"Unique visitor IPs    : {unique_ips}")
    print()

    print("-- Visits per IP (top 20) --")
    for ip, count in ip_counter.most_common(20):
        print(f"  {ip:<20} {count} visit(s)")
    print()

    print("-- Visits per hour (UTC) --")
    for hour in sorted(hourly):
        print(f"  {hour}: {hourly[hour]}")
    print()

    print("-- Top user agents --")
    for ua, count in ua_counter.most_common(5):
        short_ua = (ua[:70] + "...") if len(ua) > 70 else ua
        print(f"  ({count}x) {short_ua}")
    print()

    do_geo = input("Run IP geolocation lookups for unique IPs? (uses internet, y/n): ").strip().lower()
    if do_geo == "y":
        print()
        print("-- Approximate geolocation per unique IP --")
        for ip in ip_counter:
            geo = geolocate(ip)
            if geo.get("status") == "success":
                print(f"  {ip}: {geo.get('city')}, {geo.get('regionName')}, {geo.get('country')} "
                      f"(ISP: {geo.get('isp')})")
            else:
                print(f"  {ip}: {geo.get('reason', geo.get('status'))}")


if __name__ == "__main__":
    main()
