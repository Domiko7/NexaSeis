#pragma once

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiUdp.h>

extern WiFiUDP udp;
extern WiFiClient tcp;

void reconnect();
bool ensure_connected();
bool is_time_synchronized();
void init_wifi();
double get_timestamp();
