#include "ember_api.h"

#include <HTTPClient.h>
#include <WiFi.h>
#include <ArduinoJson.h>

#include "config.h"
#include "ember_status_led.h"

#ifndef WIFI_SSID
#error "WIFI_SSID missing — use #define (with hash) in include/config.h"
#endif
#ifndef WIFI_PASSWORD
#error "WIFI_PASSWORD missing — use #define (with hash) in include/config.h"
#endif
#ifndef EMBER_BASE_URL
#error "EMBER_BASE_URL missing — use #define (with hash) in include/config.h"
#endif

namespace {

const char *wifiStatusName(wl_status_t status) {
  switch (status) {
    case WL_IDLE_STATUS:
      return "IDLE";
    case WL_NO_SSID_AVAIL:
      return "NO_SSID";
    case WL_SCAN_COMPLETED:
      return "SCAN_DONE";
    case WL_CONNECTED:
      return "CONNECTED";
    case WL_CONNECT_FAILED:
      return "CONNECT_FAILED";
    case WL_CONNECTION_LOST:
      return "LOST";
    case WL_DISCONNECTED:
      return "DISCONNECTED";
    default:
      return "UNKNOWN";
  }
}

}  // namespace

String EmberApi::url(const char *path) const {
  return String(EMBER_BASE_URL) + path;
}

void EmberApi::applyAuth(HTTPClient &http) const {
#ifdef EMBER_DEVICE_TOKEN
  http.addHeader("Authorization", String("Bearer ") + EMBER_DEVICE_TOKEN);
#endif
}

bool EmberApi::connectWiFi(EmberStatusLed *led) {
  if (WiFi.status() == WL_CONNECTED && WiFi.localIP() != IPAddress(0, 0, 0, 0)) {
    Serial.print("[wifi] Already connected, IP ");
    Serial.println(WiFi.localIP());
    return true;
  }

  WiFi.mode(WIFI_STA);
  WiFi.setSleep(false);
  WiFi.setAutoReconnect(true);

  Serial.printf("[wifi] Connecting to \"%s\" (2.4 GHz required)\n", WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  const uint32_t timeoutMs = 60000;
  const uint32_t started = millis();
  wl_status_t lastStatus = WL_IDLE_STATUS;

  while (WiFi.status() != WL_CONNECTED && (millis() - started) < timeoutMs) {
    if (led) {
      led->tick();
    }
    const wl_status_t status = WiFi.status();
    if (status != lastStatus) {
      Serial.printf("[wifi] status=%s (%d)\n", wifiStatusName(status), status);
      lastStatus = status;
    }
    delay(100);
  }

  if (WiFi.status() != WL_CONNECTED || WiFi.localIP() == IPAddress(0, 0, 0, 0)) {
    Serial.printf("[wifi] Failed — status=%s (%d)\n", wifiStatusName(WiFi.status()),
                  WiFi.status());
    return false;
  }

  Serial.print("[wifi] Connected, IP ");
  Serial.println(WiFi.localIP());
  delay(1500);
  return true;
}

bool EmberApi::checkCapabilities() {
  for (uint8_t attempt = 1; attempt <= 5; attempt++) {
    HTTPClient http;
    http.setTimeout(15000);
    http.begin(url("/device/v1/capabilities"));
    applyAuth(http);

    const int code = http.GET();
    if (code == 200) {
      const String body = http.getString();
      http.end();
      Serial.println("[hub] Capabilities OK");
      Serial.println(body);
      backendReady_ = true;
      return true;
    }

    Serial.printf("[hub] Capabilities check failed (try %u/5): %d\n", attempt, code);
    http.end();
    backendReady_ = false;
    delay(2000);
  }

  return false;
}

bool EmberApi::fetchPersonas(std::vector<EmberPersonaSummary> &out, String &defaultId) {
  HTTPClient http;
  http.setTimeout(10000);
  http.begin(url("/device/v1/personas"));
  applyAuth(http);

  const int code = http.GET();
  if (code != 200) {
    Serial.printf("[hub] Personas fetch failed: %d\n", code);
    http.end();
    return false;
  }

  const String body = http.getString();
  http.end();

  JsonDocument doc;
  const DeserializationError err = deserializeJson(doc, body);
  if (err) {
    Serial.printf("[hub] Personas JSON error: %s\n", err.c_str());
    return false;
  }

  defaultId = doc["default"].as<String>();
  out.clear();
  for (JsonObject persona : doc["personas"].as<JsonArray>()) {
    EmberPersonaSummary summary;
    summary.id = persona["id"].as<String>();
    summary.name = persona["name"].as<String>();
    if (summary.id.length() > 0) {
      out.push_back(summary);
    }
  }

  Serial.printf("[hub] Loaded %u personas (default: %s)\n", out.size(), defaultId.c_str());
  return !out.empty();
}

bool EmberApi::converseWithWav(const uint8_t *wavData, size_t wavLen, const String &persona,
                               String &responseJson) {
  HTTPClient http;
  http.setTimeout(60000);
  http.begin(url("/device/v1/converse"));
  applyAuth(http);

  const String boundary = "----EmberForgeBoundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"persona\"\r\n\r\n";
  head += persona + "\r\n";
  head += "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n";
  head += String(EMBER_DEVICE_ID) + "\r\n";
  head += "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n";
  head += "Content-Type: audio/wav\r\n\r\n";

  const String tail = "\r\n--" + boundary + "--\r\n";
  const size_t totalLen = head.length() + wavLen + tail.length();

  uint8_t *payload =
      static_cast<uint8_t *>(heap_caps_malloc(totalLen, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!payload) {
    Serial.println("[hub] Out of memory for converse upload");
    http.end();
    return false;
  }

  size_t offset = 0;
  memcpy(payload + offset, head.c_str(), head.length());
  offset += head.length();
  memcpy(payload + offset, wavData, wavLen);
  offset += wavLen;
  memcpy(payload + offset, tail.c_str(), tail.length());

  const int code = http.POST(payload, totalLen);
  heap_caps_free(payload);

  if (code != 200) {
    Serial.printf("[hub] Converse failed: %d\n", code);
    Serial.println(http.getString());
    http.end();
    return false;
  }

  responseJson = http.getString();
  http.end();

  if (responseJson.length() == 0) {
    Serial.println("[hub] Converse response empty");
    return false;
  }

  Serial.printf("[hub] Converse OK (%u bytes JSON)\n", responseJson.length());
  return true;
}