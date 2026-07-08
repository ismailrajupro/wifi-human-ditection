import logging
import numpy as np
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

logger = logging.getLogger(__name__)

COLORS = {
    "empty": "green",
    "stationary_person": "orange",
    "moving_person": "red",
    "human_present": "orange",
    "moving": "red",
}


class Visualizer:
    def __init__(self, config):
        self.enabled = config["visualization"]["enabled"]
        self.max_points = config["visualization"]["max_points"]
        self.update_interval = config["visualization"]["update_interval"]
        self.fig = None
        self.ax1 = self.ax2 = self.ax3 = None
        self.signal_line = self.z_line = self.state_text = None
        self.times = []
        self.values = []
        self.zs = []

    def start(self, title="WiFi Human Presence Detection"):
        if not self.enabled:
            return
        plt.ion()
        self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 6))
        self.fig.suptitle(title)

        self.ax1.set_ylabel("Signal (dBm / amplitude)")
        self.ax1.set_xlabel("Time (samples)")
        self.ax1.grid(True, alpha=0.3)
        self.signal_line, = self.ax1.plot([], [], "b-", lw=1, alpha=0.7)

        self.ax2.set_ylabel("Z-score")
        self.ax2.set_xlabel("Time (samples)")
        self.ax2.axhline(y=2.5, color="orange", linestyle="--", alpha=0.5, label="Stationary thresh")
        self.ax2.axhline(y=3.5, color="red", linestyle="--", alpha=0.5, label="Moving thresh")
        self.ax2.legend(loc="upper right")
        self.ax2.grid(True, alpha=0.3)
        self.z_line, = self.ax2.plot([], [], "r-", lw=1, alpha=0.7)

        self.fig.tight_layout()
        plt.show(block=False)
        logger.info("Visualizer started")

    def update(self, value, z_score, state):
        if not self.enabled:
            return
        self.times.append(len(self.times))
        self.values.append(value if value is not None else 0)
        self.zs.append(z_score)

        if len(self.times) > self.max_points:
            self.times = self.times[-self.max_points:]
            self.values = self.values[-self.max_points:]
            self.zs = self.zs[-self.max_points:]

        self.signal_line.set_data(self.times, self.values)
        self.z_line.set_data(self.times, self.zs)

        color = COLORS.get(state, "gray")
        for ax in (self.ax1, self.ax2):
            ax.set_xlim(max(0, len(self.times) - self.max_points), len(self.times))
            ax.set_ylim(
                min(np.min(self.values), np.min(self.zs)) - 2,
                max(np.max(self.values), np.max(self.zs)) + 2,
            )

        self.fig.suptitle(f"WiFi Human Detection — State: {state}", color=color, fontsize=14)

        try:
            self.fig.canvas.draw_idle()
            self.fig.canvas.flush_events()
        except Exception:
            pass

    def stop(self):
        if self.fig:
            plt.close(self.fig)
