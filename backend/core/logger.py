import logging
import sys
from contextvars import ContextVar
from typing import Any
from pythonjsonlogger import jsonlogger

request_id_var: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def setup_logger(name: str = "soc_copilot", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            jsonlogger.JsonFormatter(
                "%(asctime)s %(name)s %(levelname)s %(message)s %(request_id)s"
            )
        )
        handler.addFilter(RequestIdFilter())
        logger.addHandler(handler)

    return logger


# Alias for compatibility with v0.2 code
def get_logger(name: str) -> logging.Logger:
    """Get or create a logger with the given name.

    Args:
        name: Logger name, typically __name__

    Returns:
        Logger instance
    """
    return setup_logger(name)
