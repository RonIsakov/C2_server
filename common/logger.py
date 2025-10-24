"""
Logging Module for C2 Server

This module provides centralized logging functionality with:
- Dual output: console and file
- Session-aware logging with unique session IDs
- Configurable format and log levels
- Automatic log directory creation

This is for authorized security testing and educational purposes only.
"""

import logging
import os
from datetime import datetime
from . import config


def setup_logger(session_id: str) -> logging.Logger:
    """
    Setup a logger with dual output (console and file) for a specific session.

    Creates a logger that outputs to both the console (for real-time monitoring)
    and a file (for audit trail). The logger includes the session ID in all
    messages for tracking.

    Args:
        session_id: Unique identifier for this session (e.g., SESSION-20251024-a7f3)

    Returns:
        logging.Logger: Configured logger instance with session context

    Example:
        >>> log = setup_logger("SESSION-20251024-a7f3")
        >>> log.info("Client connected")
        2025-10-24 14:09:33 | INFO    | [SESSION-20251024-a7f3] Client connected
    """
    # Create logs directory if it doesn't exist
    os.makedirs(config.LOG_DIRECTORY, exist_ok=True)

    # Generate log filename with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f"{config.LOG_FILE_PREFIX}_{timestamp}.log"
    log_path = os.path.join(config.LOG_DIRECTORY, log_filename)

    # Create logger with unique name per session
    logger_name = f'c2_server_{session_id}'
    logger = logging.getLogger(logger_name)

    # Set logging level from config
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Clear any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Prevent propagation to root logger
    logger.propagate = False

    # Create console handler (outputs to terminal)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Create file handler (outputs to log file)
    file_handler = logging.FileHandler(log_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Create formatter with session ID prefix
    # We'll add [SESSION-ID] prefix manually in log messages
    formatter = logging.Formatter(
        config.LOG_FORMAT,
        datefmt=config.LOG_DATE_FORMAT
    )

    # Set formatter for both handlers
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    # Log the logger setup (without session prefix for this initial message)
    logger.info(f"Logger initialized for session: {session_id}")
    logger.info(f"Log file: {log_path}")

    return logger


def create_session_prefix(session_id: str) -> str:
    """
    Create a standardized session prefix for log messages.

    Args:
        session_id: The session identifier

    Returns:
        str: Formatted session prefix like "[SESSION-123]"
    """
    return f"[{session_id}]"
