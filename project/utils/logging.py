import logging
import os
from logging.handlers import RotatingFileHandler

from project.config.settings import Settings


def setup_logging(settings: Settings) -> None:
    os.makedirs("project/logs", exist_ok=True)

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console = logging.StreamHandler()
    console.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        filename="project/logs/bot.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)
