import time
import logging
import numpy as np
from collections import deque
from .utils import compute_zscore

logger = logging.getLogger(__name__)

STATE_EMPTY = "empty"
STATE_PRESENT = "human_present"
STATE_MOVING = "moving"


class CSIDetector:
    def __init__(self, config):
        cfg = config["csi"]
        self.window_size = cfg["window_size"]
        self.z_threshold = cfg["z_threshold"]
        self.baseline_frames = cfg["baseline_frames"]
        self.min_duration = 2.0
        self.buffer = deque(maxlen=self.window_size)
        self.baseline_amplitudes = []
        self.calibrated = False
        self.state = STATE_EMPTY
        self.state_since = time.time()

    def calibrate(self, receiver, count=None):
        count = count or self.baseline_frames
        logger.info(f"Calibrating CSI baseline over {count} frames...")
        collected = 0
        for frame in receiver.stream():
            if frame is None:
                continue
            self.baseline_amplitudes.append(np.mean(frame["amplitude"]))
            collected += 1
            if collected >= count:
                break
        self.calibrated = True
        logger.info(f"CSI calibration done")

    def _subcarrier_variance(self, frame):
        return np.var(frame["amplitude"])

    def update(self, frame):
        if frame is None:
            return self.state, 0.0
        self.buffer.append(frame)
        if len(self.buffer) < self.window_size:
            return self.state, 0.0

        current_var = np.mean([self._subcarrier_variance(f) for f in self.buffer])
        baseline_var = np.mean([self._subcarrier_variance(f)
                                 for f in self.baseline_amplitudes]) if self.baseline_amplitudes else 0

        diff = abs(current_var - baseline_var)
        z = diff / (np.std([self._subcarrier_variance(f)
                           for f in self.baseline_amplitudes]) + 1e-8)

        new_state = STATE_EMPTY
        if z > self.z_threshold * 1.5:
            new_state = STATE_MOVING
        elif z > self.z_threshold:
            new_state = STATE_PRESENT

        if new_state != self.state:
            if time.time() - self.state_since > self.min_duration:
                self.state = new_state
                self.state_since = time.time()
                logger.info(f"CSI state: {self.state} (z={z:.2f})")

        return self.state, z
