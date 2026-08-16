#include <Arduino.h>
#include <SparkFunLSM6DS3.h>
#include <Wire.h>
#include <SPI.h>

#include "settings.h"
#include "utils/wifi.h"
#include "utils/packet.h"
#include "utils/timer.h"

int32_t value;
uint8_t count = 0;
int32_t waveform_z[SAMPLE_COUNT];
int32_t waveform_n[SAMPLE_COUNT];
int32_t waveform_e[SAMPLE_COUNT];

LSM6DS3 accel(I2C_MODE, 0x6B);


void setup() {
  Serial.begin(115200);

  init_wifi();

  delay(5000);

  accel.settings.gyroEnabled = 0;
  accel.settings.accelEnabled = 1;
  accel.settings.accelRange = 2;
  accel.settings.accelSampleRate = 208;
  accel.settings.accelBandWidth = 50;
  accel.settings.accelFifoEnabled = 1;
  accel.settings.accelFifoDecimation = 1;
  accel.settings.tempEnabled = 1;

  if (accel.begin() != 0) {
	  Serial.println("Problem starting the sensor.");
  }

  Serial.print("Configuring FIFO with no error checking...");
  accel.fifoBegin();
  Serial.print("Done!\n");
  
  Serial.print("Clearing out the FIFO...");
  accel.fifoClear();
  Serial.print("Done!\n");

}

void loop() {
  if (flag) {
    portENTER_CRITICAL(&timer_mux);
    flag = false;
    portEXIT_CRITICAL(&timer_mux);

    uint16_t wordsAvailable = accel.fifoGetStatus() & 0x0FFF;
    uint16_t samplesAvailable = wordsAvailable / 3;
    
    for (uint16_t i = 0; i < samplesAvailable && count < SAMPLE_COUNT; i++) {
      int16_t x = accel.fifoRead();
      int16_t y = accel.fifoRead();
      int16_t z = accel.fifoRead();

      waveform_e[count] = x;
      waveform_n[count] = y;
      waveform_z[count] = z;
      count++;
    }

    if (count >= SAMPLE_COUNT) {
      count = 0;
      send_packet(waveform_z);
      send_packet(waveform_n);
      send_packet(waveform_e);
    }
  }
}