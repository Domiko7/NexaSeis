<p align="center">
  <img src="images/nexaseis_horizontal_teal.svg" alt="NexaSeis" width="520">
</p>

<p align="center">
  An open-source, collaborative seismic monitoring network built around affordable ESP32-based stations.
</p>

> [!WARNING]
> **NexaSeis is incomplete and under active development.** Expect unfinished features, breaking changes, and limited documentation. Do not rely on it for safety-critical earthquake monitoring or emergency alerts. Of the projects in `seismometer/`, only **NX-1D** is currently complete; NX-LSM6DS3 and NX-ADXL355 remain unfinished.

## Overview

NexaSeis collects waveform samples from networked seismometers, processes and stores them, and makes live station data available to other applications. This repository contains the complete stack:

- a Python ingestion and processing server;
- a Vue web interface for viewing the network and individual stations;
- firmware and KiCad design files for several ESP32-based seismometers;
- optional WebSocket, DataLink, SeedLink, and REST API services.

The server can be installed as a Python package, while its runtime behavior and station inventory remain controlled by a JSON configuration file.

## How it works

```text
ESP32 station ──UDP/TCP──> Python server ──> signal processing ──> SQLite
                                │
                                ├──> REST API / helicorders
                                ├──> WebSocket stream
                                ├──> DataLink
                                └──> SeedLink
```

Stations send fixed-size binary packets containing a timestamp, station identifiers, and five signed integer samples. The server matches each packet to a station in `src/config.json`, applies its channel sensitivity and sample rate, buffers the waveform, calculates ground-motion values, and dispatches the result to enabled outputs.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/nexaseis/` | Python server, processing pipeline, database, and services |
| `src/config.json` | Server, station, and output configuration |
| `nexaseis-web/` | Vue 3, Vuetify, and Vite web application |
| `seismometer/NX-1D/` | Complete ESP32 firmware for the ADS1256-based one-axis station |
| `seismometer/NX-LSM6DS3/` | Unfinished ESP32 firmware and KiCad hardware files for LSM6DS3 stations |
| `seismometer/NX-ADXL355/` | Unfinished ESP32/ADXL355 firmware project |
| `fdsnws/stations/` | FDSN StationXML metadata |
| `scripts/` | Development and integration helper scripts |

See the [seismometer guide](seismometer/README.md) for hardware status, NX-1D setup, and important filter limitations.

For a practical overview of the hardware, read [How to build a DIY seismometer](https://domiko.dev/blog/diy-seismometer).

## Requirements

### Server

- Python 3.11 or newer
- `obspy`
- `websockets`
- `simpledali`
- `simplemseed`
- `uvicorn`
- `fastapi[standard]`
- `numpy`

SQLite support is provided by Python's standard library and does not need a separate package.

### Web application

- Node.js 20.19+ or 22.12+
- npm

### Firmware

- PlatformIO
- an ESP32 development board
- the sensor and electronics appropriate for the selected hardware variant

## Server setup

1. Create and activate a virtual environment:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

2. Install NexaSeis and its runtime dependencies in editable mode:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -e .
   ```

3. Edit `src/config.json`. At minimum, change `data_path` to an absolute directory writable by the server process and configure the station records you intend to receive.

4. Start the server from the repository root:

   ```bash
   ./run.sh
   ```

   The installed command and equivalent module command are:

   ```bash
   nexaseis
   python -m nexaseis
   ```

By default, a source checkout reads `src/config.json`. To keep configuration elsewhere, set `NEXASEIS_CONFIG` to its path before starting the server:

```bash
export NEXASEIS_CONFIG=/absolute/path/to/config.json
nexaseis
```

With the checked-in example configuration, the server listens on:

| Service | Default address | Purpose |
| --- | --- | --- |
| UDP ingest | `0.0.0.0:50006` | Receives station packets |
| REST API | `0.0.0.0:50010` | Station state and helicorder images |
| WebSocket | `0.0.0.0:50007` | Streams processed packets |
| DataLink | `127.0.0.1:16000` | Forwards waveform data to a DataLink server |
| TCP ingest | `0.0.0.0:50005` | Optional TCP packet input; disabled by default |
| SeedLink | `0.0.0.0:18000` | Optional SeedLink service; disabled by default |

Binding to `0.0.0.0` exposes a service on every network interface. Use a firewall and more restrictive bind addresses where appropriate.

### Station configuration

Each entry in the `stations` array identifies a station by its network, code, and location. Channels define their own calibration and sampling parameters:

```json
{
  "name": "Example Station",
  "network": "XX",
  "code": "TEST",
  "location": "00",
  "channels": {
    "EHZ": {
      "sensitivity": 5408390926,
      "sample_rate": 100
    }
  },
  "lat": 52.0,
  "lon": 21.0,
  "elevation": 100
}
```

The network, station, location, and channel values sent by the device must match this configuration. Restart the server after changing the file; configuration is loaded at startup.

### API

When the API is enabled, interactive OpenAPI documentation is available at `http://localhost:50010/docs`.

Useful endpoints include:

- `GET /` — health and server time;
- `GET /stations` — latest processed values, grouped by station;
- `GET /helicorder/{network}/{code}/{location}/{channel}?type=standard` — generated helicorder image. `type` may be `standard`, `teleseismic`, or `raw`.

Waveform packets are persisted to `nexaseis.db` beneath the configured `data_path`.

## Web application

Run the development server:

```bash
cd nexaseis-web
npm ci
npm run dev
```

Create a production build:

```bash
npm run build
```

The compiled application is written to `nexaseis-web/dist/`. Preview it locally with `npm run preview`.

## Firmware

Only `seismometer/NX-1D/` is currently considered complete. The NX-LSM6DS3 and NX-ADXL355 directories contain unfinished development work and should not be expected to build or function correctly.

Read [`seismometer/README.md`](seismometer/README.md) before configuring the firmware. It documents the required NX-1D settings and the sensor-specific limitations of its compensation and high-pass filters.

Open the NX-1D directory as a PlatformIO project. Before uploading, review its `include/settings.h` and source files for Wi-Fi credentials, station identifiers, server address, sensor pins, and calibration values.

Build the NX-1D firmware from the command line:

```bash
cd seismometer/NX-1D
pio run
```

Connect the target ESP32 and upload with:

```bash
pio run --target upload
pio device monitor
```

Never commit real Wi-Fi credentials or other secrets. Keep local values in ignored files or inject them through PlatformIO build settings.

## Development checks

The web application provides the currently configured automated checks:

```bash
cd nexaseis-web
npm run lint
npm run build
```

There is not yet an automated Python or firmware test suite. When changing the server, verify startup with a writable `data_path` and exercise the relevant input/output service.

## License

NexaSeis is licensed under the [GNU Affero General Public License v3.0](LICENSE).
