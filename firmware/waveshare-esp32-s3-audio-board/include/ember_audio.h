#pragma once

#include <Arduino.h>
#include <functional>

class EmberAudio {
 public:
  bool begin();
  void setupPtt(const std::function<void(bool)> &onPtt);
  void setupPersonaKey(const std::function<void()> &onPress);
  /** Key 3 (5th from USB) — toggle mic listen on/off (VAD hands-free). */
  void setupMicMuteKey(const std::function<void()> &onPress);
  void processInput();
  bool recordWhileActive(const std::function<bool()> &isActive, uint8_t **wavOut,
                         size_t *wavLen);
  /** Wait for speech, record one utterance, stop on trailing silence (no button). */
  bool recordVadUtterance(uint8_t **wavOut, size_t *wavLen,
                          const std::function<void()> &onSpeechStart = nullptr,
                          const std::function<bool()> &shouldAbort = nullptr);
  bool playMp3(const uint8_t *data, size_t len);
  bool playResponseJson(const String &json);
  /** Short sine tone — verifies ES8311 + PA before first converse. */
  bool playBootChime();

 private:
  bool beginRx();
  bool beginTx();
  static float blockEnergy(const int16_t *samples, size_t count);
};