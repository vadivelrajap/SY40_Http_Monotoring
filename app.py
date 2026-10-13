import os
import json
import time
from datetime import datetime, timezone
from threading import Lock
from flask import Flask, request, jsonify, render_template_string, abort

app = Flask(__name__)
DEVICE_ID = os.getenv("DEVICE_ID", "0C117F0561A4")
INGEST_TOKEN = os.getenv("INGEST_TOKEN", "change-this-token")
DASHBOARD_USER = os.getenv("DASHBOARD_USER", "")
DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "")
lock = Lock()
latest = {"device_id": DEVICE_ID, "last_seen": None, "received_at": None,
          "request_count": 0, "remote_ip": None, "content_type": None,
          "payload": None, "history": []}

def utc_now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

def dashboard_auth():
    if not DASHBOARD_USER or not DASHBOARD_PASSWORD:
        return
    auth = request.authorization
    if not auth or auth.username != DASHBOARD_USER or auth.password != DASHBOARD_PASSWORD:
        return abort(401, www_authenticate='Basic realm="SY-40 Monitor"')

@app.before_request
def protect_dashboard():
    if request.path in ("/", "/api/status", "/api/history"):
        dashboard_auth()

@app.get("/")
def dashboard():
    return render_template_string(HTML, device_id=DEVICE_ID)

@app.get("/health")
def health():
    return jsonify({"ok": True, "service": "SY-40 HTTP monitor"})

@app.route("/ingest/<token>", methods=["GET", "POST"])
def ingest(token):
    if token != INGEST_TOKEN:
        abort(404)
    raw = request.get_data(as_text=True)
    try:
        payload = request.get_json(silent=True)
        if payload is None and raw:
            payload = {"raw_text": raw}
    except Exception:
        payload = {"raw_text": raw}
    if payload is None:
        payload = dict(request.args)

    received = utc_now()
    with lock:
        latest["last_seen"] = time.time()
        latest["received_at"] = received
        latest["request_count"] += 1
        latest["remote_ip"] = request.headers.get("X-Forwarded-For", request.remote_addr)
        latest["content_type"] = request.content_type
        latest["payload"] = payload
        latest["history"].insert(0, {"time": received, "ip": latest["remote_ip"], "payload": payload})
        latest["history"] = latest["history"][:50]
    return jsonify({"ok": True, "device_id": DEVICE_ID, "received_at": received})

@app.get("/api/status")
def api_status():
    with lock:
        result = dict(latest)
    seen = result.get("last_seen")
    result["online"] = bool(seen and (time.time() - seen) <= 150)
    result.pop("history", None)
    result.pop("last_seen", None)
    return jsonify(result)

@app.get("/api/history")
def api_history():
    with lock:
        return jsonify(latest["history"])

HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SY-40 Modem Monitor</title>
<style>
:root{font-family:Inter,Segoe UI,Arial,sans-serif;color:#172033;background:#f3f6fb}
body{margin:0}.top{background:#14243a;color:white;padding:24px max(20px,calc((100% - 1100px)/2))}
main{max-width:1100px;margin:24px auto;padding:0 16px}.muted{color:#667085}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px}
.card{background:white;border:1px solid #e1e7f0;border-radius:14px;padding:18px;box-shadow:0 2px 8px #14243a0a}
.label{font-size:13px;color:#667085}.value{font-size:24px;font-weight:700;margin-top:9px;overflow-wrap:anywhere}
.pill{display:inline-block;border-radius:99px;padding:5px 10px;font-size:13px;font-weight:700}
.online{background:#d9fbe5;color:#126534}.offline{background:#fee2e2;color:#991b1b}
pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#101828;color:#e4ecf7;padding:16px;border-radius:10px;max-height:360px;overflow:auto}
table{width:100%;border-collapse:collapse}td,th{text-align:left;padding:10px;border-bottom:1px solid #edf0f5;vertical-align:top;font-size:13px}
button{padding:9px 13px;border:1px solid #d0d5dd;border-radius:8px;background:white;cursor:pointer}
</style></head>
<body>
<header class="top"><h1 style="margin:0 0 6px">📡 SY-40 4G Modem Monitor</h1>
<div style="opacity:.8">Device ID: {{ device_id }} · Auto-refresh every 10 seconds</div></header>
<main>
<div class="grid">
 <section class="card"><div class="label">Connection status</div><div class="value" id="status">Waiting…</div></section>
 <section class="card"><div class="label">Last HTTP update</div><div class="value" style="font-size:18px" id="last">—</div></section>
 <section class="card"><div class="label">Requests received</div><div class="value" id="count">0</div></section>
 <section class="card"><div class="label">Latest request source IP</div><div class="value" style="font-size:18px" id="ip">—</div></section>
</div>
<section class="card" style="margin-top:16px"><h3 style="margin-top:0">Latest modem payload</h3><div class="muted" style="margin-bottom:10px">The exact fields depend on the SY-40 firmware's HTTP State Detection format.</div><pre id="payload">Waiting for first modem request…</pre></section>
<section class="card" style="margin-top:16px"><div style="display:flex;justify-content:space-between;align-items:center;gap:10px"><h3 style="margin:0">Recent requests</h3><button onclick="refreshData()">Refresh now</button></div>
<div style="overflow:auto;margin-top:10px"><table><thead><tr><th>Received at (UTC)</th><th>Source IP</th><th>Payload</th></tr></thead><tbody id="history"></tbody></table></div></section>
<p class="muted" style="font-size:12px">Prototype monitor. “Online” means an HTTP request arrived within 150 seconds; it does not independently test mobile-network reachability.</p>
</main>
<script>
async function refreshData(){
 try{
  const r=await fetch('/api/status',{cache:'no-store'}), d=await r.json();
  document.getElementById('status').innerHTML=d.online?'<span class="pill online">ONLINE</span>':'<span class="pill offline">OFFLINE / NO RECENT DATA</span>';
  document.getElementById('last').textContent=d.received_at||'No data yet';
  document.getElementById('count').textContent=d.request_count||0;
  document.getElementById('ip').textContent=d.remote_ip||'—';
  document.getElementById('payload').textContent=d.payload===null?'Waiting for first modem request…':JSON.stringify(d.payload,null,2);
  const hr=await fetch('/api/history',{cache:'no-store'}), rows=await hr.json();
  document.getElementById('history').innerHTML=rows.map(x=>'<tr><td>'+esc(x.time)+'</td><td>'+esc(x.ip||'—')+'</td><td>'+esc(JSON.stringify(x.payload))+'</td></tr>').join('')||'<tr><td colspan="3">No requests received yet.</td></tr>';
 }catch(e){document.getElementById('status').textContent='Dashboard API unavailable';}
}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
refreshData();setInterval(refreshData,10000);
</script></body></html>
"""

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
