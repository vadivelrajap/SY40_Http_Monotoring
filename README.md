# SY-40 HTTP Monitor (free starter)

A small Flask HTTP receiver and browser dashboard for the SY-40 modem's HTTP/JSON State Detection feature.

## What it does
- Accepts GET or POST requests at `/ingest/<INGEST_TOKEN>`
- Captures JSON, query parameters, or raw request text
- Shows latest payload, last received time, request count, source IP and last 50 requests
- Marks the modem ONLINE if a request arrived within 150 seconds
- Optional Basic Auth for the dashboard using `DASHBOARD_USER` and `DASHBOARD_PASSWORD`

## Important limitations
This starter stores data in process memory. A restart or redeploy clears the request history and last status. It is suitable for initial testing, not permanent monitoring. Add a persistent database before relying on it for production.
A free Render service may sleep after 15 minutes without inbound traffic and can take about a minute to wake. A modem sending every 60 seconds should normally keep it active, but hosting is not an uptime guarantee.

## Deploy to Render (free)
1. Create a GitHub repository and upload these files.
2. Sign in to Render and create a new Blueprint from that repository, or create a Python Web Service.
3. Use build command `pip install -r requirements.txt` and start command `gunicorn app:app`.
4. Set environment variables:
   - `DEVICE_ID` = `0C117F0561A4`
   - `INGEST_TOKEN` = a long random secret string
   - `DASHBOARD_USER` = a username
   - `DASHBOARD_PASSWORD` = a strong password
5. After deploy, test `https://YOUR-SERVICE.onrender.com/health`.
6. The modem's HTTP State Detection URL/path must target:
   `https://YOUR-SERVICE.onrender.com/ingest/YOUR_INGEST_TOKEN`
   Use the modem's supported URL/path fields. If its UI accepts only a host and a separate path, put the host in the server field and `/ingest/YOUR_INGEST_TOKEN` in the path field.
7. Open the service root URL to view the dashboard. The browser will ask for the dashboard username/password.

## Local test
```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
set INGEST_TOKEN=my-test-token
set DASHBOARD_USER=admin
set DASHBOARD_PASSWORD=change-me
python app.py
```
Open `http://127.0.0.1:8080/health`, then send a test:
```bash
curl -X POST http://127.0.0.1:8080/ingest/my-test-token ^
  -H "Content-Type: application/json" ^
  -d "{\"device_id\":\"0C117F0561A4\",\"signal\":64}"
```
On Windows PowerShell, use `curl.exe` or a REST client if `curl` is aliased.

## Next step
After the first real modem request arrives, inspect the exact JSON payload and tailor the dashboard to the fields the modem actually sends (signal strength, cellular registration, WAN IP, uptime, etc.). The current starter deliberately displays unknown fields as raw JSON rather than guessing their names.
