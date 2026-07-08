import time
import logging
import numpy as np
from collections import deque
from .utils import compute_zscore

logger = logging.getLogger(__name__)

STATE_EMPTY = "empty"
STATE_STATIONARY = "stationary_person"
STATE_MOVING = "moving_person"


class RSSIDetector:
    def __init__(self, config):
        cfg = config["rssi"]
        self.window_size = cfg["window_size"]
        self.z_threshold = cfg["z_threshold"]
        self.baseline_samples = cfg["baseline_samples"]
        self.min_duration = cfg["min_duration"]
        self.buffer = deque(maxlen=self.window_size)
        self.baseline = deque(maxlen=self.baseline_samples)
        self.calibrated = False
        self.state = STATE_EMPTY
        self.state_since = time.time()

    def calibrate(self, monitor, count=None):
        count = count or self.baseline_samples
        logger.info(f"Calibrating baseline over {count} samples...")
        collected = 0
        for val in monitor.stream():
            if val is None:
                continue
            self.baseline.append(val)
            collected += 1
            if collected >= count:
                break
        self.calibrated = True
        logger.info(f"Baseline calibratd: mean={np.mean(self.baseline):.1f} dBm, "
                     f"std={np.std(self.baseline):.2f}")

    def update(self, rssi_value):
        if rssi_value is None:
            return self.state, 0.0
        self.buffer.append(rssi_value)
        if len(self.buffer) < self.window_size:
            return self.state, 0.0

        combined = list(self.baseline) + list(self.buffer)
        z = compute_zscore(combined)

        new_state = STATE_EMPTY
        if z > self.z_threshold * 1.5:
            new_state = STATE_MOVING
        elif z > self.z_threshold:
            new_state = STATE_STATIONARY

        if new_state != self.state:
            if time.time() - self.state_since > self.min_duration:
                self.state = new_state
                self.state_since = time.time()
                logger.info(f"State change: {self.state} (z={z:.2f})")

        return self.state, z
