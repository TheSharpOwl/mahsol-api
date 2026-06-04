import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Structured JSON log formatter for production observability."""

    _SKIP_KEYS = frozenset({
        "name", "msg", "args", "levelname", "levelno", "pathname",
        "filename", "module", "funcName", "lineno", "exc_info",
        "exc_text", "stack_info", "created", "msecs", "relativeCreated",
        "thread", "threadName", "processName", "process", "message",
        "taskName",
    })

    def format(self, record: logging.LogRecord) -> str:
        record.message = record.getMessage()

        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.message,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)

        # Merge any extra={} fields passed by the caller
        for key, value in record.__dict__.items():
            if key not in self._SKIP_KEYS and not key.startswith("_"):
                entry[key] = value

        return json.dumps(entry, default=str, ensure_ascii=False)


def setup_logging() -> None:
    """Configure application-wide structured logging."""
    from app.core.config import settings

    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root = logging.getLogger()
    root.setLevel(log_level)

    # Remove any handlers added by uvicorn or other libraries before us
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)

    if settings.LOG_FORMAT == "json":
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.addHandler(handler)

    # Suppress noisy third-party loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("tensorflow").setLevel(logging.WARNING)
    logging.getLogger("h5py").setLevel(logging.WARNING)
