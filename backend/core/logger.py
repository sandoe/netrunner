import sys
from pathlib import Path
from loguru import logger

# Remove default handler
logger.remove()

# Format for the logs
LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)

# Add console handler
logger.add(
    sys.stderr,
    format=LOG_FORMAT,
    level="INFO",
    colorize=True,
)


def get_logger(name: str):
    """
    Returns a configured logger instance bound to the module name.
    """
    return logger.bind(name=name)


# Expose default logger
log = logger
