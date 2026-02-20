"""
config/logging_config.py
QKD IDS — Centralised logging configuration.

Usage in any module:
    from config.logging_config import configure_logging, get_logger
    configure_logging()          # call once at entry point
    log = get_logger("qkd.simulation")
    log.info("Starting simulation...")
"""
__author__ = "Rahul Rajesh 2360445"

import logging
import logging.config
import os

# ---------------------------------------------------------------------------
# Named loggers used across the project
# "qkd.simulation"  — data generation, quantum physics engine
# "qkd.preprocess"  — feature engineering pipeline
# "qkd.training"    — model training
# "qkd.inference"   — real-time IDS inference engine
# "qkd.xai"         — SHAP and explain_logic
# "qkd.gui"         — GUI / worker thread events
# ---------------------------------------------------------------------------

_LOGGING_CONFIG: dict = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)-8s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "brief": {
            "format": "[%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "brief",
            "level": "INFO",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "standard",
            "level": "DEBUG",
            "filename": "logs/ids_audit.log",
            "maxBytes": 10_485_760,   # 10 MB before rotating
            "backupCount": 5,
            "mode": "a",
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "qkd.simulation": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "qkd.preprocess": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "qkd.training": {
            "handlers": ["console", "file"],
            "level": "DEBUG",
            "propagate": False,
        },
        "qkd.inference": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "qkd.xai": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False,
        },
        "qkd.gui": {
            "handlers": ["console", "file"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "level": "WARNING",
        "handlers": ["console"],
    },
}


def configure_logging() -> None:
    """
    Initialise logging from the built-in config dict.
    Call this exactly ONCE at the entry point of any script
    (data_generation.py, model_training.py, gui/main_window.py, etc.).
    """
    os.makedirs("logs", exist_ok=True)
    logging.config.dictConfig(_LOGGING_CONFIG)


def get_logger(name: str) -> logging.Logger:
    """
    Convenience wrapper — returns a named logger.
    Recommended names: 'qkd.simulation', 'qkd.preprocess',
    'qkd.training', 'qkd.inference', 'qkd.xai', 'qkd.gui'
    """
    return logging.getLogger(name)
