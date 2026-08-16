#include "ads1256.h"

#include <Arduino.h>

volatile bool DRDY_flag = false;

void IRAM_ATTR DRDY_ISR() { DRDY_flag = true; }

ADS1256::ADS1256(uint8_t sps, uint8_t g, uint8_t ain_p, uint8_t ain_n) 
  : sample_rate(sps), gain(g), _ain_p(ain_p), _ain_n(ain_n), spi(&SPI) {
}

void ADS1256::init_ADS() {
  pinMode(PIN_DRDY, INPUT);
  pinMode(PIN_CS, OUTPUT);
  digitalWrite(PIN_CS, HIGH);

  if (PIN_RST >= 0) {
    pinMode(PIN_RST, OUTPUT);
    digitalWrite(PIN_RST, HIGH);
  }

  attachInterrupt(digitalPinToInterrupt(PIN_DRDY), DRDY_ISR, FALLING);

  spi->begin();

  if (PIN_RST >= 0) {
    digitalWrite(PIN_RST, LOW);
    delay(10);
    digitalWrite(PIN_RST, HIGH);
    delay(100);
  }

  reset();
  delay(100);

  write_register(_ain_p, _ain_n);
  write_register(0x02, gain);
  write_register(0x03, sample_rate);
  delay(50);

  send_command(0xF0);
  delay(100);
}

void ADS1256::wait_DRDY() {
  while (!DRDY_flag) {
  }
  noInterrupts();
  DRDY_flag = false;
  interrupts();
}

int32_t ADS1256::read_raw() {
  wait_DRDY();

  spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(PIN_CS, LOW);

  spi->transfer(0x01);
  delayMicroseconds(7);

  uint8_t buf[3];
  buf[0] = spi->transfer(0x00);
  buf[1] = spi->transfer(0x00);
  buf[2] = spi->transfer(0x00);

  digitalWrite(PIN_CS, HIGH);
  spi->endTransaction();

  int32_t result = 0;
  result |= buf[0];
  result <<= 8;
  result |= buf[1];
  result <<= 8;
  result |= buf[2];

  if (result & 0x800000) {
    result -= 16777216;
  }

  return result;
}

void ADS1256::send_command(uint8_t cmd) {
  wait_DRDY();
  spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(PIN_CS, LOW);
  spi->transfer(cmd);
  delayMicroseconds(10);
  digitalWrite(PIN_CS, HIGH);
  spi->endTransaction();
}

void ADS1256::write_register(uint8_t reg, uint8_t value) {
  uint8_t prev = read_register(reg);
  if (prev != value) {
    wait_DRDY();
    spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
    digitalWrite(PIN_CS, LOW);
    spi->transfer(0x50 | reg);
    spi->transfer(0x00);
    spi->transfer(value);
    delayMicroseconds(10);
    digitalWrite(PIN_CS, HIGH);
    spi->endTransaction();
  }
}

uint8_t ADS1256::read_register(uint8_t reg) {
  wait_DRDY();
  spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(PIN_CS, LOW);
  spi->transfer(0x10 | reg);
  spi->transfer(0x00);
  uint8_t value = spi->transfer(0x00);
  delayMicroseconds(10);
  digitalWrite(PIN_CS, HIGH);
  spi->endTransaction();
  return value;
}

void ADS1256::reset() {
  spi->beginTransaction(SPISettings(1000000, MSBFIRST, SPI_MODE1));
  digitalWrite(PIN_CS, LOW);
  spi->transfer(0xFE);
  delay(2);
  spi->transfer(0x0F);
  delayMicroseconds(100);
  digitalWrite(PIN_CS, HIGH);
  spi->endTransaction();
}