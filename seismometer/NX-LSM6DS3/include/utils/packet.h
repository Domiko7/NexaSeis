#pragma once
#include <Arduino.h>

#include "settings.h"

struct __attribute__((__packed__)) StationInfo {
  char code[8];
  char network[8];
  char channel[8];
  char location[8];
};

struct __attribute__((__packed__)) WaveformPacket {
  double timestamp;
  StationInfo station_info;
  int32_t waveform[SAMPLE_COUNT];
};

void send_packet(int32_t* waveform);