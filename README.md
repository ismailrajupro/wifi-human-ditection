# WiFi Human Presence Detection

Detect human presence using WiFi signals — no cameras, no wearables, just radio waves.

This project implements **device-free human presence detection** by analyzing how the human body affects WiFi signal propagation. It supports two sensing methods:

- **RSSI mode** — works immediately on any Windows laptop by polling signal strength via `netsh`
- **CSI mode** — uses an ESP32 microcontroller to capture fine-grained Channel State Information from 52 OFDM subcarriers for far more accurate detection

Both modes feed into a real-time visualization dashboard and use z-score based change detection to classify the environment as **empty**, **stationary person**, or **moving person**.

---

## How It Works

### Physics

The human body is mostly water, which absorbs and reflects 2.4/5 GHz radio waves. When a person enters a WiFi signal's propagation path:

- **Reflection** — the body acts as a reflector, creating new multipath components
- **Absorption** — water content attenuates signal strength by 3–10 dB
- **Scattering** — movement causes Doppler shifts in the received signal

RSSI captures the aggregate power change. CSI goes deeper, resolving individual subcarrier amplitude and phase shifts across the OFDM spectrum, giving sub-meter sensitivity.

### Detection Algorithm

Both modes use a **sliding window z-score** approach:

1. **Calibration** — collect N baseline samples with the room empty
2. **Scoring** — for each new sample, compute `z = (x - μ) / σ` against the baseline distribution
3. **Classification**:
   - `z < threshold` — empty
   - `threshold < z < 1.5×threshold` — stationary person present
   - `z > 1.5×threshold` — moving person
4. **Debouncing** — state changes must persist for `min_duration` seconds to trigger

---

## Project Structure

```
wifi_human_detection/
├── main.py                 # CLI entry point
├── config.yaml             # All tunable parameters
├── requirements.txt        # Python dependencies
│
├── src/
│   ├── rssi_monitor.py     # Windows RSSI polling (netsh)
│   ├── rssi_detector.py    # Z-score detector for RSSI data
│   ├── csi_receiver.py     # Serial parser for ESP32 CSI frames
│   ├── csi_detector.py     # Subcarrier variance detector for CSI
│   ├── visualizer.py       # Real-time matplotlib dashboard
│   ├── utils.py            # Shared helpers (config, logging, math)
│   └── __init__.py
│
├── firmware/
│   ├── esp32_csi_receiver/ # ESP-IDF project for CSI capture
│   │   ├── CMakeLists.txt
│   │   └── main/
│   │       ├── CMakeLists.txt
│   │       ├── main.c
│   │       └── Kconfig.projbuild
│   │
│   └── platformio/         # PlatformIO/Arduino variant
│       ├── platformio.ini
│       └── src/
│           └── main.cpp
│
├── scripts/
│   ├── install_deps.bat    # Install Python packages
│   └── run_monitor.bat     # Launch RSSI monitor
│
└── data/                   # Captured data directory
```

---

## Quick Start — RSSI Mode (No Hardware Required)

This works on any Windows machine with a WiFi adapter.

### 1. Install Dependencies

```powershell
pip install -r requirements.txt
```

Or double-click `scripts\install_deps.bat`.

### 2. Run the Monitor

```powershell
python main.py -m rssi
```

Or double-click `scripts\run_monitor.bat`.

### 3. Interpret the Output

```
RSSI:  -38.4 dBm | Z:  0.00 | [EMPTY]
RSSI:  -42.1 dBm | Z:  2.80 | [STATIONARY]
RSSI:  -51.7 dBm | Z:  4.20 | [MOVING]
```

A real-time matplotlib window shows the signal trace and z-score over time.

### Options

| Flag | Description |
|---|---|
| `-m rssi` or `-m csi` | Force detection mode |
| `--calibrate N` | Override calibration sample count |
| `--no-viz` | Disable matplotlib visualization (console only) |
| `-c path/to/config.yaml` | Custom config path |

---

## CSI Mode — ESP32 Hardware Setup

For accurate detection, you need an ESP32 board (~$5). The ESP32 captures Channel State Information from WiFi packets and streams it over USB serial.

### Hardware Needed

| Component | Notes |
|---|---|
| ESP32 dev board | ESP32, ESP32-S3, ESP32-C3, ESP32-C5, ESP32-C6 all work |
| USB cable | Data-capable, not just charging |
| WiFi router | Any 2.4 GHz or 5 GHz access point |

### Option A: ESP-IDF (Official)

1. Install [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/get-started/)
2. Configure the firmware:
```powershell
cd firmware\esp32_csi_receiver
idf.py menuconfig
```
Set your WiFi SSID, password, and channel under "CSI Receiver Configuration".

3. Build and flash:
```powershell
idf.py build
idf.py -p COM3 flash
```

4. Monitor:
```powershell
idf.py -p COM3 monitor
```

### Option B: PlatformIO / Arduino (Easier)

1. Install [PlatformIO](https://platformio.org/) in VS Code
2. Open `firmware\platformio\` as a project
3. Edit `src\main.cpp` with your WiFi credentials
4. Build and upload
5. Open serial monitor at 921600 baud

### Running the CSI Detector

1. Find your ESP32's serial port (`COM3`, `COM5`, etc.)
2. Edit `config.yaml`:
```yaml
csi:
  port: COM3
  baud: 921600
```
3. Run:
```powershell
python main.py -m csi
```

---

## Configuration Reference

All parameters are in `config.yaml`.

| Section | Parameter | Default | Description |
|---|---|---|---|
| `mode` | | `rssi` | Detection mode: `rssi` or `csi` |
| `rssi` | `sample_interval` | `0.2` | Seconds between RSSI polls |
| `rssi` | `window_size` | `30` | Samples in sliding window |
| `rssi` | `z_threshold` | `2.5` | Z-score threshold for detection |
| `rssi` | `baseline_samples` | `100` | Samples to calibrate baseline |
| `rssi` | `min_duration` | `2.0` | Seconds a state must persist |
| `csi` | `port` | `COM3` | ESP32 serial port |
| `csi` | `baud` | `921600` | Serial baud rate |
| `csi` | `window_size` | `50` | CSI frames in sliding window |
| `csi` | `z_threshold` | `3.0` | Z-score threshold |
| `csi` | `baseline_frames` | `200` | Frames to calibrate baseline |
| `visualization` | `enabled` | `true` | Show live matplotlib plot |
| `visualization` | `max_points` | `300` | Points on live plot |

### Tuning Tips

- **False positives (detecting when empty)** — increase `z_threshold` or increase `baseline_samples` for a more stable baseline
- **False negatives (missing presence)** — decrease `z_threshold` or decrease `min_duration`
- **Noisy signal** — increase `window_size` to smooth fluctuations
- **Slow detection** — decrease `min_duration` or `sample_interval`

---

## RSSI vs CSI: Trade-offs

| Aspect | RSSI | CSI |
|---|---|---|
| **Hardware** | Any WiFi device | ESP32 + USB |
| **Accuracy** | ~room-level | ~sub-meter |
| **Stationary person** | Poor | Good |
| **Through-wall** | Limited | Better |
| **Setup time** | 0 minutes | 30 minutes |
| **Cost** | $0 | ~$5 |
| **Subcarrier detail** | None | 52 OFDM subcarriers |
| **Update rate** | 5 Hz (netsh limit) | ~10–50 Hz |

RSSI is a **coarse** aggregate measurement — a single power number. CSI provides **fine-grained** per-subcarrier amplitude and phase, making it vastly more sensitive to subtle environmental changes.

---

## CSI Data Format

The ESP32 firmware outputs CSI frames over serial in this format:

```
CSI_DATA: frame=42,mac=a0:b1:c2:d3:e4:f5,rssi=-45,rssi_ack=-44,rate=3,channel=1,len=128,data=ab12cd34...
```

The `data` field contains 128 bytes (64 subcarriers × 2 bytes for real + imaginary components). The Python `csi_receiver.py` parser converts this to amplitude values per subcarrier.

---

## Algorithm Details

### Z-Score Detection

```
z = (current_value - mean_baseline) / std_baseline
```

- Assumes the baseline distribution is approximately Gaussian
- For RSSI: operates on raw dBm values
- For CSI: operates on mean subcarrier variance across the sliding window

### State Machine

```
                    z < threshold
    ┌─────────┐ ──────────────────► ┌─────────┐
    │ EMPTY   │                     │ EMPTY   │
    └─────────┘ ◄────────────────── └─────────┘
         │                               ▲
         │ z > threshold                  │
         ▼                               │
    ┌──────────────┐              ┌──────────────┐
    │ STATIONARY   │─────────────►│   MOVING     │
    └──────────────┘  z > 1.5×th  └──────────────┘
```

State transitions are debounced by `min_duration` to prevent flutter.

---

## References

- [Espressif ESP-CSI](https://github.com/espressif/esp-csi) — official ESP32 CSI framework
- [ESP-WIFI-CSI Guide](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi.html) — IDF documentation for CSI
- [RuView](https://github.com/ruvnet/RuView) — open-source AI WiFi sensing platform
- [ESPectre](https://github.com/francescopace/espectre) — CSI motion detection with Home Assistant
- [Through-Wall Human Pose Estimation](http://rfpose.csail.mit.edu/) — MIT CSAIL research
- [Awesome WiFi CSI Sensing](https://github.com/Marsrocky/Awesome-WiFi-CSI-Sensing) — paper collection

---

## License

MIT
"# wifi-human-ditection" 
