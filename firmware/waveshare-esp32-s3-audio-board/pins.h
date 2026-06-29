#pragma once
/**
 * Pin map — Waveshare ESP32-S3-AUDIO-Board
 *
 * Same hardware as Amazon ASIN B0FPCNZS9M ("Esp32-s3 Audio board" on product sticker).
 * Official wiki: https://www.waveshare.com/wiki/ESP32-S3-AUDIO-Board
 *
 * EXIO* lines route through the TCA9555 I2C GPIO expander — use a TCA9555 driver,
 * not digitalRead/digitalWrite on ESP32 GPIO numbers.
 */

// ---------------------------------------------------------------------------
// I2C (codec control + TCA9555)
// ---------------------------------------------------------------------------

#define EMBER_I2C_SCL_PIN 10
#define EMBER_I2C_SDA_PIN 11
#define EMBER_TCA9555_I2C_ADDR 0x20

// ---------------------------------------------------------------------------
// I2S audio bus (shared MCLK/BCLK/LRCK; separate DOUT/DIN data lines)
// ---------------------------------------------------------------------------

#define EMBER_I2S_MCLK_PIN 12
#define EMBER_I2S_BCLK_PIN 13
#define EMBER_I2S_LRCK_PIN 14

/** ESP32 receives mic PCM from ES7210 (ASDOUT). */
#define EMBER_I2S_MIC_DIN_PIN 15

/** ESP32 sends speaker PCM to ES8311 (DSDIN). */
#define EMBER_I2S_SPK_DOUT_PIN 16

// ---------------------------------------------------------------------------
// Audio codecs (controlled over I2C; data over I2S above)
// ---------------------------------------------------------------------------

/** ES7210 — dual-mic ADC. Use left channel only for EmberForge mono WAV upload. */
#define EMBER_CODEC_ADC_ES7210

/** ES8311 — DAC + headphone/line path to onboard PA. Enable PA before playback. */
#define EMBER_CODEC_DAC_ES8311

/** EmberForge hub expects 16 kHz mono 16-bit PCM WAV uploads. */
#define EMBER_MIC_SAMPLE_RATE_HZ 16000
#define EMBER_MIC_BITS_PER_SAMPLE 16
#define EMBER_MIC_CHANNELS 1

/**
 * Playback rate for ES8311/I2S sink. Hub TTS is MP3 (ElevenLabs); decode then
 * resample if needed. Community ESPHome stacks often run 16 kHz end-to-end.
 */
#define EMBER_SPK_SAMPLE_RATE_HZ 16000
#define EMBER_SPK_BITS_PER_SAMPLE 16

// ---------------------------------------------------------------------------
// TCA9555 EXIO expander (logical indices used with Waveshare / AudioDriver)
// ---------------------------------------------------------------------------

/** Map silkscreen EXIOn to the expander pin index (0–15). */
#define EMBER_EXIO_PIN(n) ((n) - 1)

/** Power amplifier enable — must be driven high before speaker output. */
#define EMBER_EXIO_PA_ENABLE 9

/** TF card chip select (active level depends on driver; see Waveshare demos). */
#define EMBER_EXIO_SD_CS 4

/** audio-driver user keys: getKey(1..3) → EXIO10 / EXIO11 / EXIO12. */
#define EMBER_EXIO_KEY1 10
#define EMBER_EXIO_KEY2 11
#define EMBER_EXIO_KEY3 12

/**
 * Edge buttons left → right from USB-C (Waveshare diagram):
 *   [1 RESET] [2 BOOT] [3 KEY1 EXIO9] [4 KEY2 EXIO10] [5 KEY3 EXIO11]
 *
 * Silkscreen labels do not always match TCA9555 wiring — trust firmware behavior.
 * EmberForge docs call the mic-mute control "Key 3" (5th button / rightmost user key).
 * In code that is audio-driver getKey(1) → EXIO10 (not EXIO11).
 * Persona cycle: getKey(2) → EXIO11. EXIO9 is PA enable, not a button input.
 */
#define EMBER_DRIVER_KEY_PTT 1
#define EMBER_DRIVER_KEY_MIC_MUTE 1
#define EMBER_DRIVER_KEY_PERSONA 2

/** LCD reset (when using Waveshare SPI display FPC). */
#define EMBER_EXIO_LCD_RST 0

/** Touch panel reset */
#define EMBER_EXIO_TP_RST 1

/** Touch panel interrupt */
#define EMBER_EXIO_TP_INT 2

/** Camera power-down (DVP camera add-on). */
#define EMBER_EXIO_CAM_PWDN 5

/** Camera pin mux (see Waveshare wiki for PCLK/XCLK routing). */
#define EMBER_EXIO_CAM_SET 6

// ---------------------------------------------------------------------------
// Direct ESP32 GPIO
// ---------------------------------------------------------------------------

/** 7× WS2812 RGB ring (single data line). */
#define EMBER_RGB_LED_PIN 38
#define EMBER_RGB_LED_COUNT 7

/** BOOT (GPIO0) — hold during USB flash if port not detected. */
#define EMBER_BOOT_BUTTON_GPIO 0

// SDMMC (TF slot) — SPI/SDMMC pins per Waveshare wiki
#define EMBER_SD_SCK_PIN 40
#define EMBER_SD_MOSI_PIN 42
#define EMBER_SD_MISO_PIN 41

// ---------------------------------------------------------------------------
// EmberForge device contract timing (see device/README.md)
// ---------------------------------------------------------------------------

#define EMBER_RECORD_MAX_SECONDS 12
#define EMBER_RECORD_TRAILING_SILENCE_SECONDS 2.2f
#define EMBER_RECORD_MIN_SPEECH_SECONDS 0.35f