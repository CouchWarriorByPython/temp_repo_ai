import logging
import sys
from typing import Optional

from config import config


class Logger:
    """Центральний логер для проєкту"""
    
    _loggers = {}
    
    @classmethod
    def get_logger(cls, name: Optional[str] = None) -> logging.Logger:
        """Отримати логер з налаштуваннями"""
        if name is None:
            name = __name__
            
        if name in cls._loggers:
            return cls._loggers[name]
        
        logger = logging.getLogger(name)
        
        if not logger.handlers:
            cls._setup_logger(logger)
        
        cls._loggers[name] = logger
        return logger
    
    @classmethod
    def _setup_logger(cls, logger: logging.Logger) -> None:
        """Налаштовує логер з форматуванням та рівнем"""
        log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
        logger.setLevel(log_level)
        
        if config.is_cloud():
            formatter = logging.Formatter('%(levelname)s: %(message)s')
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        
        logger.addHandler(console_handler)
        logger.propagate = False


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Зручна функція для отримання логера"""
    return Logger.get_logger(name)


logger = get_logger(__name__) 