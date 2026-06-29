# Pico Simple Oscilloscope

A low-cost USB oscilloscope based on Raspberry Pi Pico. Three-channel ADC sampling via USB serial, with a real-time host GUI.

## Features

- 3-channel 12-bit ADC sampling
- USB CDC serial data transmission
- Real-time waveform display (tkinter GUI)
- Cross-platform host (Windows / Linux / macOS)
- Single-file executable build support

## Hardware Requirements

| Component | Specification |
|-----------|---------------|
| MCU Board | Raspberry Pi Pico / Pico W |
| USB Cable | Micro-USB data cable |
| Probe | Dupont lines or oscilloscope probes |
| Input Voltage | **0 ~ 3.3V only** |

> **Warning:** ADC inputs must not exceed 3.3V. Use a voltage divider for higher voltages.

## Pinout

| Channel | Pico Pin | Function |
|---------|----------|----------|
| CH1 | GP26 (ADC0) | Analog input 1 |
| CH2 | GP27 (ADC1) | Analog input 2 |
| CH3 | GP28 (ADC2) | Analog input 3 |
| GND | Any GND | Common ground with DUT |

## Firmware

Upload `firmware/main.py` to the root of your Pico filesystem. Rename it to `main.py` for auto-start on boot.

### Quick Upload (Thonny)

1. Connect Pico to PC via USB
2. Open Thonny, select interpreter: **MicroPython (Raspberry Pi Pico)**
3. File → Open → `firmware/main.py`
4. File → Save as → **Raspberry Pi Pico** → name it `main.py`
5. Press **Ctrl+D** to soft-reboot

You should see the boot message in the Shell:

```
========================================
Pico Simple Oscilloscope Ready
Channels : 3
Target   : 100000 Hz
PackSize : 500 points
Commands : START | STOP | INFO | REBOOT
========================================
```

## Host Software

### Run from Source

```bash
cd host
pip install -r requirements.txt
python oscilloscope_tk.py
```

### Build Executable (Windows)

```bash
cd host
python -m PyInstaller --onefile --windowed --name "PicoScope" oscilloscope_tk.py
```

The executable will be located at `dist/PicoScope.exe`.

### Usage

1. Launch `PicoScope.exe` (or run `python oscilloscope_tk.py`)
2. Select the correct COM port from the dropdown
3. Click **Connect**
4. Click the waveform area to pause/resume

## Communication Protocol

Data is transmitted in packets over USB CDC serial.

| Bytes | Field | Description |
|-------|-------|-------------|
| 0xAA 0x55 | Sync Header | Frame synchronization |
| 1 | NumChannels | Number of active ADC channels |
| 2 | PackSize | Samples per packet (uint16, little-endian) |
| N×2 | Data | ADC values (uint16, 12-bit effective, little-endian) |

### Control Commands

Send ASCII commands followed by newline (`\n`) to Pico:

| Command | Action |
|---------|--------|
| `START` | Begin continuous sampling and transmission |
| `STOP` | Stop sampling |
| `INFO` | Print current configuration |
| `REBOOT` | Soft-reset the Pico |

## Safety & Notes

### Input Voltage Limit

**Pico ADC pins (GP26/GP27/GP28) accept 0 ~ 3.3V only.** Exceeding 3.3V will damage the ADC peripheral and may destroy the chip. Always verify the voltage of your signal source with a multimeter before connecting.

### About AC Coupling (Optional)

When measuring DC signals (e.g., 3.3V power rails), the waveform may sit at the top of the display (near 4095) because the ADC reads the full DC offset. To observe ripple or small AC variations, you may use a **0.1µF ceramic capacitor** (marked "104", non-polarized) in series between the signal source and the ADC pin.

> **Note:** 0.1µF (microfarad) is NOT 0.1F (farad). The "104" ceramic capacitor is a tiny, non-polarized component commonly used for decoupling. Do not use electrolytic or tantalum capacitors for this purpose unless you understand their polarity and voltage ratings.

### Sampling Rate

The actual achievable frame rate is limited by USB CDC throughput. If you experience low FPS, reduce `Rate_pack` in `firmware/main.py` (e.g., from 500 to 100) and update `DEFAULT_RATE_PACK` in the host script accordingly.

### Measuring Digital Signals

This is an **ADC-based oscilloscope**, not a logic analyzer. Digital signals (I2C, SPI, UART) will appear as noisy envelopes rather than clean square waves because the ADC sampling rate is much lower than typical digital clock frequencies. For digital protocol analysis, use a dedicated logic analyzer.

## Disclaimer

This project is provided as-is for educational and hobbyist purposes. The authors are not responsible for any damage to equipment, injury, or data loss resulting from the use of this hardware or software. Users assume all risks associated with connecting external circuits to the Raspberry Pi Pico. Always double-check your wiring and signal levels before powering on.

## License

MIT
