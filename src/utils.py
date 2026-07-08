import yaml
import logging
import numpy as np
from pathlib import Path
from datetime import datetime


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def setup_logging(cfg):
    level = getattr(logging, cfg["logging"]["level"].upper(), logging.INFO)
    fmt = "%(asctime)s [%(levelname)s] %(message)s"
    handlers = [logging.StreamHandler()]
    if cfg["logging"].get("file"):
        handlers.append(logging.FileHandler(cfg["logging"]["file"]))
    logging.basicConfig(level=level, format=fmt, handlers=handlers)


def compute_zscore(values):
    arr = np.array(values, dtype=float)
    if np.std(arr) == 0:
        return 0.0
    return (arr[-1] - np.mean(arr)) / np.std(arr)


def moving_average(data, window):
    return np.convolve(data, np.ones(window)/window, mode="valid")


def timestamp():
    return datetime.now().isoformat(timespec="milliseconds")
