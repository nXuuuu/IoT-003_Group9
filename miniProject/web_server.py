# =============================================================================
# web_server.py — ESP32 Hosted Web Dashboard
# Smart IoT Parking Management System
# =============================================================================
# The socket is created in main.py using the exact protocol:
#
#   addr = socket.getaddrinfo("0.0.0.0", 80)[0][-1]
#   s = socket.socket()
#   s.bind(addr)
#   s.listen(1)
#
# That socket is passed directly into WebServer(state, hw, sock) so
# there is no double-binding and it matches the expected protocol exactly.
#
# Pages / Endpoints:
#   GET  /           → Main dashboard HTML page
#   GET  /data       → Live JSON data (polled by dashboard every 3s)
#   POST /gate/open  → Open the gate
#   POST /gate/close → Close the gate
#   POST /light/on   → Turn lights ON
#   POST /light/off  → Turn lights OFF
# =============================================================================

import ujson
import config


class WebServer:
    """
    Lightweight non-blocking HTTP server for the parking dashboard.
    Receives a pre-bound socket from main.py — does not create its own.
    """

    def __init__(self, state, hardware, sock):
        """
        state    → shared ParkingState object
        hardware → dict of hardware drivers
        sock     → pre-bound, pre-listening socket from main.py
        """
        self.state = state
        self.hw    = hardware
        self.sock  = sock
        print("[Web] Server ready — waiting for connections")

    # ── HTML Dashboard Page ───────────────────────────────────────────────────

    def _html_page(self):
        """
        Full HTML dashboard page.
        JavaScript fetches /data every 3 seconds and updates the page
        without a full reload, keeping it responsive.
        ✏️  Edit the HTML/CSS below to customise the appearance.
        """
        s = self.state
        html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Parking</title>
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:Arial,sans-serif;background:#0f172a;color:#e2e8f0;padding:16px}
  h1{text-align:center;color:#38bdf8;font-size:20px;margin-bottom:16px}
  .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;max-width:680px;margin:0 auto 16px}
  .card{background:#1e293b;border-radius:10px;padding:14px;text-align:center;border:1px solid #334155}
  .label{font-size:10px;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px}
  .value{font-size:24px;font-weight:bold}
  .blue{color:#38bdf8} .green{color:#4ade80} .red{color:#f87171} .yellow{color:#fbbf24}
  .slots-row{display:flex;gap:10px;justify-content:center;max-width:680px;margin:0 auto 16px;flex-wrap:wrap}
  .slot{flex:1;min-width:100px;padding:12px;border-radius:8px;text-align:center;font-weight:bold;font-size:12px;border:2px solid}
  .free{background:#052e16;border-color:#4ade80;color:#4ade80}
  .occ{background:#450a0a;border-color:#f87171;color:#f87171}
  .btns{display:flex;flex-wrap:wrap;gap:10px;justify-content:center;max-width:680px;margin:0 auto}
  button{padding:10px 20px;border-radius:8px;border:none;font-size:13px;font-weight:bold;cursor:pointer}
  .btn-open{background:#4ade80;color:#052e16}
  .btn-close{background:#f87171;color:#450a0a}
  .btn-lon{background:#fbbf24;color:#451a03}
  .btn-loff{background:#475569;color:#e2e8f0}
  .footer{text-align:center;font-size:10px;color:#475569;margin-top:16px}
  #ts{color:#64748b;font-size:10px;text-align:center;margin-top:8px}
</style>
</head>
<body>
<h1>&#127358; Smart Parking Dashboard</h1>

<div class="grid">
  <div class="card">
    <div class="label">Available Slots</div>
    <div class="value blue" id="slots">""" + str(s.available_slots) + "/" + str(s.total_slots) + """</div>
  </div>
  <div class="card">
    <div class="label">Gate</div>
    <div class="value """ + ("green" if s.gate_open else "red") + """" id="gate">""" + ("OPEN" if s.gate_open else "CLOSED") + """</div>
  </div>
  <div class="card">
    <div class="label">Temperature</div>
    <div class="value yellow" id="temp">""" + str(round(s.temperature, 1)) + """&deg;C</div>
  </div>
  <div class="card">
    <div class="label">Humidity</div>
    <div class="value blue" id="hum">""" + str(round(s.humidity, 1)) + """%</div>
  </div>
  <div class="card">
    <div class="label">Lights</div>
    <div class="value """ + ("yellow" if s.light_on else "") + """" id="light">""" + ("ON" if s.light_on else "OFF") + """</div>
  </div>
</div>

<div class="slots-row" id="slotrow">"""

        for i in range(s.total_slots):
            css = "occ" if s.slot_status[i] else "free"
            label = "OCCUPIED" if s.slot_status[i] else "FREE"
            html += f'<div class="slot {css}" id="s{i+1}">Slot {i+1}<br>{label}</div>'

        html += """</div>

<div class="btns">
  <button class="btn-open"  onclick="cmd('/gate/open')">&#128275; Open Gate</button>
  <button class="btn-close" onclick="cmd('/gate/close')">&#128274; Close Gate</button>
  <button class="btn-lon"   onclick="cmd('/light/on')">&#128161; Lights ON</button>
  <button class="btn-loff"  onclick="cmd('/light/off')">&#127773; Lights OFF</button>
</div>

<div id="ts">Updating every 3 seconds...</div>
<div class="footer">Smart IoT Parking &middot; ESP32 MicroPython</div>

<script>
function cmd(url){
  fetch(url,{method:'POST'}).then(()=>refresh()).catch(console.log);
}
function refresh(){
  fetch('/data').then(r=>r.json()).then(d=>{
    document.getElementById('slots').textContent = d.available+'/'+d.total;
    var g = document.getElementById('gate');
    g.textContent = d.gate;
    g.className = 'value '+(d.gate==='OPEN'?'green':'red');
    document.getElementById('temp').innerHTML = d.temp+'&deg;C';
    document.getElementById('hum').textContent = d.hum+'%';
    var l = document.getElementById('light');
    l.textContent = d.light;
    l.className = 'value '+(d.light==='ON'?'yellow':'');
    for(var i=1;i<=d.total;i++){
      var el=document.getElementById('s'+i);
      var occ=d.slots[i-1];
      el.className='slot '+(occ?'occ':'free');
      el.innerHTML='Slot '+i+'<br>'+(occ?'OCCUPIED':'FREE');
    }
    document.getElementById('ts').textContent='Last updated: '+new Date().toLocaleTimeString();
  }).catch(console.log);
}
setInterval(refresh,3000);
</script>
</body></html>"""
        return html
        #return "<div></div>"

    # ── JSON Data Endpoint ────────────────────────────────────────────────────

    def _json_data(self):
        """Returns current system state as a JSON string for AJAX refresh."""
        s = self.state
        return ujson.dumps({
            "available": s.available_slots,
            "total":     s.total_slots,
            "slots":     s.slot_status,
            "gate":      "OPEN" if s.gate_open else "CLOSED",
            "light":     "ON"   if s.light_on  else "OFF",
            "temp":      round(s.temperature, 1),
            "hum":       round(s.humidity,    1),
        })

    # ── Request Router ────────────────────────────────────────────────────────

    def _handle(self, client):
        """
        Reads one HTTP request, routes it, sends response, closes connection.
        All in one call — keeps memory usage low on ESP32.
        """
        try:
            raw = client.recv(1024).decode("utf-8")
            if not raw:
                return

            # Parse method and path from HTTP request first line
            # e.g. "GET / HTTP/1.1" → method="GET", path="/"
            first_line = raw.split("\r\n")[0]
            parts = first_line.split(" ")
            if len(parts) < 2:
                return
            method = parts[0]
            path   = parts[1]

            if config.DEBUG_MODE:
                print("[Web]", method, path)

            # ── Route ─────────────────────────────────────────────────────
            if method == "GET" and path == "/":
                self._respond(client, "200 OK", "text/html", self._html_page())

            elif method == "GET" and path == "/data":
                self._respond(client, "200 OK", "application/json", self._json_data())

            elif method == "POST" and path == "/gate/open":
                self.hw['servo'].open()
                self.state.gate_open = True
                self._respond(client, "200 OK", "application/json", '{"ok":true}')

            elif method == "POST" and path == "/gate/close":
                self.hw['servo'].close()
                self.state.gate_open = False
                self._respond(client, "200 OK", "application/json", '{"ok":true}')

            elif method == "POST" and path == "/light/on":
                self.hw['relay'].turn_on()
                self.state.light_on = True
                self._respond(client, "200 OK", "application/json", '{"ok":true}')

            elif method == "POST" and path == "/light/off":
                self.hw['relay'].turn_off()
                self.state.light_on = False
                self._respond(client, "200 OK", "application/json", '{"ok":true}')

            else:
                self._respond(client, "404 Not Found", "text/plain", "Not Found")

        except Exception as e:
            print("[Web] Handle error:", e)
        finally:
            client.close()

    def _respond(self, client, status, content_type, body):
        """Sends a complete HTTP response."""
        header = (
            "HTTP/1.1 " + status + "\r\n"
            "Content-Type: " + content_type + "\r\n"
            "Content-Length: " + str(len(body)) + "\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        client.sendall((header + body).encode("utf-8"))

    # ── Poll (called from main loop) ──────────────────────────────────────────

    def poll(self):
        """
        Checks for a waiting HTTP connection and handles it.
        Non-blocking — returns immediately if no client is waiting.
        The socket timeout (0.1s) set in main.py ensures this doesn't block.
        """
        if not self.sock:
            return
        try:
            client, addr = self.sock.accept()
            if config.DEBUG_MODE:
                print("[Web] Client:", addr)
            client.settimeout(3)
            self._handle(client)
        except OSError:
            pass  # Timeout — no connection waiting, completely normal

