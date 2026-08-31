#pragma once

#include <stdint.h>

struct Axis {
  float x;
  float y;
  float z;
};

Axis normalize(int16_t x, int16_t y, int16_t z);