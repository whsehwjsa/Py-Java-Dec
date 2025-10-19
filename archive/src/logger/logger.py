#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志器实现
提供统一的日志记录功能
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

# 定义日志级别
LOG_LEVELS = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL
}

# 日志颜色配置
LOG_COLORS = {
    'DEBUG': '\033[92m',  # 绿色
    'INFO': '\033[94m',   # 蓝色
    'WARNING': '\033[93m',  # 黄色
    'ERROR': '\033[91m',    # 红色
    'CRITICAL': '\033[95m',  # 紫色
    'RESET': '\033[0m'      # 重置
}

class Logger:
    """
    自定义日志器类
    """
    
    def __init__(self, 
                 name: str = 'java-decompiler',
                 level: str = 'info',
                 log_file: Optional[str] = None,
                 enable_console: bool = True,
                 enable_color: bool = True):
        """
        初始化日志器
        
        Args:
            name: 日志器名称
            level: 日志级别
            log_file: 日志文件路径
            enable_console: 是否启用控制台输出
            enable_color: 是否启用彩色输出
        """
        # 创建logger实例
        self.logger = logging.getLogger(name)
        self.logger.setLevel(LOG_LEVELS.get(level.lower(), logging.INFO))
        self.logger.propagate = False
        
        # 清除已存在的处理器
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 保存配置
        self.enable_color = enable_color
        self.level = level.lower()
        
        # 创建格式化器
        self.formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 添加控制台处理器
        if enable_console:
            self._add_console_handler()
        
        # 添加文件处理器
        if log_file:
            self._add_file_handler(log_file)
    
    def _add_console_handler(self) -> None:
        """
        添加控制台日志处理器
        """
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(LOG_LEVELS.get(self.level, logging.INFO))
        
        # 如果启用彩色输出，则使用彩色格式化器
        if self.enable_color and self._supports_color():
            console_handler.setFormatter(self._get_color_formatter())
        else:
            console_handler.setFormatter(self.formatter)
        
        self.logger.addHandler(console_handler)
    
    def _add_file_handler(self, log_file: str) -> None:
        """
        添加文件日志处理器
        
        Args:
            log_file: 日志文件路径
        """
        # 确保日志目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            Path(log_dir).mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(LOG_LEVELS.get(self.level, logging.INFO))
        file_handler.setFormatter(self.formatter)
        
        self.logger.addHandler(file_handler)
    
    def _get_color_formatter(self) -> logging.Formatter:
        """
        获取带颜色的格式化器
        
        Returns:
            带颜色的日志格式化器
        """
        class ColorFormatter(logging.Formatter):
            def format(self, record):
                log_color = LOG_COLORS.get(record.levelname, LOG_COLORS['RESET'])
                record.levelname = f"{log_color}{record.levelname}{LOG_COLORS['RESET']}"
                record.msg = f"{log_color}{record.msg}{LOG_COLORS['RESET']}"
                return super().format(record)
        
        return ColorFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    def _supports_color(self) -> bool:
        """
        检查终端是否支持彩色输出
        
        Returns:
            bool: 是否支持彩色输出
        """
        try:
            import sys
            return (
                hasattr(sys.stdout, 'isatty') and 
                sys.stdout.isatty() and
                os.name != 'nt'  # Windows命令行通常不支持ANSI颜色
            )
        except:
            return False
    
    def debug(self, message: str, **kwargs) -> None:
        """
        记录调试信息
        
        Args:
            message: 日志消息
            **kwargs: 额外参数
        """
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """
        记录信息
        
        Args:
            message: 日志消息
            **kwargs: 额外参数
        """
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """
        记录警告信息
        
        Args:
            message: 日志消息
            **kwargs: 额外参数
        """
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """
        记录错误信息
        
        Args:
            message: 日志消息
            **kwargs: 额外参数
        """
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """
        记录严重错误信息
        
        Args:
            message: 日志消息
            **kwargs: 额外参数
        """
        self.logger.critical(message, **kwargs)

# 全局日志器实例
_global_logger: Optional[Logger] = None

def setup_logger(
    name: str = 'java-decompiler',
    level: str = 'info',
    log_file: Optional[str] = None,
    enable_console: bool = True,
    enable_color: bool = True
) -> Logger:
    """
    设置全局日志器
    
    Args:
        name: 日志器名称
        level: 日志级别
        log_file: 日志文件路径
        enable_console: 是否启用控制台输出
        enable_color: 是否启用彩色输出
        
    Returns:
        Logger: 配置好的日志器实例
    """
    global _global_logger
    _global_logger = Logger(
        name=name,
        level=level,
        log_file=log_file,
        enable_console=enable_console,
        enable_color=enable_color
    )
    return _global_logger

def get_logger() -> Logger:
    """
    获取全局日志器实例
    如果全局日志器未初始化，则创建一个默认配置的日志器
    
    Returns:
        Logger: 全局日志器实例
    """
    global _global_logger
    if _global_logger is None:
        _global_logger = Logger()
    return _global_logger