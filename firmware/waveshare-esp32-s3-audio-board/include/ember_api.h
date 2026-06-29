#pragma once

#include <Arduino.h>
#include <vector>

struct EmberPersonaSummary {
  String id;
  String name;
};

class EmberStatusLed;

class EmberApi {
 public:
  bool connectWiFi(EmberStatusLed *led = nullptr);
  bool checkCapabilities();
  bool fetchPersonas(std::vector<EmberPersonaSummary> &out, String &defaultId);
  bool converseWithWav(const uint8_t *wavData, size_t wavLen, const String &persona,
                       String &responseJson);

  bool isBackendReady() const { return backendReady_; }

 private:
  String url(const char *path) const;
  void applyAuth(class HTTPClient &http) const;

  bool backendReady_ = false;
};