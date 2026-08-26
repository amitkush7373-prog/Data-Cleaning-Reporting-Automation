"""
Logging module for Data Cleaning & Reporting Automation.
Provides file logging, console logging, and an in-memory audit log stream.
"""
import logging
import os
from datetime import datetime
from typing import List, Dict, Any

LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, f"pipeline_{datetime.now().strftime('%Y%m%d')}.log")

# In-memory structured log history for UI display and reporting
_audit_trail: List[Dict[str, Any]] = []

logger = logging.getLogger("DataCleaner")
logger.setLevel(logging.INFO)

# Avoid duplicate handlers if reloaded
if not logger.handlers:
    # File Handler
    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        "[%(levelname)s] %(message)s"
    )
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def log_event(level: str, category: str, message: str, details: Dict[str, Any] = None):
    """
    Log an event to file, console, and the in-memory audit trail.
    
    Args:
        level: 'INFO', 'WARNING', 'ERROR', 'SUCCESS'
        category: Pipeline stage (e.g. 'LOAD', 'VALIDATE', 'CLEAN', 'TRANSFORM', 'EXPORT')
        message: Human-readable description
        details: Optional dictionary of key-value metrics
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = {
        "timestamp": timestamp,
        "level": level.upper(),
        "category": category.upper(),
        "message": message,
        "details": details or {}
    }
    _audit_trail.append(entry)

    log_msg = f"[{category.upper()}] {message}"
    if details:
        log_msg += f" | Details: {details}"

    if level.upper() == "ERROR":
        logger.error(log_msg)
    elif level.upper() == "WARNING":
        logger.warning(log_msg)
    else:
        logger.info(log_msg)


def get_audit_trail() -> List[Dict[str, Any]]:
    """Retrieve all logged audit events in current session."""
    return _audit_trail.copy()


def clear_audit_trail():
    """Reset the in-memory audit log stream."""
    global _audit_trail
    _audit_trail = []
