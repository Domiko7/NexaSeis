#include <Arduino.h>
#include <SparkFunLSM6DS3.h>
#include <Wire.h>
#include <SPI.h>

#include "settings.h"
#include "utils/wifi.h"
#include "utils/packet.h"
#include "utils/filter.h"
#include "utils/serial.h"

int32_t waveform_z[SAMPLE_COUNT];
int32_t waveform_n[SAMPLE_COUNT];
int32_t waveform_e[SAMPLE_COUNT];

int32_t accum_x = 0;
int32_t accum_y = 0;
int32_t accum_z = 0;
uint8_t oversample_count = 0;
uint8_t count = 0;

LSM6DS3 accel(I2C_MODE, LSM6DS3_ADDR);

void setup() {
  Serial.begin(115200);

  init_wifi();

  delay(5000);

  accel.settings.gyroEnabled = 0;
  accel.settings.accelEnabled = 1;
  accel.settings.accelRange = 2;
  accel.settings.accelSampleRate = 416;
  accel.settings.accelBandWidth = 50;
  accel.settings.accelFifoEnabled = 1;
  accel.settings.accelFifoDecimation = 1;
  accel.settings.tempEnabled = 0;

  if (accel.begin() != 0) {
    Serial.println("Problem starting the sensor. Check hardware/wiring!");
  } else {
    Serial.println("LSM6DS3 initialized successfully.");
  }

  Serial.println("Configuring FIFO with no error checking...");
  accel.fifoBegin();
  Serial.println("Done!\n");
  
  Serial.println("Clearing out the FIFO...");
  accel.fifoClear();
  Serial.println("Done!\n");
}

void loop() {
  if (!is_sensor_connected()) {
    return; 
  }

  uint16_t status = accel.fifoGetStatus();

  if (status == 0xFFFF || status == 0) {
    return;
  }

  uint16_t words_available = accel.fifoGetStatus() & 0x0FFF; 
  uint16_t samples_available = words_available / 3;
  
  if (samples_available == 0) {
    return;
  }

  for (uint16_t i = 0; i < samples_available && count < SAMPLE_COUNT; i++) {
    int16_t x = accel.fifoRead();
    int16_t y = accel.fifoRead();
    int16_t z = accel.fifoRead();

    Axis normalized_packet = normalize(x, y, z);

    accum_x += normalized_packet.x;
    accum_y += normalized_packet.y;
    accum_z += normalized_packet.z;
    oversample_count++;

    if (oversample_count >= 4) {
      waveform_e[count] = (float)accum_x * 50.0f / 4.0f;
      waveform_n[count] = (float)accum_y * 50.0f / 4.0f;
      waveform_z[count] = (float)accum_z * 50.0f / 4.0f;
      
      count++;

      accum_x = 0;
      accum_y = 0;
      accum_z = 0;
      oversample_count = 0;
    }
  }

  if (count >= SAMPLE_COUNT) {
    count = 0;
    send_packet(waveform_z, CHANNEL_Z);
    send_packet(waveform_n, CHANNEL_N);
    send_packet(waveform_e, CHANNEL_E);
  }
}