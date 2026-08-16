
#include "utils/packet.h"

#include <Arduino.h>

#include "utils/wifi.h"

StationInfo station_info = {CODE, NETWORK, CHANNEL, LOCATION};

uint8_t packet_num = 0;

void send_packet(int32_t* waveform) {

  if (!ensure_connected()) {
    Serial.println("Skipping send: Server unreachable.");
    return;
  }

  WaveformPacket packet;

  memset(&packet, 0, sizeof(WaveformPacket));

  packet.timestamp = get_timestamp();

  packet.station_info = station_info;

  for (size_t i = 0; i < (sizeof(packet.waveform) / sizeof(packet.waveform[0]));
       i++) {
    packet.waveform[i] = waveform[i];
  }

  if (TRANSMISSION_PROTOCOL == "UDP") {
    udp.beginPacket(SERVER_IP, SERVER_PORT);

    udp.write((uint8_t*)&packet, sizeof(packet));

    udp.endPacket();

    Serial.print("[UDP] Successfully sent a packet (num ");
    Serial.print(packet_num);
    Serial.print(")\n");

    packet_num++;
  } else if (TRANSMISSION_PROTOCOL == "TCP") {
    size_t bytes_sent = tcp.write((uint8_t*)&packet, sizeof(packet));

    if (bytes_sent != sizeof(packet)) {
      Serial.println("Warning: TCP send buffer incomplete. Data dropped.");
    }

    Serial.print("[TCP] Successfully sent a packet of ");
    Serial.print(bytes_sent);
    Serial.print(" bytes (num ");
    Serial.print(packet_num);
    Serial.print(")\n");

    packet_num++;
  } else {
    Serial.println("Invalid transmission protocol!");
  }

  if (packet_num == 50) packet_num = 0;
}