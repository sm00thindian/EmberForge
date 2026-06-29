/**
 * EmberForge thin client — Waveshare ESP32-S3-AUDIO-Board
 */

#include <Arduino.h>
#include <WiFi.h>

#include <vector>

#include "config.h"
#include "ember_api.h"
#include "ember_audio.h"
#include "ember_status_led.h"
#include "pins.h"

#ifndef EMBER_TRIGGER_MODE
#define EMBER_TRIGGER_MODE EMBER_TRIGGER_VAD
#endif

EmberApi gApi;
EmberAudio gAudio;
EmberStatusLed gLed;

std::vector<EmberPersonaSummary> gPersonas;
String gActivePersona = EMBER_DEFAULT_PERSONA;
size_t gPersonaIndex = 0;

volatile bool gPttHeld = false;
volatile bool gPttEdge = false;
bool gMicEnabled = true;

enum class DeviceState {
  Boot,
  Ready,
  Recording,
  Uploading,
  Playing,
  Error,
};

DeviceState gState = DeviceState::Boot;
bool gHubReady = false;
bool gAudioReady = false;
uint32_t gLastHubTryMs = 0;

void delayWithLed(uint32_t ms) {
  const uint32_t end = millis() + ms;
  while ((int32_t)(millis() - end) < 0) {
    gLed.tick();
    delay(20);
  }
}

void blinkReadySuccess() {
  for (uint8_t i = 0; i < 3; i++) {
    gLed.setState(EmberLedState::Ready);
    delay(200);
    gLed.flashOff();
    delay(200);
  }
  gLed.setState(EmberLedState::Ready);
}

void printBakedConfig() {
  Serial.println("[config] Baked into firmware:");
  Serial.printf("[config]   WIFI_SSID = \"%s\"\n", WIFI_SSID);
  Serial.printf("[config]   EMBER_BASE_URL = \"%s\"\n", EMBER_BASE_URL);
#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_VAD
  Serial.println("[config]   TRIGGER = VAD (hands-free)");
#elif EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
  Serial.println("[config]   TRIGGER = BOOT button PTT");
#else
  Serial.println("[config]   TRIGGER = KEY1 PTT");
#endif
}

void onPtt(bool active) {
  gPttHeld = active;
  gPttEdge = active;
}

void setListenLed() {
  gLed.setState(gMicEnabled ? EmberLedState::Ready : EmberLedState::MicMuted);
}

void toggleMicMute() {
  gMicEnabled = !gMicEnabled;
  if (gMicEnabled) {
    Serial.println("[mic] Listening ON (Key 3 to mute)");
  } else {
    Serial.println("[mic] Listening OFF (Key 3 to unmute)");
  }
  setListenLed();
}

void onMicMuteKey() { toggleMicMute(); }

bool pollVadControls() {
  gAudio.processInput();
  gLed.tick();
  return !gMicEnabled;
}

void printPersonaList() {
  if (gPersonas.empty()) {
    Serial.println("[persona] None loaded from hub");
    return;
  }
  Serial.printf("[persona] %u available — Key 2 cycles:", gPersonas.size());
  for (const auto &p : gPersonas) {
    Serial.printf(" %s", p.id.c_str());
  }
  Serial.println();
}

void pollBootPtt() {
#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
  const bool pressed = digitalRead(EMBER_BOOT_BUTTON_GPIO) == LOW;
  if (pressed && !gPttHeld) {
    gPttHeld = true;
    gPttEdge = true;
  } else if (!pressed && gPttHeld) {
    gPttHeld = false;
  }
#endif
}

void cyclePersona() {
  if (gPersonas.empty()) {
    return;
  }
  gPersonaIndex = (gPersonaIndex + 1) % gPersonas.size();
  gActivePersona = gPersonas[gPersonaIndex].id;
  Serial.print("[persona] Switched to ");
  Serial.print(gPersonas[gPersonaIndex].name);
  Serial.print(" (");
  Serial.print(gActivePersona);
  Serial.println(")");
}

void flashPersonaAck() {
  for (uint8_t i = 0; i < 2; i++) {
    gLed.setState(EmberLedState::PersonaSwitch);
    delayWithLed(140);
    setListenLed();
    delayWithLed(100);
  }
}

void onPersonaKey() {
  if (gState != DeviceState::Ready || gPersonas.empty()) {
    return;
  }
  cyclePersona();
  flashPersonaAck();
}

bool bootHub() {
  if (!gApi.checkCapabilities()) {
    return false;
  }

  String defaultPersona;
  if (gApi.fetchPersonas(gPersonas, defaultPersona)) {
    gActivePersona = defaultPersona;
    for (size_t i = 0; i < gPersonas.size(); i++) {
      if (gPersonas[i].id == gActivePersona) {
        gPersonaIndex = i;
        break;
      }
    }
    Serial.print("[persona] Active ");
    Serial.println(gActivePersona);
    printPersonaList();
  }

  return true;
}

bool tryHub() {
  if (!bootHub()) {
    Serial.printf("[hub] Not reachable at %s — will retry quietly\n", EMBER_BASE_URL);
    gHubReady = false;
    return false;
  }

  gHubReady = true;
  Serial.println("[hub] Connected");
  return true;
}

bool tryAudio() {
  gLed.setState(EmberLedState::AudioInit);
  if (!gAudio.begin()) {
    Serial.println("[audio] Init failed — will retry");
    gAudioReady = false;
    gLed.setState(EmberLedState::Ready);
    return false;
  }

#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
  pinMode(EMBER_BOOT_BUTTON_GPIO, INPUT_PULLUP);
  gAudio.setupPersonaKey(onPersonaKey);
  gAudio.setupMicMuteKey(onMicMuteKey);
#elif EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_KEY1
  gAudio.setupPtt(onPtt);
  gAudio.setupPersonaKey(onPersonaKey);
  gAudio.setupMicMuteKey(onMicMuteKey);
#else
  gAudio.setupPersonaKey(onPersonaKey);
  gAudio.setupMicMuteKey(onMicMuteKey);
#endif

  gAudioReady = true;
  Serial.println("[audio] ES7210/ES8311 ready");
  gAudio.playBootChime();
  gLed.setState(EmberLedState::Ready);
  return true;
}

bool captureAndConverse() {
  uint8_t *wav = nullptr;
  size_t wavLen = 0;
  bool captured = false;

#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_VAD
  captured = gAudio.recordVadUtterance(
      &wav, &wavLen, []() { gLed.setState(EmberLedState::Recording); }, pollVadControls);
#else
  gLed.setState(EmberLedState::Recording);
  captured = gAudio.recordWhileActive([]() { return gPttHeld; }, &wav, &wavLen);
#endif

  if (!captured) {
    setListenLed();
    gState = DeviceState::Ready;
    return false;
  }

  gState = DeviceState::Uploading;
  gLed.setState(EmberLedState::Uploading);

  String response;
  const bool ok = gApi.converseWithWav(wav, wavLen, gActivePersona, response);
  heap_caps_free(wav);

  if (!ok) {
    gLed.setState(EmberLedState::HubError);
    gState = DeviceState::Ready;
    delayWithLed(1500);
    setListenLed();
    return false;
  }

  gState = DeviceState::Playing;
  gLed.setState(EmberLedState::Playing);
  if (!gAudio.playResponseJson(response)) {
    Serial.println("[audio] No playback — hub returned no TTS or decode failed");
    gLed.setState(EmberLedState::PlayError);
    delayWithLed(1200);
  }

  setListenLed();
  gState = DeviceState::Ready;
  return true;
}

void setup() {
  Serial.begin(115200);
  delay(2000);
  Serial.println();
  Serial.println("EmberForge Waveshare ESP32-S3 voice client (full audio)");
  printBakedConfig();

  gLed.begin();
  gLed.setState(EmberLedState::WiFiConnecting);

  if (!gApi.connectWiFi(&gLed)) {
    Serial.println("[error] WiFi failed");
    gLed.setState(EmberLedState::WiFiError);
    gState = DeviceState::Error;
    return;
  }

  gState = DeviceState::Ready;
  gLed.setState(EmberLedState::Ready);
  blinkReadySuccess();

  tryHub();
  gLastHubTryMs = millis();
  tryAudio();

  if (gAudioReady && gHubReady) {
#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_VAD
    Serial.println("[ready] CYAN = listen | say \"Hey Ember\" (+ command) | AMBER = muted (Key 3)");
#elif EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
    Serial.println("[ready] Solid CYAN — hold BOOT to talk");
#else
    Serial.println("[ready] Solid CYAN — hold KEY1 to talk");
#endif
  } else {
    Serial.println("[ready] WiFi OK (cyan) — waiting for hub and/or audio");
  }
}

void loop() {
  gLed.tick();
  gAudio.processInput();

#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
  pollBootPtt();
#endif

  if (gState == DeviceState::Error) {
    delayWithLed(5000);
    gLed.setState(EmberLedState::WiFiConnecting);
    if (!gApi.connectWiFi(&gLed)) {
      gLed.setState(EmberLedState::WiFiError);
      return;
    }
    gState = DeviceState::Ready;
    blinkReadySuccess();
    tryHub();
    tryAudio();
    gLastHubTryMs = millis();
    return;
  }

  if (!gHubReady && (millis() - gLastHubTryMs) > 15000) {
    gLastHubTryMs = millis();
    tryHub();
  }

  if (!gAudioReady && gHubReady) {
    tryAudio();
  }

  if (gState != DeviceState::Ready || !gHubReady || !gAudioReady) {
    delay(20);
    return;
  }

#if EMBER_TRIGGER_MODE == EMBER_TRIGGER_VAD
  if (gMicEnabled) {
    captureAndConverse();
  } else {
    delay(20);
  }
#elif EMBER_TRIGGER_MODE == EMBER_TRIGGER_PTT_BOOT
  if (gPttEdge && gPttHeld && gMicEnabled) {
    gPttEdge = false;
    captureAndConverse();
  } else if (gPttEdge) {
    gPttEdge = false;
  }
#else
  if (gPttEdge && gPttHeld && gMicEnabled) {
    gPttEdge = false;
    captureAndConverse();
  } else if (gPttEdge) {
    gPttEdge = false;
  }
#endif

  delay(5);
}