/**
 * Stub audio layer used when EMBER_WIFI_BRINGUP=1 (no pschatzmann static init).
 */
#include "ember_audio.h"

#if EMBER_WIFI_BRINGUP

#include <Arduino.h>
#include <functional>

bool EmberAudio::begin() {
  Serial.println("[audio] Stub mode — audio disabled for WiFi bring-up");
  return true;
}

void EmberAudio::setupPtt(const std::function<void(bool)> &) {}

void EmberAudio::setupPersonaKey(const std::function<void()> &) {}

void EmberAudio::setupMicMuteKey(const std::function<void()> &) {}

void EmberAudio::processInput() {}

bool EmberAudio::recordWhileActive(const std::function<bool()> &, uint8_t **, size_t *) {
  return false;
}

bool EmberAudio::recordVadUtterance(uint8_t **, size_t *, const std::function<void()> &,
                                    const std::function<bool()> &) {
  return false;
}

bool EmberAudio::playMp3(const uint8_t *, size_t) { return false; }

bool EmberAudio::playResponseJson(const String &) { return false; }

bool EmberAudio::playBootChime() { return false; }

#endif