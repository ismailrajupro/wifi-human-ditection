import re
import time
import logging
import serial
from collections import deque

logger = logging.getLogger(__name__)

CSI_LINE_RE = re.compile(
    r"CSI_DATA\s*:\s*([\d\s,\.\-eE+]+)"
)


class CSIReceiver:
    def __init__(self, config):
        cfg = config["csi"]
        self.port = cfg["port"]
        self.baud = cfg["baud"]
        self.window_size = cfg["window_size"]
        self.buffer = deque(maxlen=self.window_size)
        self.ser = None
        self.running = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            logger.info(f"Connected to ESP32 on {self.port} @ {self.baud}")
            return True
        except Exception as e:
            logger.error(f"Failed to open {self.port}: {e}")
            return False

    def _parse_csi_line(self, line):
        try:
            line = line.strip()
            m = CSI_LINE_RE.search(line)
            if not m:
                return None
            parts = m.group(1).strip().split(",")
            values = [float(v.strip()) for v in parts if v.strip()]
            if len(values) < 64:
                return None
            amplitudes = [
                (values[i]**2 + values[i+1]**2) ** 0.5
                for i in range(0, min(len(values) - 1, 128), 2)
            ]
            return {
                "raw": values,
                "amplitude": amplitudes,
                "rssi": self._extract_rssi(line),
            }
        except Exception as e:
            logger.debug(f"Parse error: {e}")
            return None

    @staticmethod
    def _extract_rssi(line):
        m = re.search(r"rssi[\s=:]+(-?\d+)", line, re.I)
        return int(m.group(1)) if m else None

    def stream(self):
        if not self.ser and not self.connect():
            return
        self.running = True
        logger.info("CSI stream started")
        while self.running:
            try:
                line = self.ser.readline().decode("utf-8", errors="replace")
                parsed = self._parse_csi_line(line)
                if parsed:
                    self.buffer.append(parsed)
                    yield parsed
                else:
                    yield None
            except serial.SerialException:
                logger.error("Serial connection lost")
                break
            except Exception as e:
                logger.debug(f"Stream error: {e}")
                yield None

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()
