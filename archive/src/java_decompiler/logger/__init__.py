#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志模块
提供日志记录功能
"""

from java_decompiler.logger.logger import (
    get_logger,
    setup_logger,
    set_log_level,
    get_log_level,
    enable_console_logging,
    enable_file_logging,
    disable_console_logging,
    disable_file_logging
)

__all__ = [
    'get_logger',
    'setup_logger',
    'set_log_level',
    'get_log_level',
    'enable_console_logging',
    'enable_file_logging',
    'disable_console_logging',
    'disable_file_logging'
]