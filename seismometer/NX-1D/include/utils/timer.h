#pragma once

#include <Arduino.h>

#include "settings.h"

extern hw_timer_t* timer;
extern portMUX_TYPE timer_mux;
extern volatile bool flag;

void IRAM_ATTR on_timer();
void init_timer();
