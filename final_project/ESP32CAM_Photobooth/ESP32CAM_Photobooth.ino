#include "esp_camera.h"
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <WebServer.h>

// ── CONFIG ───────────────────────────────────────────────────
const char* WIFI_SSID     = "";
const char* WIFI_PASSWORD = "";
const char* BOT_TOKEN     = "";   // from @BotFather
const char* CHAT_ID       = "";   // group chat ID (negative number for groups)
// ─────────────────────────────────────────────────────────────

// AI Thinker pin map
#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22
#define FLASH_GPIO_NUM     4

// Port 80 = control (capture, resolution)
// Port 81 = MJPEG stream (separate task, never blocks port 80)
WebServer controlServer(80);
WebServer streamServer(81);

// Mutex so capture and stream don't grab the camera at the same time
SemaphoreHandle_t camMutex;

// ── Camera init ───────────────────────────────────────────────
bool initCamera() {
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer   = LEDC_TIMER_0;
  config.pin_d0       = Y2_GPIO_NUM;
  config.pin_d1       = Y3_GPIO_NUM;
  config.pin_d2       = Y4_GPIO_NUM;
  config.pin_d3       = Y5_GPIO_NUM;
  config.pin_d4       = Y6_GPIO_NUM;
  config.pin_d5       = Y7_GPIO_NUM;
  config.pin_d6       = Y8_GPIO_NUM;
  config.pin_d7       = Y9_GPIO_NUM;
  config.pin_xclk     = XCLK_GPIO_NUM;
  config.pin_pclk     = PCLK_GPIO_NUM;
  config.pin_vsync    = VSYNC_GPIO_NUM;
  config.pin_href     = HREF_GPIO_NUM;
  config.pin_pwdn     = PWDN_GPIO_NUM;
  config.pin_reset    = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size   = FRAMESIZE_UXGA;
  config.jpeg_quality = 12;
  config.fb_count     = 1;
  config.grab_mode    = CAMERA_GRAB_WHEN_EMPTY;
  config.fb_location  = CAMERA_FB_IN_PSRAM;

  // Try new field name first (ESP32 core >= 2.0.4), fall back to old name
#if defined(CONFIG_IDF_TARGET_ESP32)
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
#else
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
#endif

  if (psramFound()) {
    config.jpeg_quality = 10;
    config.fb_count     = 2;
    config.grab_mode    = CAMERA_GRAB_LATEST;
    Serial.println("PSRAM found — high quality, dual buffer");
  } else {
    config.frame_size  = FRAMESIZE_SVGA;
    config.fb_location = CAMERA_FB_IN_DRAM;
    Serial.println("No PSRAM — SVGA/DRAM mode");
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init FAILED: 0x%x\n", err);
    return false;
  }

  sensor_t* s = esp_camera_sensor_get();
  if (s->id.PID == OV3660_PID) {
    s->set_vflip(s, 1);
    s->set_brightness(s, 1);
    s->set_saturation(s, -2);
  }
  s->set_framesize(s, FRAMESIZE_QVGA);  // start at QVGA for smooth stream
  Serial.println("Camera OK");
  return true;
}

// ── WiFi ──────────────────────────────────────────────────────
void wifiConnect() {
  Serial.print("Connecting to WiFi");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  WiFi.setSleep(false);
  int r = 0;
  while (WiFi.status() != WL_CONNECTED && r++ < 20) {
    delay(1000); Serial.print(".");
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nWiFi FAILED — restarting");
    delay(2000); ESP.restart();
  }
  Serial.println();
  Serial.print("IP: "); Serial.println(WiFi.localIP());
  Serial.print("Stream: http://"); Serial.print(WiFi.localIP()); Serial.println(":81/");
  Serial.print("Control: http://"); Serial.println(WiFi.localIP());
}

// ── CORS (needed because UI is on Main ESP32, CAM is different IP) ──
void addCORSHeaders(WebServer& srv) {
  srv.sendHeader("Access-Control-Allow-Origin",  "*");
  srv.sendHeader("Access-Control-Allow-Methods", "GET, OPTIONS");
  srv.sendHeader("Access-Control-Allow-Headers", "Content-Type");
}
void handleControlOptions() { addCORSHeaders(controlServer); controlServer.send(204); }

// ── MJPEG stream task (runs forever on core 0) ───────────────
// Completely separate from the control server — capture can never be blocked
void streamTask(void* param) {
  streamServer.on("/", HTTP_GET, []() {
    WiFiClient client = streamServer.client();
    client.print(
      "HTTP/1.1 200 OK\r\n"
      "Content-Type: multipart/x-mixed-replace; boundary=frame\r\n"
      "Access-Control-Allow-Origin: *\r\n"
      "Cache-Control: no-cache\r\n"
      "\r\n"
    );
    Serial.println("Stream client connected");

    while (client.connected()) {
      // Take mutex — wait up to 500ms, then skip this frame
      if (xSemaphoreTake(camMutex, pdMS_TO_TICKS(500)) == pdTRUE) {
        camera_fb_t* fb = esp_camera_fb_get();
        xSemaphoreGive(camMutex);

        if (!fb) { delay(50); continue; }

        String hdr =
          "--frame\r\n"
          "Content-Type: image/jpeg\r\n"
          "Content-Length: " + String(fb->len) + "\r\n\r\n";
        client.print(hdr);

        const size_t CHUNK = 4096;
        size_t pos = 0;
        while (pos < fb->len && client.connected()) {
          size_t n = min(CHUNK, fb->len - pos);
          client.write(fb->buf + pos, n);
          pos += n;
        }
        client.print("\r\n");
        esp_camera_fb_return(fb);
      }
      delay(33);  // ~30fps cap
    }
    Serial.println("Stream client disconnected");
  });

  streamServer.begin();
  Serial.println("Stream server started on port 81");

  while (true) {
    streamServer.handleClient();
    delay(1);
  }
}

// ── Flush stale frames before capture ────────────────────────
void flushFrameBuffer() {
  // Drain up to 3 buffered frames so we always get a fresh one
  for (int i = 0; i < 3; i++) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (fb) esp_camera_fb_return(fb);
    else break;
  }
}

// ── Telegram sender ───────────────────────────────────────────
bool sendTelegram(uint8_t* buf, size_t len) {
  const char* HOST     = "api.telegram.org";
  const char* BOUNDARY = "PhotoboothBoundary";

  WiFiClientSecure client;
  client.setInsecure();
  client.setTimeout(20);

  Serial.println("Connecting to Telegram...");
  if (!client.connect(HOST, 443)) {
    Serial.println("Telegram: connection FAILED");
    return false;
  }

  String body1 =
    "--" + String(BOUNDARY) + "\r\n"
    "Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n" +
    String(CHAT_ID) + "\r\n"
    "--" + String(BOUNDARY) + "\r\n"
    "Content-Disposition: form-data; name=\"photo\"; filename=\"photo.jpg\"\r\n"
    "Content-Type: image/jpeg\r\n\r\n";

  String body2 = "\r\n--" + String(BOUNDARY) + "--\r\n";
  size_t total = body1.length() + len + body2.length();

  client.printf(
    "POST /bot%s/sendPhoto HTTP/1.1\r\n"
    "Host: %s\r\n"
    "Content-Type: multipart/form-data; boundary=%s\r\n"
    "Content-Length: %d\r\n"
    "Connection: close\r\n\r\n",
    BOT_TOKEN, HOST, BOUNDARY, (int)total
  );
  client.print(body1);

  // Send image in chunks
  const size_t CHUNK = 2048;
  size_t pos = 0;
  while (pos < len) {
    size_t n = min(CHUNK, len - pos);
    client.write(buf + pos, n);
    pos += n;
  }
  client.print(body2);

  // Read response (wait up to 15s)
  String resp;
  unsigned long t = millis();
  while (millis() - t < 15000) {
    while (client.available()) resp += (char)client.read();
    if (resp.indexOf("\"ok\":true") >= 0) break;
    if (!client.connected()) break;
    delay(10);
  }
  client.stop();

  bool ok = resp.indexOf("\"ok\":true") >= 0;
  Serial.println(ok ? "Telegram: SENT OK" : "Telegram: FAILED");
  if (!ok) {
    // Print first 200 chars of response to help diagnose
    Serial.println("Response: " + resp.substring(0, 200));
  }
  return ok;
}

// ── Capture and send ──────────────────────────────────────────
bool captureAndSend() {
  // Take mutex — stop stream from grabbing frames while we capture
  if (xSemaphoreTake(camMutex, pdMS_TO_TICKS(2000)) != pdTRUE) {
    Serial.println("Capture: could not get camera mutex");
    return false;
  }

  sensor_t* s = esp_camera_sensor_get();
  delay(100);  // brief settle before capture

  // Flush any stale buffered frames
  flushFrameBuffer();

  // Flash on → grab → flash off
  digitalWrite(FLASH_GPIO_NUM, HIGH);
  delay(150);
  camera_fb_t* fb = esp_camera_fb_get();
  digitalWrite(FLASH_GPIO_NUM, LOW);

  xSemaphoreGive(camMutex);

  if (!fb) {
    Serial.println("Capture: esp_camera_fb_get() returned NULL");
    return false;
  }

  Serial.printf("Captured %d bytes\n", fb->len);
  bool ok = sendTelegram(fb->buf, fb->len);
  esp_camera_fb_return(fb);
  return ok;
}

// ── Control server handlers ───────────────────────────────────
void handleCapture() {
  addCORSHeaders(controlServer);
  controlServer.send(200, "text/plain", "OK");
  Serial.println("/capture received");
  bool ok = captureAndSend();
  Serial.println(ok ? "Result: OK" : "Result: FAILED");
}

void handleResolution() {
  addCORSHeaders(controlServer);

  if (!controlServer.hasArg("size")) {
    controlServer.send(400, "text/plain", "Missing ?size=");
    return;
  }

  String sz = controlServer.arg("size");
  sz.toUpperCase();

  framesize_t fs;
  if      (sz == "QQVGA") fs = FRAMESIZE_QQVGA;
  else if (sz == "QVGA")  fs = FRAMESIZE_QVGA;
  else if (sz == "VGA")   fs = FRAMESIZE_VGA;
  else if (sz == "SVGA")  fs = FRAMESIZE_SVGA;
  else if (sz == "XGA")   fs = FRAMESIZE_XGA;
  else if (sz == "SXGA")  fs = FRAMESIZE_SXGA;
  else if (sz == "UXGA")  fs = FRAMESIZE_UXGA;
  else {
    controlServer.send(400, "text/plain", "Unknown size");
    return;
  }

  if (!psramFound() && (fs == FRAMESIZE_UXGA || fs == FRAMESIZE_SXGA || fs == FRAMESIZE_XGA)) {
    sensor_t* s = esp_camera_sensor_get();
    s->set_framesize(s, FRAMESIZE_SVGA);
    controlServer.send(200, "text/plain", "No PSRAM — forced SVGA");
    return;
  }

  sensor_t* s = esp_camera_sensor_get();
  s->set_framesize(s, fs);
  Serial.print("Resolution → "); Serial.println(sz);
  controlServer.send(200, "text/plain", "Resolution set to " + sz);
}

void handleControlRoot() {
  String page =
    "<!DOCTYPE html><html><head>"
    "<meta charset='UTF-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
    "<title>ESP32-CAM</title>"
    "<style>body{font-family:sans-serif;background:#111;color:#eee;padding:20px;text-align:center}"
    "h2{color:#f90}select,button{font-size:1em;padding:8px 14px;margin:6px;border-radius:8px}"
    "#msg{color:#8f8;margin-top:10px}</style></head><body>"
    "<h2>&#128247; ESP32-CAM</h2>"
    "<p>Stream on port 81</p>"
    "<select id='r'>"
    "<option value='QQVGA'>QQVGA 160x120</option>"
    "<option value='QVGA' selected>QVGA 320x240</option>"
    "<option value='VGA'>VGA 640x480</option>"
    "<option value='SVGA'>SVGA 800x600</option>"
    "<option value='XGA'>XGA 1024x768 (PSRAM)</option>"
    "<option value='SXGA'>SXGA 1280x1024 (PSRAM)</option>"
    "<option value='UXGA'>UXGA 1600x1200 (PSRAM)</option>"
    "</select>"
    "<button onclick=\"fetch('/resolution?size='+document.getElementById('r').value)"
    ".then(r=>r.text()).then(t=>document.getElementById('msg').innerText=t)\">"
    "Apply</button>"
    "<div id='msg'></div></body></html>";
  controlServer.send(200, "text/html", page);
}

// ── setup / loop ──────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("\n=== ESP32-CAM Photobooth ===");

  pinMode(FLASH_GPIO_NUM, OUTPUT);
  digitalWrite(FLASH_GPIO_NUM, LOW);

  // Create mutex before starting any tasks
  camMutex = xSemaphoreCreateMutex();

  if (!initCamera()) {
    Serial.println("Camera init FAILED — check board selection and partition scheme");
    // Blink flash to signal error
    while (true) {
      digitalWrite(FLASH_GPIO_NUM, HIGH); delay(200);
      digitalWrite(FLASH_GPIO_NUM, LOW);  delay(200);
    }
  }

  wifiConnect();

  // Control server (port 80)
  controlServer.on("/",            HTTP_GET,     handleControlRoot);
  controlServer.on("/capture",     HTTP_GET,     handleCapture);
  controlServer.on("/capture",     HTTP_OPTIONS, handleControlOptions);
  controlServer.on("/resolution",  HTTP_GET,     handleResolution);
  controlServer.on("/resolution",  HTTP_OPTIONS, handleControlOptions);
  controlServer.begin();
  Serial.println("Control server started on port 80");

  // Stream server runs in its own FreeRTOS task on core 0
  // (Arduino loop runs on core 1 — they don't block each other)
  xTaskCreatePinnedToCore(
    streamTask,   // function
    "stream",     // name
    8192,         // stack size (bytes)
    NULL,         // param
    1,            // priority
    NULL,         // handle
    0             // core 0
  );
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi lost — reconnecting");
    wifiConnect();
  }
  controlServer.handleClient();
  delay(1);
}
