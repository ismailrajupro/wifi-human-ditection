#!/usr/bin/env python3
import sys
import time
import logging
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from src.utils import load_config, setup_logging
from src.visualizer import Visualizer

logger = logging.getLogger(__name__)

import platform
_USE_COLOR = platform.system() != "Windows"
STATE_LABELS = {
    "empty": "\033[92m[EMPTY]\033[0m" if _USE_COLOR else "[EMPTY]",
    "stationary_person": "\033[93m[STATIONARY]\033[0m" if _USE_COLOR else "[STATIONARY]",
    "moving_person": "\033[91m[MOVING]\033[0m" if _USE_COLOR else "[MOVING]",
    "human_present": "\033[93m[PRESENT]\033[0m" if _USE_COLOR else "[PRESENT]",
    "moving": "\033[91m[MOVING]\033[0m" if _USE_COLOR else "[MOVING]",
}


def main():
    parser = argparse.ArgumentParser(description="WiFi Human Presence Detection")
    parser.add_argument("-c", "--config", default="config.yaml", help="Config file path")
    parser.add_argument("-m", "--mode", choices=["rssi", "csi"], help="Override detection mode")
    parser.add_argument("--calibrate", type=int, help="Calibration sample count")
    parser.add_argument("--no-viz", action="store_true", help="Disable visualization")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.mode:
        config["mode"] = args.mode
    if args.no_viz:
        config["visualization"]["enabled"] = False
    setup_logging(config)

    viz = Visualizer(config)
    viz.start()

    try:
        if config["mode"] == "rssi":
            _run_rssi_mode(config, viz, args)
        elif config["mode"] == "csi":
            _run_csi_mode(config, viz, args)
        else:
            logger.error(f"Unknown mode: {config['mode']}")
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        viz.stop()


def _run_rssi_mode(config, viz, args):
    from src.rssi_monitor import RSSIMonitor
    from src.rssi_detector import RSSIDetector

    monitor = RSSIMonitor(config)
    detector = RSSIDetector(config)

    calibrate_count = args.calibrate or config["rssi"]["baseline_samples"]
    detector.calibrate(monitor, calibrate_count)

    logger.info("Monitoring for human presence (RSSI mode)...")
    print("\nPress Ctrl+C to stop\n")

    for val in monitor.stream():
        state, z = detector.update(val)
        label = STATE_LABELS.get(state, state)
        if val is not None:
            print(f"\rRSSI: {val:6.1f} dBm | Z: {z:5.2f} | {label}   ", end="", flush=True)
        viz.update(val, z, state)


def _run_csi_mode(config, viz, args):
    from src.csi_receiver import CSIReceiver
    from src.csi_detector import CSIDetector

    receiver = CSIReceiver(config)
    detector = CSIDetector(config)

    calibrate_count = args.calibrate or config["csi"]["baseline_frames"]
    if not receiver.connect():
        logger.error("Cannot connect to ESP32. Check port and baud rate.")
        return

    detector.calibrate(receiver, calibrate_count)

    logger.info("Monitoring for human presence (CSI mode)...")
    print("\nPress Ctrl+C to stop\n")

    for frame in receiver.stream():
        state, z = detector.update(frame)
        label = STATE_LABELS.get(state, state)
        rssi = frame.get("rssi", 0) if frame else 0
        print(f"\rCSI RSSI: {rssi} | Z: {z:5.2f} | {label}   ", end="", flush=True)
        viz.update(rssi, z, state)


if __name__ == "__main__":
    main()
