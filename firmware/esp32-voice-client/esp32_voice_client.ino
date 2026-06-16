/*
 * EmberForge ESP32-S3 Voice Client (scaffold)
 *
 * Thin client for consumer-grade companion hardware.
 * Records audio on button press, uploads to EmberForge backend,
 * displays and plays the persona response.
 *
 * Requires: WiFi, I2S mic, speaker, optional OLED display
 * Backend:  GET  /device/v1/capabilities
 *           GET  /device/v1/personas
 *           POST /device/v1/converse  (multipart WAV upload)
 *
 * Copy config.h.example → config.h before building.
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include "config.h"

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

bool backendReady = false;
String activePersona = EMBER_DEFAULT_PERSONA;

// ---------------------------------------------------------------------------
// Backend helpers
// ---------------------------------------------------------------------------

String emberUrl(const char *path) {
  return String(EMBER_BASE_URL) + path;
}

void applyAuthHeaders(HTTPClient &http) {
#ifdef EMBER_DEVICE_TOKEN
  http.addHeader("Authorization", String("Bearer ") + EMBER_DEVICE_TOKEN);
#endif
}

bool checkCapabilities() {
  HTTPClient http;
  http.begin(emberUrl("/device/v1/capabilities"));
  applyAuthHeaders(http);

  int code = http.GET();
  if (code != 200) {
    Serial.printf("Capabilities check failed: %d\n", code);
    http.end();
    return false;
  }

  String body = http.getString();
  http.end();
  Serial.println("Backend capabilities:");
  Serial.println(body);
  return true;
}

bool converseWithAudio(const uint8_t *wavData, size_t wavLen, String &responseText) {
  HTTPClient http;
  http.begin(emberUrl("/device/v1/converse"));
  applyAuthHeaders(http);

  String boundary = "----EmberForgeBoundary";
  http.addHeader("Content-Type", "multipart/form-data; boundary=" + boundary);

  String head = "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"persona\"\r\n\r\n";
  head += activePersona + "\r\n";
  head += "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"device_id\"\r\n\r\n";
  head += EMBER_DEVICE_ID + "\r\n";
  head += "--" + boundary + "\r\n";
  head += "Content-Disposition: form-data; name=\"audio\"; filename=\"recording.wav\"\r\n";
  head += "Content-Type: audio/wav\r\n\r\n";

  String tail = "\r\n--" + boundary + "--\r\n";

  size_t totalLen = head.length() + wavLen + tail.length();
  uint8_t *payload = (uint8_t *)malloc(totalLen);
  if (!payload) return false;

  size_t offset = 0;
  memcpy(payload + offset, head.c_str(), head.length()); offset += head.length();
  memcpy(payload + offset, wavData, wavLen);               offset += wavLen;
  memcpy(payload + offset, tail.c_str(), tail.length());

  int code = http.POST(payload, totalLen);
  free(payload);

  if (code != 200) {
    Serial.printf("Converse failed: %d\n", code);
    Serial.println(http.getString());
    http.end();
    return false;
  }

  responseText = http.getString();
  http.end();
  return true;
}

// ---------------------------------------------------------------------------
// Audio (implement for your I2S hardware)
// ---------------------------------------------------------------------------

/*
 * recordWav():
 *   - Start I2S mic on button press
 *   - Stop on button release or silence timeout
 *   - Return 16-bit PCM WAV buffer (16 kHz mono)
 *
 * playResponse():
 *   - Phase 1: display response_text on OLED
 *   - Phase 2: play voice.audio_base64 from server TTS
 *   - Phase 3: local codec fallback if needed
 */

bool recordWav(uint8_t **outData, size_t *outLen) {
  // TODO: wire to your I2S microphone driver
  Serial.println("[audio] recordWav() not implemented yet");
  *outData = nullptr;
  *outLen = 0;
  return false;
}

void playResponse(const String &jsonResponse) {
  // TODO: parse JSON, show display.lines on OLED, play TTS audio
  Serial.println("[response]");
  Serial.println(jsonResponse);
}

// ---------------------------------------------------------------------------
// Setup & loop
// ---------------------------------------------------------------------------

void connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("Connecting to %s", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());
}

void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_PIN, INPUT_PULLUP);

  connectWiFi();
  backendReady = checkCapabilities();

  if (!backendReady) {
    Serial.println("Backend not ready — check EMBER_HOST and server status.");
  } else {
    Serial.println("EmberForge device client ready. Hold button to talk.");
  }
}

void loop() {
  if (!backendReady) {
    delay(2000);
    backendReady = checkCapabilities();
    return;
  }

  if (digitalRead(BUTTON_PIN) == LOW) {
    Serial.println("Recording...");
    uint8_t *wavData = nullptr;
    size_t wavLen = 0;

    if (recordWav(&wavData, &wavLen)) {
      String response;
      if (converseWithAudio(wavData, wavLen, response)) {
        playResponse(response);
      }
      free(wavData);
    }

    // Debounce
    while (digitalRead(BUTTON_PIN) == LOW) {
      delay(50);
    }
  }

  delay(20);
}