import json
import logging
import logging.config
import sys
from pathlib import Path

# Paths definition
CONFIG_FILE = Path("logging_config.json")
LOG_DIR = Path("logs")

# Default dictionary configuration
DEFAULT_LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
        },
        "simple": {
            "format": "[%(levelname)s] %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
        "file_rotating": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "standard",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 5242880,  # 5 MB
            "backupCount": 5,
            "encoding": "utf-8",
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "standard",
            "filename": str(LOG_DIR / "errors.log"),
            "maxBytes": 5242880,  # 5 MB
            "backupCount": 3,
            "encoding": "utf-8",
        },
    },
    "loggers": {
        "": {
            "handlers": ["console", "file_rotating", "error_file"],
            "level": "DEBUG",
            "propagate": True,
        },
        "urllib3": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}


def setup_logging(config_path: Path = CONFIG_FILE) -> None:
    """Load logging configuration from a file, creating it with defaults if missing."""
    LOG_DIR.mkdir(exist_ok=True)

    if config_path.is_file():
        # File exists: Load external configuration
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except json.JSONDecodeError as exc:
            # Fallback to basic configuration if the file has syntax errors
            logging.basicConfig(level=logging.INFO)
            logging.error(f"Malformed config in {config_path}. Reverting to fallback.", exc_info=True)
            return
    else:
        # File is missing: Write default configuration to disk
        config = DEFAULT_LOGGING_CONFIG
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        print(f"[INIT] Created default logging configuration at: {config_path.resolve()}")

    logging.config.dictConfig(config)
