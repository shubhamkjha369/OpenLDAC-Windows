"""OpenLDAC Logging Subsystem.

Thread-safe event logging with console and GUI observer support.
"""

from __future__ import annotations
import logging
import queue
import time
from typing import Callable

_log_queue: queue.Queue[str] = queue.Queue(maxsize=1000)
_observers: list[Callable[[str], None]] = []

class QueueHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if not _log_queue.full():
                _log_queue.put_nowait(msg)
            for obs in _observers:
                try:
                    obs(msg)
                except Exception:
                    pass
        except Exception:
            self.handleError(record)

def get_logger(name: str = "OpenLDAC") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter(
            "[%(asctime)s.%(msecs)03d] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%H:%M:%S"
        )
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        qh = QueueHandler()
        qh.setFormatter(formatter)
        logger.addHandler(qh)
    return logger

def register_log_observer(callback: Callable[[str], None]) -> None:
    if callback not in _observers:
        _observers.append(callback)

def unregister_log_observer(callback: Callable[[str], None]) -> None:
    if callback in _observers:
        _observers.remove(callback)

def drain_log_queue() -> list[str]:
    logs = []
    while not _log_queue.empty():
        try:
            logs.append(_log_queue.get_nowait())
        except queue.Empty:
            break
    return logs
