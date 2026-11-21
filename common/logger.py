import logging
import sys

from common.config import logging_config


def configure_logger(name):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # Tránh lỗi font tiếng Việt trên console Windows
    for luong in (sys.stdout, sys.stderr):
        try:
            luong.reconfigure(encoding="utf-8")  # type: ignore
        except Exception:
            pass

    formatter = logging.Formatter(logging_config["format"])

    file_handler = logging.FileHandler(logging_config["filename"], encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging_config["level"])
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger
