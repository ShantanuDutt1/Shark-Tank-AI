"""
Tests for logging configuration.
"""

from __future__ import annotations

import logging

from config.logging_config import build_logging_config, setup_logging


def test_build_logging_config_console_only():
    config = build_logging_config(log_level="INFO", log_to_file=False)
    assert "console" in config["handlers"]
    assert "file" not in config["handlers"]
    assert config["root"]["level"] == "INFO"


def test_build_logging_config_with_file(tmp_path):
    log_file = tmp_path / "app.log"
    config = build_logging_config(log_level="DEBUG", log_to_file=True, log_file_path=str(log_file))
    assert "file" in config["handlers"]
    assert config["handlers"]["file"]["filename"] == str(log_file)


def test_setup_logging_runs_without_error(tmp_path):
    log_file = tmp_path / "app.log"
    setup_logging(log_level="DEBUG", log_to_file=True, log_file_path=str(log_file), force=True)
    logger = logging.getLogger("test_setup_logging")
    logger.info("test message")
    assert log_file.exists()
