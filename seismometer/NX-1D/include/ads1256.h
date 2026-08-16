#pragma once

#include <Arduino.h>
#include <SPI.h>

#include "settings.h"

class ADS1256 {
 public:
  ADS1256(uint8_t sps, uint8_t g, uint8_t ain_p, uint8_t ain_n);
  void init_ADS();
  int32_t read_raw();

 private:
  uint8_t sample_rate;
  uint8_t gain;
  uint8_t _ain_p;
  uint8_t _ain_n;
  SPIClass* spi;

  void send_command(uint8_t cmd);
  void write_register(uint8_t reg, uint8_t value);
  uint8_t read_register(uint8_t reg);
  void wait_DRDY();
  void reset();
};