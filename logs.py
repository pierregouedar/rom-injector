"""In-memory ring buffer log handler."""
import logging
from collections import deque

import decky

LOG_BUFFER: deque[str] = deque(maxlen=500)


class _RingHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            LOG_BUFFER.append(f"{record.levelname:<7} {record.getMessage()}")
        except Exception:
            pass


def install() -> None:
    h = _RingHandler()
    h.setLevel(logging.INFO)
    decky.logger.addHandler(h)


def tail(limit: int) -> list[str]:
    n = max(1, min(limit, len(LOG_BUFFER)))
    return list(LOG_BUFFER)[-n:]
