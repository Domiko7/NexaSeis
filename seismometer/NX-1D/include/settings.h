#pragma once

#define ENABLE_COMPENSATION true // !!
#define ENABLE_HIGH_PASS true // !!

#define WIFI_SSID "YOUR_WIFI_SSID"
#define WIFI_PASSWORD "YOUR_WIFI_PASSWORD"
#define CODE "YOUR_CODE"
#define NETWORK "YOUR_NETWORK"
#define CHANNEL "YOUR_CHANNEL" // for vertical 4.5hz geophones -> EHZ
#define LOCATION "YOUR_LOCATION"
#define SERVER_IP "YOUR_SERVER_IP"
#define SERVER_PORT 50006
#define NTP_SERVER "time.google.com"
#define TRANSMISSION_PROTOCOL "UDP" // can be either TCP or UDP

#define SAMPLE_RATE 100
#define SAMPLE_COUNT 5
#define GAIN 64
#define POSITIVE_PIN 0x01
#define NEGATIVE_PIN 0x01 // if you're using AIN0 and AIN1 change this to 0x01

#define GAIN_BYTES 0x26
#define SAMPLE_RATE_BYTES 0b10000010

#define SEND_INTERVAL ((5 * 1000) / SAMPLE_RATE)
#define GET_INTERVAL (SEND_INTERVAL / SAMPLE_COUNT)

#define PACKET_SIZE 66

#define CLOCKMHZ 7.68
#define VREF 2.5

#define PIN_SCK 18
#define PIN_MISO 19
#define PIN_MOSI 23
#define PIN_CS 5
#define PIN_DRDY 16
#define PIN_RST -1
#define PIN_SYNC -1