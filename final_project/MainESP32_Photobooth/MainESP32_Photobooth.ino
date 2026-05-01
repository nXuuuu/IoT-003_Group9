#include <WiFi.h>
#include <WebServer.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <hd44780.h>
#include <hd44780ioClass/hd44780_I2Cexp.h>
#include <Adafruit_NeoPixel.h>

// ── CONFIG — fill these in ──────────────────────────────────
const char* WIFI_SSID     = "";
const char* WIFI_PASSWORD = "";
const char* ESP32CAM_IP   = "";  // ← set after ESP32-CAM boots
const int   ESP32CAM_PORT = 80;
const int   NUM_LEDS      = 24;
// ────────────────────────────────────────────────────────────

#define LED_PIN    5
#define BUZZER_PIN 18
#define TRIG_PIN   27
#define ECHO_PIN   14
#define LCD_COLS   16
#define LCD_ROWS   2
#define DIST_MIN_CM 100

hd44780_I2Cexp lcd;
Adafruit_NeoPixel leds(NUM_LEDS, LED_PIN, NEO_GRB + NEO_KHZ800);
WebServer server(80);

volatile bool isCounting = false;

// ── Hardware helpers ─────────────────────────────────────────
void ledsSet(uint8_t r, uint8_t g, uint8_t b) {
  for (int i = 0; i < NUM_LEDS; i++)
    leds.setPixelColor(i, leds.Color(r, g, b));
  leds.show();
}
void ledsOff() { ledsSet(0, 0, 0); }

void beep(int ms = 80) {
  digitalWrite(BUZZER_PIN, HIGH);
  delay(ms);
  digitalWrite(BUZZER_PIN, LOW);
}

void lcdShow(const char* row0, const char* row1) {
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(row0);
  lcd.setCursor(0, 1); lcd.print(row1);
}

// ── HC-SR04 ──────────────────────────────────────────────────
float measureDistanceCm() {
  digitalWrite(TRIG_PIN, LOW);  delayMicroseconds(2);
  digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  long d = pulseIn(ECHO_PIN, HIGH, 30000);
  return (d == 0) ? -1 : (d / 2.0) / 29.1;
}

// ── WiFi ─────────────────────────────────────────────────────
void wifiConnect() {
  lcdShow("WiFi...", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int r = 0;
  while (WiFi.status() != WL_CONNECTED && r++ < 20) delay(1000);
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi OK: "); Serial.println(WiFi.localIP());
  } else {
    lcdShow("WiFi FAILED", "Restarting...");
    delay(2000); ESP.restart();
  }
}

// ── Trigger ESP32-CAM capture ────────────────────────────────
bool triggerCam() {
  HTTPClient http;
  String url = "http://"; url += ESP32CAM_IP; url += "/capture";
  http.begin(url);
  http.setTimeout(8000);
  int code = http.GET();
  http.end();
  bool ok = (code == 200);
  Serial.println(ok ? "CAM: OK" : "CAM: FAIL");
  if (!ok) lcdShow("CAM Error!", "Check CAM IP");
  return ok;
}

// ── Countdown task (hardware side: LCD + LEDs + buzzer) ──────
//    Browser handles its own visual timer independently.
//    At t=0 the browser calls /capture, which triggers this task
//    via the /start_countdown endpoint for the hardware effects.
void countdownTask(void* param) {
  int value = (int)(intptr_t)param;
  isCounting = true;

  // Warm colours that deepen as countdown reaches zero
  uint32_t colours[6] = {0, 0xFF8000, 0xFF8C00, 0xFF3200, 0xC80000, 0x780000};

  for (int i = value; i > 0; i--) {
    char buf[10];
    snprintf(buf, sizeof(buf), "    %d...", i);
    lcdShow("Get Ready!", buf);
    uint32_t c = (i <= 5) ? colours[i] : colours[1];
    ledsSet((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF);
    beep(100);
    delay(1000);
  }

  // Flash white + "CHEESE!"
  ledsSet(255, 255, 255);
  lcdShow("  CHEESE!", "");
  beep(300);
  delay(200);
  ledsOff();

  // Trigger camera
  lcdShow("Capturing...", "");
  bool ok = triggerCam();

  delay(2000);
  if (ok) {
    ledsSet(0, 80, 0);
    lcdShow("Photo Sent!", "Check Telegram");
    beep(80); delay(150); beep(80);
  } else {
    ledsSet(80, 0, 0);
    lcdShow("CAM Failed!", "Check CAM IP");
    beep(500);
  }

  delay(4000);
  ledsOff();
  ledsSet(0, 0, 30);
  lcdShow("Ready!", "Open browser");
  isCounting = false;
  vTaskDelete(NULL);
}

// ── Distance monitor task ────────────────────────────────────
void distanceTask(void* param) {
  while (true) {
    vTaskDelay(300 / portTICK_PERIOD_MS);
    if (isCounting) continue;
    float dist = measureDistanceCm();
    if (dist < 0) continue;
    if (dist < DIST_MIN_CM) {
      ledsSet(200, 0, 0);
      char buf[16];
      snprintf(buf, sizeof(buf), "%.0f cm - Back!", dist);
      lcdShow("!! TOO CLOSE !!", buf);
      beep(60); delay(80); beep(60);
    } else {
      ledsSet(0, 200, 0);
      lcdShow("Ready!", "Open browser");
    }
  }
}

// ── Web UI ───────────────────────────────────────────────────
// The page is built dynamically so we can inject ESP32CAM_IP at runtime.
// Layout:
//   [Live stream from ESP32-CAM fills top half]
//   [3s] [5s] buttons  →  browser counts down visually
//   At t=0: browser calls /capture on Main ESP32
//            Main ESP32 runs hardware countdown + triggers camera
//
// Note: the stream src uses the CAM's IP directly (cross-origin img is fine).

void handleRoot() {
  // Build URLs from runtime config
  String camStreamUrl = "http://";
  camStreamUrl += ESP32CAM_IP;
  camStreamUrl += ":81/";

  String camResBase = "http://";
  camResBase += ESP32CAM_IP;
  camResBase += ":80/resolution?size=";

  String page = R"rawhtml(<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Photobooth</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: sans-serif;
    background: #111;
    color: #eee;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-height: 100vh;
    padding: 16px;
  }
  h1 { color: #f90; font-size: 1.5em; margin-bottom: 12px; }

  /* Stream container */
  #stream-wrap {
    position: relative;
    width: 100%;
    max-width: 640px;
    background: #000;
    border-radius: 12px;
    overflow: hidden;
    aspect-ratio: 4/3;
  }
  #stream {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }

  /* Big countdown overlay on top of the stream */
  #overlay {
    position: absolute;
    inset: 0;
    display: none;
    align-items: center;
    justify-content: center;
    background: rgba(0,0,0,0.45);
    font-size: 20vw;
    font-weight: bold;
    color: #fff;
    text-shadow: 0 0 30px #f90, 0 4px 12px #000;
  }
  #overlay.show { display: flex; }

  /* Flash effect */
  #flash {
    position: absolute;
    inset: 0;
    background: #fff;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.05s;
    border-radius: 12px;
  }
  #flash.bang { opacity: 1; }

  /* Buttons */
  #controls { margin-top: 18px; }
  .btn {
    font-size: 1.4em;
    font-weight: bold;
    padding: 14px 36px;
    margin: 8px;
    border-radius: 12px;
    border: none;
    cursor: pointer;
    background: #f90;
    color: #111;
    transition: transform 0.1s, opacity 0.1s;
  }
  .btn:active { transform: scale(0.95); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }

  /* Resolution row */
  #res-row {
    margin-top: 14px;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
    font-size: 0.95em;
    color: #bbb;
  }
  #res-row select {
    font-size: 0.95em;
    padding: 6px 10px;
    border-radius: 8px;
    border: none;
    background: #222;
    color: #eee;
    cursor: pointer;
  }
  #res-row button {
    font-size: 0.9em;
    padding: 6px 14px;
    border-radius: 8px;
    border: none;
    background: #555;
    color: #eee;
    cursor: pointer;
  }
  #res-row button:hover { background: #777; }
  #res-msg { font-size: 0.85em; color: #8f8; min-height: 1.2em; }

  /* Status bar */
  #status {
    margin-top: 14px;
    font-size: 1.05em;
    min-height: 1.4em;
    color: #aaa;
  }
  #status.ok  { color: #4f4; }
  #status.err { color: #f44; }
  #status.cnt { color: #f90; font-weight: bold; font-size: 1.2em; }
</style>
</head>
<body>

<h1>Photobooth</h1>

<div id="stream-wrap">
  <img id="stream" src=")rawhtml";

  page += camStreamUrl;

  page += R"rawhtml(" alt="Live stream loading...">
  <div id="overlay"></div>
  <div id="flash"></div>
</div>

<div id="controls">
  <button class="btn" id="btn3" onclick="startCountdown(3)">&#9654; 3s</button>
  <button class="btn" id="btn5" onclick="startCountdown(5)">&#9654; 5s</button>
</div>

<div id="res-row">
  Resolution:
  <select id="res">
    <option value="QQVGA">QQVGA — 160x120 (fastest)</option>
    <option value="QVGA" selected>QVGA — 320x240 (default)</option>
    <option value="VGA">VGA — 640x480</option>
    <option value="SVGA">SVGA — 800x600</option>
    <option value="XGA">XGA — 1024x768 (PSRAM)</option>
    <option value="SXGA">SXGA — 1280x1024 (PSRAM)</option>
    <option value="UXGA">UXGA — 1600x1200 (PSRAM)</option>
  </select>
  <button onclick="setResolution()">Apply</button>
</div>
<div id="res-msg"></div>

<div id="status">Ready — tap a button to start!</div>

<script>
const CAM_RES_BASE = ")rawhtml";

  page += camResBase;

  page += R"rawhtml(";

function setResolution() {
  const size = document.getElementById('res').value;
  const msg  = document.getElementById('res-msg');
  msg.style.color = '#aaa';
  msg.innerText = 'Setting ' + size + '...';
  fetch(CAM_RES_BASE + size)
    .then(r => r.text())
    .then(t => { msg.style.color = '#8f8'; msg.innerText = t; })
    .catch(() => { msg.style.color = '#f44'; msg.innerText = 'Failed — is CAM online?'; });
}
let counting = false;

function setStatus(msg, cls) {
  const el = document.getElementById('status');
  el.innerText = msg;
  el.className = cls || '';
}

function setButtonsDisabled(dis) {
  document.getElementById('btn3').disabled = dis;
  document.getElementById('btn5').disabled = dis;
}

function flashScreen() {
  const f = document.getElementById('flash');
  f.classList.add('bang');
  setTimeout(() => f.classList.remove('bang'), 300);
}

function startCountdown(seconds) {
  if (counting) return;
  counting = true;
  setButtonsDisabled(true);

  const overlay = document.getElementById('overlay');
  overlay.classList.add('show');

  let remaining = seconds;

  function tick() {
    if (remaining > 0) {
      overlay.innerText = remaining;
      setStatus('Get ready... ' + remaining, 'cnt');
      remaining--;
      setTimeout(tick, 1000);
    } else {
      // Timer hit zero — show CHEESE + flash
      overlay.innerText = '&#128247;';
      setStatus('CHEESE! Taking photo...', 'cnt');
      flashScreen();

      // Tell Main ESP32 to run hardware effects + trigger camera
      fetch('/capture')
        .then(r => r.text())
        .then(t => {
          overlay.classList.remove('show');
          overlay.innerText = '';
          if (t === 'BUSY') {
            setStatus('System busy — try again', 'err');
          } else {
            setStatus('Photo sent to Telegram! &#10003;', 'ok');
          }
        })
        .catch(() => {
          overlay.classList.remove('show');
          setStatus('Error — check connection', 'err');
        })
        .finally(() => {
          counting = false;
          setButtonsDisabled(false);
        });
    }
  }

  tick();
}
</script>
</body>
</html>
)rawhtml";

  server.send(200, "text/html", page);
}

// ── /capture — called by browser at t=0 ─────────────────────
// Runs hardware countdown on ESP32 then triggers camera
void handleCapture() {
  if (isCounting) {
    server.send(200, "text/plain", "BUSY");
    return;
  }
  server.send(200, "text/plain", "OK");
  // Default to 0-step "countdown" — hardware just does CHEESE + shoot
  // Pass 0 so the for-loop is skipped and it goes straight to capture
  xTaskCreate(countdownTask, "countdown", 4096, (void*)(intptr_t)0, 1, NULL);
}

// ── /start_countdown — kept for backwards compat with old flow ─
void handleCountdown() {
  if (!server.hasArg("value")) { server.send(400, "text/plain", "missing value"); return; }
  int value = server.arg("value").toInt();
  value = max(0, min(10, value));
  if (isCounting) { server.send(200, "text/plain", "BUSY"); return; }
  server.send(200, "text/plain", "OK");
  xTaskCreate(countdownTask, "countdown", 4096, (void*)(intptr_t)value, 1, NULL);
}

void handle404() { server.send(404, "text/plain", "Not found"); }

// ── setup / loop ─────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("=== Main ESP32 Photobooth ===");

  pinMode(BUZZER_PIN, OUTPUT); digitalWrite(BUZZER_PIN, LOW);
  pinMode(TRIG_PIN, OUTPUT);   digitalWrite(TRIG_PIN, LOW);
  pinMode(ECHO_PIN, INPUT);

  Wire.begin(21, 22);
  lcd.begin(LCD_COLS, LCD_ROWS);
  lcd.backlight();
  lcdShow("Photobooth", "Booting...");

  leds.begin();
  ledsOff();

  wifiConnect();

  String ip = WiFi.localIP().toString();
  lcdShow("WiFi OK!", ip.c_str());
  delay(1000);

  xTaskCreate(distanceTask, "distance", 2048, NULL, 1, NULL);

  server.on("/",                HTTP_GET, handleRoot);
  server.on("/index.html",      HTTP_GET, handleRoot);
  server.on("/capture",         HTTP_GET, handleCapture);
  server.on("/start_countdown", HTTP_GET, handleCountdown);
  server.onNotFound(handle404);
  server.begin();

  Serial.print("UI ready: http://");
  Serial.println(WiFi.localIP());

  ledsSet(0, 0, 30);
  lcdShow("Ready!", ip.c_str());
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost, reconnecting...");
    wifiConnect();
  }
  server.handleClient();
}
