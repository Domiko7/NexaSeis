#include "utils/timer.h"

hw_timer_t* timer = NULL;
portMUX_TYPE timer_mux = portMUX_INITIALIZER_UNLOCKED;
volatile bool flag = false;

void IRAM_ATTR on_timer() {
  portENTER_CRITICAL_ISR(&timer_mux);
  flag = true;
  portEXIT_CRITICAL_ISR(&timer_mux);
}

void init_timer() {
  timer = timerBegin(0, 80, true);
  timerAttachInterrupt(timer, &on_timer, true);
  timerAlarmWrite(timer, GET_INTERVAL * 1000, true);
  timerAlarmEnable(timer);
}