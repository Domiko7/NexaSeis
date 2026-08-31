#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>

#include "settings.h"
#include "utils/serial.h"

bool is_sensor_connected() {
  Wire.beginTransmission(LSM6DS3_ADDR);
  uint8_t error = Wire.endTransmission();
  
  if (error != 0) {
    String error_msg = "Caught I2C error code: " + String(error);
    Serial.println(error_msg);
    return false;
  }
  return true;
}