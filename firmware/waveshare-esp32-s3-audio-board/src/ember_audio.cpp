#include "ember_audio.h"

#include <cmath>
#include <cstring>
#include <functional>

#include <AudioTools.h>
#include <AudioTools/AudioCodecs/CodecMP3Helix.h>
#include <AudioTools/AudioLibs/AudioBoardStream.h>
#include <AudioBoards/ESP32S3AISmartSpeaker.h>
#include <mbedtls/base64.h>

#include "pins.h"

namespace {

// Lazy-init: global AudioBoardStream ctor touches I2C before setup() and boot-loops.
AudioBoardStream *gBoardPtr = nullptr;

AudioBoardStream &board() {
  if (!gBoardPtr) {
    gBoardPtr = new AudioBoardStream(ESP32S3AISmartSpeaker);
  }
  return *gBoardPtr;
}

std::function<void(bool)> gOnPtt;
std::function<void()> gOnPersonaKey;
std::function<void()> gOnMicMuteKey;
bool gRxReady = false;
uint32_t gVadSuppressUntilMs = 0;

constexpr uint32_t kVadKeySuppressMs = 600;

void handlePttKey(bool active, int /*gpio*/, void * /*ref*/) { gOnPtt(active); }

void handlePersonaKey(bool active, int gpio, void * /*ref*/) {
  if (active) {
    gVadSuppressUntilMs = millis() + kVadKeySuppressMs;
    if (gOnPersonaKey) {
      Serial.printf("[key] Key 2 persona (gpio %d, driver getKey %d)\n", gpio,
                    EMBER_DRIVER_KEY_PERSONA);
      gOnPersonaKey();
    }
  }
}

void handleMicMuteKey(bool active, int gpio, void * /*ref*/) {
  if (active) {
    gVadSuppressUntilMs = millis() + kVadKeySuppressMs;
    if (gOnMicMuteKey) {
      Serial.printf("[key] Key 3 mic mute (gpio %d, driver getKey %d)\n", gpio,
                    EMBER_DRIVER_KEY_MIC_MUTE);
      gOnMicMuteKey();
    }
  }
}

struct WavHeader {
  char riff[4] = {'R', 'I', 'F', 'F'};
  uint32_t chunkSize = 0;
  char wave[4] = {'W', 'A', 'V', 'E'};
  char fmt[4] = {'f', 'm', 't', ' '};
  uint32_t fmtSize = 16;
  uint16_t audioFormat = 1;
  uint16_t numChannels = 1;
  uint32_t sampleRate = EMBER_MIC_SAMPLE_RATE_HZ;
  uint32_t byteRate = 0;
  uint16_t blockAlign = 0;
  uint16_t bitsPerSample = EMBER_MIC_BITS_PER_SAMPLE;
  char data[4] = {'d', 'a', 't', 'a'};
  uint32_t dataSize = 0;
};

constexpr float kBlockSeconds = 0.1f;
constexpr float kPlaybackVolume = 0.45f;
constexpr float kChimeVolume = 0.58f;
constexpr int16_t kSilenceThreshold = 120;
constexpr uint32_t kMicDebugIntervalMs = 2000;
constexpr size_t kBlockSamples =
    static_cast<size_t>(EMBER_MIC_SAMPLE_RATE_HZ * kBlockSeconds);
constexpr size_t kMaxPcmBytes =
    static_cast<size_t>(EMBER_RECORD_MAX_SECONDS * EMBER_MIC_SAMPLE_RATE_HZ *
                        EMBER_MIC_CHANNELS * (EMBER_MIC_BITS_PER_SAMPLE / 8));

bool locateJsonString(const char *json, const char *key, const char **valueStart, size_t *valueLen) {
  if (!json || !key || !valueStart || !valueLen) {
    return false;
  }

  char needle[48];
  snprintf(needle, sizeof(needle), "\"%s\"", key);
  const char *keyPos = strstr(json, needle);
  if (!keyPos) {
    return false;
  }

  const char *colonPos = strchr(keyPos + strlen(needle), ':');
  if (!colonPos) {
    return false;
  }

  int i = static_cast<int>(colonPos - json) + 1;
  while (json[i] == ' ' || json[i] == '\n' || json[i] == '\r' || json[i] == '\t') {
    i++;
  }
  if (json[i] == 'n') {
    return false;
  }
  if (json[i] != '"') {
    return false;
  }
  i++;

  const int start = i;
  bool escaped = false;
  for (; json[i] != '\0'; i++) {
    const char ch = json[i];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch == '\\') {
      escaped = true;
      continue;
    }
    if (ch == '"') {
      *valueStart = json + start;
      *valueLen = static_cast<size_t>(i - start);
      return true;
    }
  }
  return false;
}

bool decodeBase64Mp3(const char *encoded, size_t encodedLen, uint8_t **outData, size_t *outLen) {
  if (!encoded || encodedLen == 0) {
    return false;
  }

  size_t decodedLen = 0;
  const unsigned char *src = reinterpret_cast<const unsigned char *>(encoded);
  const size_t srcLen = encodedLen;

  if (mbedtls_base64_decode(nullptr, 0, &decodedLen, src, srcLen) != MBEDTLS_ERR_BASE64_BUFFER_TOO_SMALL) {
    return false;
  }

  uint8_t *buffer =
      static_cast<uint8_t *>(heap_caps_malloc(decodedLen, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!buffer) {
    return false;
  }

  if (mbedtls_base64_decode(buffer, decodedLen, &decodedLen, src, srcLen) != 0) {
    heap_caps_free(buffer);
    return false;
  }

  *outData = buffer;
  *outLen = decodedLen;
  return true;
}

}  // namespace

bool EmberAudio::begin() {
  if (!gBoardPtr) {
    gBoardPtr = new AudioBoardStream(ESP32S3AISmartSpeaker);
  }
  return beginRx();
}

void EmberAudio::setupPtt(const std::function<void(bool)> &onPtt) {
  gOnPtt = onPtt;
  board().addAction(board().getKey(EMBER_DRIVER_KEY_PTT), handlePttKey);
}

void EmberAudio::setupPersonaKey(const std::function<void()> &onPress) {
  gOnPersonaKey = onPress;
  board().addAction(board().getKey(EMBER_DRIVER_KEY_PERSONA), handlePersonaKey);
}

void EmberAudio::setupMicMuteKey(const std::function<void()> &onPress) {
  gOnMicMuteKey = onPress;
  board().addAction(board().getKey(EMBER_DRIVER_KEY_MIC_MUTE), handleMicMuteKey);
}

void EmberAudio::processInput() {
  if (gBoardPtr) {
    board().processActions();
  }
}

bool EmberAudio::beginRx() {
  if (!gBoardPtr) {
    return false;
  }
  if (gRxReady) {
    return true;
  }
  board().end();
  auto cfg = board().defaultConfig(RX_MODE);
  cfg.sample_rate = EMBER_MIC_SAMPLE_RATE_HZ;
  cfg.channels = 2;
  cfg.bits_per_sample = EMBER_MIC_BITS_PER_SAMPLE;
  cfg.input_device = ADC_INPUT_LINE1;
  cfg.sd_active = false;
  cfg.sdmmc_active = false;
  if (!board().begin(cfg)) {
    Serial.println("[audio] RX init failed");
    gRxReady = false;
    return false;
  }
  board().setVolume(1.0f);
  board().setInputVolume(1.0f);
  gRxReady = true;
  return true;
}

bool EmberAudio::beginTx() {
  if (!gBoardPtr) {
    return false;
  }
  gRxReady = false;
  board().end();
  auto cfg = board().defaultConfig(TX_MODE);
  // Waveshare ES8311 path expects stereo I2S; hub TTS is 44.1 kHz MP3.
  cfg.sample_rate = 44100;
  cfg.channels = 2;
  cfg.bits_per_sample = EMBER_SPK_BITS_PER_SAMPLE;
  cfg.output_device = DAC_OUTPUT_ALL;
  cfg.sd_active = false;
  cfg.sdmmc_active = false;
  if (!board().begin(cfg)) {
    Serial.println("[audio] TX init failed");
    return false;
  }
  board().setPAPower(true);
  board().setMute(false);
  board().setVolume(kPlaybackVolume);
  return true;
}

float EmberAudio::blockEnergy(const int16_t *samples, size_t count) {
  if (count == 0) {
    return 0.0f;
  }
  double sum = 0.0;
  for (size_t i = 0; i < count; i++) {
    const double v = static_cast<double>(samples[i]);
    sum += v * v;
  }
  return static_cast<float>(sqrt(sum / static_cast<double>(count)));
}

bool EmberAudio::recordWhileActive(const std::function<bool()> &isActive, uint8_t **wavOut,
                                   size_t *wavLen) {
  *wavOut = nullptr;
  *wavLen = 0;

  if (!beginRx()) {
    return false;
  }

  int16_t *pcm =
      static_cast<int16_t *>(heap_caps_malloc(kMaxPcmBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!pcm) {
    Serial.println("[audio] Out of memory for PCM buffer");
    return false;
  }

  const size_t stereoBlockBytes = kBlockSamples * 2 * sizeof(int16_t);
  int16_t *stereoBlock =
      static_cast<int16_t *>(heap_caps_malloc(stereoBlockBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!stereoBlock) {
    heap_caps_free(pcm);
    return false;
  }

  size_t pcmSamples = 0;
  bool speechStarted = false;
  size_t speechBlocks = 0;
  size_t silentBlocks = 0;

  const size_t maxBlocks = static_cast<size_t>(EMBER_RECORD_MAX_SECONDS / kBlockSeconds);
  const size_t silenceBlocksNeeded =
      static_cast<size_t>(EMBER_RECORD_TRAILING_SILENCE_SECONDS / kBlockSeconds);
  const size_t minSpeechBlocks =
      static_cast<size_t>(EMBER_RECORD_MIN_SPEECH_SECONDS / kBlockSeconds);

  Serial.println("[audio] Recording (hold PTT)...");

  for (size_t block = 0; block < maxBlocks; block++) {
    if (!isActive()) {
      break;
    }

    const size_t readBytes =
        board().readBytes(reinterpret_cast<uint8_t *>(stereoBlock), stereoBlockBytes);
    const size_t stereoSamples = readBytes / sizeof(int16_t);
    if (stereoSamples < 2) {
      continue;
    }

    const size_t frames = stereoSamples / 2;
    for (size_t i = 0; i < frames; i++) {
#if EMBER_MIC_USE_LEFT_CHANNEL_ONLY
      pcm[pcmSamples++] = stereoBlock[i * 2];
#else
      const int32_t mixed =
          (static_cast<int32_t>(stereoBlock[i * 2]) + static_cast<int32_t>(stereoBlock[i * 2 + 1])) / 2;
      pcm[pcmSamples++] = static_cast<int16_t>(mixed);
#endif
    }

    const float energy = blockEnergy(pcm + pcmSamples - frames, frames);
    if (energy >= kSilenceThreshold) {
      speechStarted = true;
      speechBlocks++;
      silentBlocks = 0;
    } else if (speechStarted) {
      silentBlocks++;
      if (silentBlocks >= silenceBlocksNeeded && speechBlocks >= minSpeechBlocks) {
        break;
      }
    }
  }

  heap_caps_free(stereoBlock);

  if (!speechStarted || speechBlocks < minSpeechBlocks) {
    Serial.println("[audio] No clear speech detected");
    heap_caps_free(pcm);
    return false;
  }

  const uint32_t dataBytes = static_cast<uint32_t>(pcmSamples * sizeof(int16_t));
  WavHeader header;
  header.numChannels = EMBER_MIC_CHANNELS;
  header.sampleRate = EMBER_MIC_SAMPLE_RATE_HZ;
  header.bitsPerSample = EMBER_MIC_BITS_PER_SAMPLE;
  header.byteRate = header.sampleRate * header.numChannels * (header.bitsPerSample / 8);
  header.blockAlign = header.numChannels * (header.bitsPerSample / 8);
  header.dataSize = dataBytes;
  header.chunkSize = 36 + dataBytes;

  const size_t wavSize = sizeof(WavHeader) + dataBytes;
  uint8_t *wav =
      static_cast<uint8_t *>(heap_caps_malloc(wavSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!wav) {
    heap_caps_free(pcm);
    return false;
  }

  memcpy(wav, &header, sizeof(WavHeader));
  memcpy(wav + sizeof(WavHeader), pcm, dataBytes);
  heap_caps_free(pcm);

  *wavOut = wav;
  *wavLen = wavSize;

  Serial.printf("[audio] Captured %.2fs (%u bytes WAV)\n",
                static_cast<double>(pcmSamples) / EMBER_MIC_SAMPLE_RATE_HZ, wavSize);
  return true;
}

bool EmberAudio::recordVadUtterance(uint8_t **wavOut, size_t *wavLen,
                                    const std::function<void()> &onSpeechStart,
                                    const std::function<bool()> &shouldAbort) {
  *wavOut = nullptr;
  *wavLen = 0;

  if (!beginRx()) {
    return false;
  }

  int16_t *pcm =
      static_cast<int16_t *>(heap_caps_malloc(kMaxPcmBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!pcm) {
    return false;
  }

  const size_t stereoBlockBytes = kBlockSamples * 2 * sizeof(int16_t);
  int16_t *stereoBlock =
      static_cast<int16_t *>(heap_caps_malloc(stereoBlockBytes, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!stereoBlock) {
    heap_caps_free(pcm);
    return false;
  }

  const size_t maxBlocks = static_cast<size_t>(EMBER_RECORD_MAX_SECONDS / kBlockSeconds);
  const size_t silenceBlocksNeeded =
      static_cast<size_t>(EMBER_RECORD_TRAILING_SILENCE_SECONDS / kBlockSeconds);
  const size_t minSpeechBlocks =
      static_cast<size_t>(EMBER_RECORD_MIN_SPEECH_SECONDS / kBlockSeconds);

  size_t pcmSamples = 0;
  bool speechStarted = false;
  size_t speechBlocks = 0;
  size_t silentBlocks = 0;

  Serial.println("[audio] Listening — speak clearly toward the mics...");

  uint32_t lastMicDebugMs = millis();
  float peakEnergy = 0.0f;

  for (size_t block = 0; block < maxBlocks; block++) {
    if (shouldAbort && shouldAbort()) {
      Serial.println("[audio] VAD cancelled (mic muted or key)");
      heap_caps_free(stereoBlock);
      heap_caps_free(pcm);
      return false;
    }

    const size_t readBytes =
        board().readBytes(reinterpret_cast<uint8_t *>(stereoBlock), stereoBlockBytes);
    const size_t stereoSamples = readBytes / sizeof(int16_t);
    if (stereoSamples < 2) {
      if (block == 0) {
        Serial.println("[audio] Warning: no mic samples — check ES7210 path");
      }
      continue;
    }

    const size_t frames = stereoSamples / 2;
    int16_t monoBlock[kBlockSamples];
    for (size_t i = 0; i < frames; i++) {
#if EMBER_MIC_USE_LEFT_CHANNEL_ONLY
      const int16_t left = stereoBlock[i * 2];
      const int16_t right = stereoBlock[i * 2 + 1];
      monoBlock[i] = (abs(left) >= abs(right)) ? left : right;
#else
      monoBlock[i] = static_cast<int16_t>(
          (static_cast<int32_t>(stereoBlock[i * 2]) + static_cast<int32_t>(stereoBlock[i * 2 + 1])) /
          2);
#endif
    }

    const float energy = blockEnergy(monoBlock, frames);
    if (energy > peakEnergy) {
      peakEnergy = energy;
    }
    const uint32_t now = millis();
    if ((now - lastMicDebugMs) >= kMicDebugIntervalMs) {
      Serial.printf("[audio] Mic level peak=%.0f (need >%d to trigger)\n", peakEnergy,
                    kSilenceThreshold);
      peakEnergy = 0.0f;
      lastMicDebugMs = now;
    }
    if (!speechStarted) {
      if (millis() < gVadSuppressUntilMs) {
        continue;
      }
      if (energy >= kSilenceThreshold) {
        speechStarted = true;
        speechBlocks = 1;
        silentBlocks = 0;
        if (onSpeechStart) {
          onSpeechStart();
        }
        for (size_t i = 0; i < frames; i++) {
          pcm[pcmSamples++] = monoBlock[i];
        }
      }
      continue;
    }

    for (size_t i = 0; i < frames; i++) {
      pcm[pcmSamples++] = monoBlock[i];
    }

    if (energy >= kSilenceThreshold) {
      speechBlocks++;
      silentBlocks = 0;
    } else {
      silentBlocks++;
      if (silentBlocks >= silenceBlocksNeeded && speechBlocks >= minSpeechBlocks) {
        break;
      }
    }
  }

  heap_caps_free(stereoBlock);

  if (!speechStarted || speechBlocks < minSpeechBlocks) {
    heap_caps_free(pcm);
    return false;
  }

  const uint32_t dataBytes = static_cast<uint32_t>(pcmSamples * sizeof(int16_t));
  WavHeader header;
  header.numChannels = EMBER_MIC_CHANNELS;
  header.sampleRate = EMBER_MIC_SAMPLE_RATE_HZ;
  header.bitsPerSample = EMBER_MIC_BITS_PER_SAMPLE;
  header.byteRate = header.sampleRate * header.numChannels * (header.bitsPerSample / 8);
  header.blockAlign = header.numChannels * (header.bitsPerSample / 8);
  header.dataSize = dataBytes;
  header.chunkSize = 36 + dataBytes;

  const size_t wavSize = sizeof(WavHeader) + dataBytes;
  uint8_t *wav =
      static_cast<uint8_t *>(heap_caps_malloc(wavSize, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT));
  if (!wav) {
    heap_caps_free(pcm);
    return false;
  }

  memcpy(wav, &header, sizeof(WavHeader));
  memcpy(wav + sizeof(WavHeader), pcm, dataBytes);
  heap_caps_free(pcm);

  *wavOut = wav;
  *wavLen = wavSize;

  Serial.printf("[audio] VAD captured %.2fs\n",
                static_cast<double>(pcmSamples) / EMBER_MIC_SAMPLE_RATE_HZ);
  return true;
}

bool EmberAudio::playMp3(const uint8_t *data, size_t len) {
  if (!data || len == 0) {
    return false;
  }

  if (!beginTx()) {
    return false;
  }

  MemoryStream mp3Stream(const_cast<uint8_t *>(data), len);
  MP3DecoderHelix decoder;
  EncodedAudioStream decoded(&board(), &decoder);

  if (!decoded.begin()) {
    Serial.println("[audio] MP3 decoder init failed");
    return false;
  }

  StreamCopy copier(decoded, mp3Stream);
  Serial.printf("[audio] Playing response (%u byte MP3)...\n", len);
  copier.copyAll();

  const AudioInfo info = decoded.decoder().audioInfo();
  Serial.printf("[audio] Decoded %u Hz, %u ch\n", info.sample_rate, info.channels);

  decoder.end();
  decoded.end();
  delay(100);
  beginRx();
  return true;
}

bool EmberAudio::playBootChime() {
  if (!beginTx()) {
    return false;
  }

  constexpr uint32_t kChimeMs = 520;
  constexpr uint32_t kFadeInMs = 140;
  constexpr uint32_t kFadeOutMs = 220;

  AudioInfo info(44100, 2, 16);
  SineGenerator<int16_t> sine(4200);
  GeneratedSoundStream<int16_t> tone(sine);
  StreamCopy copier(board(), tone);
  sine.begin(info, N_G3);

  Serial.println("[audio] Boot chime (speaker test)...");
  const uint32_t start = millis();
  const uint32_t end = start + kChimeMs;
  while ((int32_t)(millis() - end) < 0) {
    const uint32_t elapsed = millis() - start;
    float envelope = 1.0f;
    if (elapsed < kFadeInMs) {
      envelope = static_cast<float>(elapsed) / static_cast<float>(kFadeInMs);
    } else if (elapsed > kChimeMs - kFadeOutMs) {
      envelope = static_cast<float>(end - millis()) / static_cast<float>(kFadeOutMs);
    }
    board().setVolume(kChimeVolume * envelope);
    copier.copy();
  }

  beginRx();
  return true;
}

bool EmberAudio::playResponseJson(const String &json) {
  const char *raw = json.c_str();
  const char *valueStart = nullptr;
  size_t valueLen = 0;

  if (strstr(raw, "\"ignored\":true") != nullptr) {
    if (locateJsonString(raw, "transcript", &valueStart, &valueLen) && valueLen > 0) {
      Serial.print("[wake] Ignored (say \"Hey Ember\" first): ");
      Serial.write(reinterpret_cast<const uint8_t *>(valueStart), valueLen);
      Serial.println();
    } else {
      Serial.println("[wake] Ignored — say \"Hey Ember\" to activate");
    }
    return true;
  }

  if (locateJsonString(raw, "transcript", &valueStart, &valueLen) && valueLen > 0) {
    Serial.print("[you] ");
    Serial.write(reinterpret_cast<const uint8_t *>(valueStart), valueLen);
    Serial.println();
  }

  if (locateJsonString(raw, "response_text", &valueStart, &valueLen) && valueLen > 0) {
    Serial.print("[ember] ");
    Serial.write(reinterpret_cast<const uint8_t *>(valueStart), valueLen);
    Serial.println();
  }

  if (!locateJsonString(raw, "audio_base64", &valueStart, &valueLen) || valueLen == 0) {
    Serial.println("[audio] No voice.audio_base64 in response (enable ElevenLabs on hub)");
    return false;
  }

  Serial.printf("[audio] TTS base64=%u chars\n", valueLen);

  uint8_t *mp3Data = nullptr;
  size_t mp3Len = 0;
  if (!decodeBase64Mp3(valueStart, valueLen, &mp3Data, &mp3Len)) {
    Serial.println("[audio] Base64 MP3 decode failed");
    return false;
  }

  Serial.printf("[audio] MP3 payload %u bytes\n", mp3Len);
  const bool ok = playMp3(mp3Data, mp3Len);
  heap_caps_free(mp3Data);
  if (!ok) {
    Serial.println("[audio] Playback failed");
  }
  return ok;
}