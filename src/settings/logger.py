import logging
import logging.handlers

from scripts import create_folder
from settings.paths import LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s:%(levelname)s:%(name)s:%(funcName)s:%(lineno)d - %(message)s",
    handlers=[
        logging.handlers.RotatingFileHandler(
            create_folder.create(LOGS_DIR) / "logs.log", maxBytes=1024**3, backupCount=10
        ),
        logging.StreamHandler(),
    ],
)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
