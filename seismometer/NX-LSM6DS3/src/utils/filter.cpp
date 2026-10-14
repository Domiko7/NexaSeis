#include "utils/filter.h"

float hpf_x = 0.0f;
float hpf_y = 0.0f;
float hpf_z = 0.0f;

int16_t prev_x = 0;
int16_t prev_y = 0;
int16_t prev_z = 0;

const float ALPHA = 0.90f;

Axis normalize(int16_t x, int16_t y, int16_t z) {
  hpf_x = ALPHA * (hpf_x + x - prev_x);
  hpf_y = ALPHA * (hpf_y + y - prev_y);
  hpf_z = ALPHA * (hpf_z + z - prev_z);

  prev_x = x;
  prev_y = y;
  prev_z = z;

  return {hpf_x * 50.0f, hpf_y * 50.0f, hpf_z * 50.0f};
}