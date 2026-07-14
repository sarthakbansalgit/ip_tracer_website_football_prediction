# World Cup Predictions — Research Traffic Logger

A simple, transparent setup for logging visitor traffic to the World Cup
Predictions page, for use in your research project.

## Files
- `index.html` — the page itself (includes a small notice at the bottom
  disclosing that visits are logged, which is good practice to show your
  professor you considered research ethics/consent).
- `server.py` — a Python web server that serves `index.html` and logs
  every request's IP address, timestamp, method/path, user-agent, and
  referrer to `access_log.csv`.
- `analyze_log.py` — a script that reads `access_log.csv` and prints
  summary stats: total requests, unique visitor IPs, visits per IP,
  visits per hour, top browsers/user-agents, and (optionally) approximate
  geolocation per IP using the free ip-api.com lookup service.

## How to run

1. Make sure you have Python 3 installed.
2. From this folder, start the server:
   ```
   python3 server.py 8000
   ```
3. Open `http://localhost:8000/` in a browser to view the page (or share
   your machine's local network address / a public URL if deploying
   elsewhere, e.g. on a VPS or a service like Render/Railway/PythonAnywhere).
4. Every visit gets appended to `access_log.csv` automatically.
5. To analyze the collected data:
   ```
   python3 analyze_log.py
   ```
   This prints a summary report, and can optionally do IP geolocation
   lookups (needs internet access).

## Why this approach (for your writeup)

This mirrors exactly how real web servers (Apache, nginx, etc.) log
traffic by default — it's the standard, industry-normal method used in
web analytics research, rather than a covert client-side script. Because
the page discloses that visits are logged, this keeps the project on
solid ethical footing, which is usually something professors check for
in research methodology.

## Notes / limitations
- `access_log.csv` grows with every request — you may want to rotate or
  archive it periodically for a long-running study.
- IP geolocation via ip-api.com is approximate (usually city/region level,
  not exact address) and free-tier rate-limited (~45 requests/minute).
- If you deploy this publicly, make sure your deployment complies with
  your institution's research ethics guidelines (e.g. IRB) if you're
  collecting data from real, non-consenting members of the public.
