#pragma once

#include <Arduino.h>

enum class EmberLedState {
  Boot,
  WiFiConnecting,
  HubCheck,
  AudioInit,
  Ready,
  Recording,
  Uploading,
  Playing,
  Error,
  WiFiError,
  HubError,
  PlayError,
  MicMuted,
  PersonaSwitch,
};

class EmberStatusLed {
 public:
  void begin();
  void setState(EmberLedState state);
  void tick();
  void flashOff();

 private:
  void show(uint8_t r, uint8_t g, uint8_t b);
  EmberLedState state_ = EmberLedState::Boot;
  uint32_t lastTickMs_ = 0;
  bool pulseOn_ = false;
};