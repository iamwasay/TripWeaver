import logging
import sys


def setup_logger():
    """Configures a standard console logger for the app."""
    logger = logging.getLogger("tripweaver")

    # Prevent duplicate logs if the function is called multiple times
    if logger.hasHandlers():
        return logger

    logger.setLevel(logging.INFO)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    # Create formatter (Time - Level - Message)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-7s | %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    return logger


# Create a global logger instance to import elsewhere
logger = setup_logger()
