#include "utils/wifi.h"
#include "settings.h"

WiFiUDP udp;
WiFiClient tcp;

bool is_wifi_connecting = false; 

void start_time_sync() {
  Serial.println("Starting NTP synchronization...");
  configTime(0, 0, NTP_SERVER);
}

void reconnect() {
  if (WiFi.status() != WL_CONNECTED) {
    if (!is_wifi_connecting) {
      Serial.println("Wi-Fi connection lost. Triggering fast reconnect...");
      WiFi.begin(WIFI_SSID, WIFI_PASSWORD); 
      is_wifi_connecting = true;
    }
    
    return; 
  }

  if (is_wifi_connecting) {
    Serial.println("Wi-Fi Reconnected successfully!");
    is_wifi_connecting = false;
    start_time_sync();
  }

  if (TRANSMISSION_PROTOCOL == "TCP" && !tcp.connected()) {
    static unsigned long last_tcp_attempt = 0;
    
    if (millis() - last_tcp_attempt > 3000) {
      last_tcp_attempt = millis();
      Serial.println("TCP connection lost, trying to reconnect...");
      
      tcp.stop();
      tcp.setTimeout(500);

      if (tcp.connect(SERVER_IP, SERVER_PORT)) {
        Serial.println("TCP Connection Established!");
      } else {
        Serial.println("TCP Connection Failed! Will retry...");
      }
    }
  }
}

bool ensure_connected() {
  reconnect();
  
  if (TRANSMISSION_PROTOCOL == "TCP") {
    return tcp.connected();
  }
  
  return (WiFi.status() == WL_CONNECTED);
}

void init_wifi() {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);

  Serial.println("Initializing Wi-Fi...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  unsigned long start_attempt = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start_attempt < 10000) {
    delay(100);
    Serial.print(".");
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("Wi-Fi Connected on Boot!");
    is_wifi_connecting = false;
    
    start_time_sync();
  } else {
    Serial.println("Wi-Fi Boot connection timed out. Will retry in background.");
    is_wifi_connecting = true; 
  }

  if (TRANSMISSION_PROTOCOL == "TCP" && WiFi.status() == WL_CONNECTED) {
    tcp.setTimeout(500);
    Serial.println("Attempting initial TCP connection...");
    tcp.connect(SERVER_IP, SERVER_PORT);
  }
}

bool is_time_synchronized() {
  constexpr time_t MIN_VALID_EPOCH = 1700000000;
  return time(nullptr) >= MIN_VALID_EPOCH;
}

double get_timestamp() {
    struct timeval tv;
    gettimeofday(&tv, nullptr);

    return (double)tv.tv_sec +
           (double)tv.tv_usec / 1000000.0;
}
