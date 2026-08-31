# NexaSeis seismometers

This directory contains the firmware and hardware work for the NexaSeis sensing devices.

See [How to build a DIY seismometer](https://domiko.dev/blog/diy-seismometer) for the accompanying hardware build guide.

> [!WARNING]
> Only **NX-1D** is currently complete. **NX-LSM6DS3** and **NX-ADXL355** are unfinished development projects and should not be expected to build or operate correctly.

## Project status

| Project | Status | Description |
| --- | --- | --- |
| [`NX-1D`](NX-1D/) | Complete | ESP32 and ADS1256 firmware for a one-axis station |
| [`NX-LSM6DS3`](NX-LSM6DS3/) | Untested | Experimental LSM6DS3 firmware (104sps not 100sps!!) |
| [`NX-ADXL355`](NX-ADXL355/) | Incomplete | Early ADXL355 firmware project |

## NX-1D setup

NX-1D is a PlatformIO project targeting an ESP32 development board. Before building or uploading it, edit [`NX-1D/include/settings.h`](NX-1D/include/settings.h) for your station and hardware.

Review at least the following settings:

- `WIFI_SSID` and `WIFI_PASSWORD` — Wi-Fi credentials;
- `CODE`, `NETWORK`, `CHANNEL`, and `LOCATION` — seismic channel identifiers, which must match the server configuration;
- `SERVER_IP`, `SERVER_PORT`, and `TRANSMISSION_PROTOCOL` — NexaSeis server connection;
- `SAMPLE_RATE`, ADC gain, input pins, and ADS1256 register values;
- ESP32 SPI, data-ready, reset, and synchronization pins;
- `ENABLE_COMPENSATION` and `ENABLE_HIGH_PASS` — optional real-time filters described below.

Do not commit real credentials or private server details to the repository.

Build and upload from the NX-1D directory:

```bash
cd seismometer/NX-1D
pio run
pio run --target upload
pio device monitor
```

## Filter limitations

The implementations controlled by `ENABLE_COMPENSATION` and `ENABLE_HIGH_PASS` are designed **only for a 4.5 Hz geophone sampled at 100 samples per second**. Do not enable them for another sensor or sample rate without calculating and validating suitable filter coefficients.

Set both options explicitly in `NX-1D/include/settings.h`:

```cpp
#define ENABLE_COMPENSATION true
#define ENABLE_HIGH_PASS true
```

Set an option to `false` when its filter is not appropriate for the connected sensor or sampling configuration.

### A note on waveform distortion

While this filter allows a $35–$50 geophone to detect low-frequency teleseismic activity, real-time Infinite Impulse Response (IIR) filters introduce phase distortion. Because different frequencies experience slight differences in group delay, wave arrivals (like P-waves and S-waves) may appear visually smoothed or stretched. For real-time event detection on low-cost hardware, this trade-off is usually well worth it.
