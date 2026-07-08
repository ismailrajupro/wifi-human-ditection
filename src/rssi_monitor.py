import re
import time
import subprocess
import logging
from collections import deque

logger = logging.getLogger(__name__)


class RSSIMonitor:
    def __init__(self, config):
        self.interval = config["rssi"]["sample_interval"]
        self.window_size = config["rssi"]["window_size"]
        self.buffer = deque(maxlen=self.window_size)
        self.running = False

    def _get_rssi_windows(self):
        try:
            out = subprocess.check_output(
                "netsh wlan show interfaces",
                shell=True,
                stderr=subprocess.STDOUT,
                timeout=5,
            ).decode("utf-8", errors="replace")
            m = re.search(r"Signal\s*:\s*(\d+)%", out)
            if m:
                rssi_pct = int(m.group(1))
                return self._pct_to_dbm(rssi_pct)
        except Exception as e:
            logger.debug(f"Failed to read RSSI: {e}")
        return None

    @staticmethod
    def _pct_to_dbm(pct):
        return -100 + (pct / 100) * 70

    def read(self):
        return self._get_rssi_windows()

    def stream(self):
        self.running = True
        logger.info("RSSI monitor started (Windows netsh)")
        while self.running:
            val = self.read()
            if val is not None:
                self.buffer.append(val)
                yield val
            else:
                yield None
            time.sleep(self.interval)

    def stop(self):
        self.running = False
