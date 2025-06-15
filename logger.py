import logging
import sys
from typing import Optional
from config import config


class Logger:
    _loggers = {}

    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        name = name or __name__

        if name in cls._loggers:
            return cls._loggers[name]

        logger = logging.getLogger(name)

        if not logger.handlers:
            cls._setup_logger(logger)

        cls._loggers[name] = logger
        return logger

    @classmethod
    def _setup_logger(cls, logger: logging.Logger) -> None:
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)

        formatter = logging.Formatter(
            '%(levelname)s: %(message)s' if config.is_cloud()
            else '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.propagate = False


def get_logger(name: Optional[str] = None) -> logging.Logger:
    return Logger.get_logger(name)


logger = get_logger(__name__)