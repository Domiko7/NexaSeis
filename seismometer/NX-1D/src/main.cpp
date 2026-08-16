#include <Arduino.h>

#include "ads1256.h"
#include "settings.h"
#include "utils/wifi.h"
#include "utils/filter.h"
#include "utils/timer.h"
#include "utils/packet.h"

int32_t value;
uint8_t count = 0;
int32_t waveform[SAMPLE_COUNT];

#if ENABLE_HIGH_PASS
  filter_iir_sos_t pre_processing_highpass_filter;
#endif

#if ENABLE_COMPENSATION
  filter_iir_df1_t compensation_filter;
#endif

ADS1256 adc(SAMPLE_RATE_BYTES, GAIN_BYTES, POSITIVE_PIN, NEGATIVE_PIN);

void setup() {
  Serial.begin(115200);

  adc.init_ADS();

  #if ENABLE_HIGH_PASS
  filter_iir_sos_new(&pre_processing_highpass_filter, PRE_PROC_HPF_COEFFS);
  #endif
  
  #if ENABLE_COMPENSATION
  filter_iir_df1_new(&compensation_filter, COMPENSATION_COEFFS_B, COMPENSATION_COEFFS_A);
  #endif

  init_wifi();

  delay(5000);

  init_timer();
}

void loop() {
  if (flag) {
    portENTER_CRITICAL(&timer_mux);
    flag = false;
    portEXIT_CRITICAL(&timer_mux);

    value = adc.read_raw();
    waveform[count] = value;

    count++;

    if (count == SAMPLE_COUNT) {
      count = 0;

      #if ENABLE_HIGH_PASS
        apply_data_pre_processing(waveform, SAMPLE_COUNT, &pre_processing_highpass_filter);
      #endif

      #if ENABLE_COMPENSATION
        apply_data_compensation(waveform, SAMPLE_COUNT, &compensation_filter);
      #endif

      send_packet(waveform);
    }
  }
}
