#include "ember_status_led.h"

#include <Adafruit_NeoPixel.h>

#include "pins.h"

namespace {

// Waveshare ring uses RGB order (GRB makes success green appear red).
Adafruit_NeoPixel gRing(EMBER_RGB_LED_COUNT, EMBER_RGB_LED_PIN, NEO_RGB + NEO_KHZ800);

}  // namespace

void EmberStatusLed::begin() {
  gRing.begin();
  gRing.setBrightness(80);
  setState(EmberLedState::Boot);
}

void EmberStatusLed::show(uint8_t r, uint8_t g, uint8_t b) {
  for (uint8_t i = 0; i < EMBER_RGB_LED_COUNT; i++) {
    gRing.setPixelColor(i, gRing.Color(r, g, b));
  }
  gRing.show();
}

void EmberStatusLed::flashOff() { show(0, 0, 0); }

void EmberStatusLed::setState(EmberLedState state) {
  state_ = state;
  pulseOn_ = true;
  lastTickMs_ = millis();

  switch (state_) {
    case EmberLedState::Boot:
      show(255, 80, 0);
      break;
    case EmberLedState::WiFiConnecting:
      show(0, 0, 255);
      break;
    case EmberLedState::HubCheck:
      show(255, 180, 0);
      break;
    case EmberLedState::AudioInit:
      show(180, 0, 255);
      break;
    case EmberLedState::Ready:
      show(0, 180, 180);
      break;
    case EmberLedState::Recording:
      show(255, 0, 0);
      break;
    case EmberLedState::Uploading:
      show(120, 0, 180);
      break;
    case EmberLedState::Playing:
      show(0, 255, 80);
      break;
    case EmberLedState::Error:
    case EmberLedState::WiFiError:
      show(255, 0, 0);
      break;
    case EmberLedState::HubError:
      show(255, 0, 180);
      break;
    case EmberLedState::PlayError:
      show(255, 120, 0);
      break;
    case EmberLedState::MicMuted:
      show(180, 90, 0);
      break;
    case EmberLedState::PersonaSwitch:
      show(100, 140, 255);
      break;
  }
}

void EmberStatusLed::tick() {
  const uint32_t now = millis();
  if (now - lastTickMs_ < 350) {
    return;
  }
  lastTickMs_ = now;

  if (state_ == EmberLedState::WiFiConnecting || state_ == EmberLedState::HubCheck ||
      state_ == EmberLedState::AudioInit || state_ == EmberLedState::Error ||
      state_ == EmberLedState::WiFiError || state_ == EmberLedState::HubError ||
      state_ == EmberLedState::PlayError || state_ == EmberLedState::MicMuted) {
    pulseOn_ = !pulseOn_;
    if (pulseOn_) {
      setState(state_);
    } else {
      show(0, 0, 0);
    }
  }
}