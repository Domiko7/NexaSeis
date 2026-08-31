#include "utils/filter.h"

int16_t hpf_x = 0, hpf_y = 0, hpf_z = 0;
int16_t prev_x = 0, prev_y = 0, prev_z = 0;

const float ALPHA = 0.993f;

Axis normalize(int16_t x, int16_t y, int16_t z) {
  hpf_x = ALPHA * (hpf_x + x - prev_x);
  hpf_y = ALPHA * (hpf_y + y - prev_y);
  hpf_z = ALPHA * (hpf_z + z - prev_z);

  prev_x = x;
  prev_y = y;
  prev_z = z;

  return {hpf_x, hpf_y, hpf_z};
}