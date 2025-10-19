#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志模块实现
"""

import logging
import os
import sys
import time
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# 全局日志级别映射
LOG_LEVEL_MAP = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'WARN': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

# 全局日志配置
_global_config = {
    'level': logging.INFO,
    'console_enabled': True,
    'file_enabled': False,
    'log_file': None,
    'log_format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'date_format': '%Y-%m-%d %H:%M:%S',
    'file_max_bytes': 10 * 1024 * 1024,  # 10MB
    'file_backup_count': 5
}

# 已创建的logger实例缓存
_logger_cache: Dict[str, logging.Logger] = {}

# 当前的console和file handlers
_current_handlers = {
    'console': None,
    'file': None
}

def _get_formatter() -> logging.Formatter:
    """
    获取日志格式化器
    """
    return logging.Formatter(
        fmt=_global_config['log_format'],
        datefmt=_global_config['date_format']
    )

def setup_logger(config: Optional[Dict[str, Any]] = None) -> None:
    """
    设置全局日志配置
    
    Args:
        config: 日志配置字典，可选的键包括：
            - level: 日志级别（DEBUG, INFO, WARNING, ERROR, CRITICAL）
            - console_enabled: 是否启用控制台日志
            - file_enabled: 是否启用文件日志
            - log_file: 日志文件路径
            - log_format: 日志格式
            - date_format: 日期格式
            - file_max_bytes: 文件最大字节数
            - file_backup_count: 备份文件数量
    """
    global _global_config
    
    # 更新全局配置
    if config:
        _global_config.update(config)
    
    # 确保日志级别是整数
    if isinstance(_global_config['level'], str):
        _global_config['level'] = LOG_LEVEL_MAP.get(
            _global_config['level'].upper(), logging.INFO
        )
    
    # 重置所有已存在的logger
    for logger_name, logger_instance in _logger_cache.items():
        _configure_logger(logger_instance)

def get_logger(name: str) -> logging.Logger:
    """
    获取或创建指定名称的logger
    
    Args:
        name: logger名称
        
    Returns:
        logging.Logger: logger实例
    """
    # 检查缓存
    if name in _logger_cache:
        return _logger_cache[name]
    
    # 创建新的logger
    logger = logging.getLogger(name)
    _configure_logger(logger)
    
    # 缓存logger实例
    _logger_cache[name] = logger
    
    return logger

def _configure_logger(logger: logging.Logger) -> None:
    """
    配置指定的logger
    
    Args:
        logger: 要配置的logger实例
    """
    # 移除所有已存在的handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 设置日志级别
    logger.setLevel(_global_config['level'])
    logger.propagate = False
    
    # 添加console handler
    if _global_config['console_enabled']:
        console_handler = _get_console_handler()
        logger.addHandler(console_handler)
    
    # 添加file handler
    if _global_config['file_enabled'] and _global_config['log_file']:
        file_handler = _get_file_handler()
        if file_handler:
            logger.addHandler(file_handler)

def _get_console_handler() -> logging.StreamHandler:
    """
    获取控制台日志处理器
    """
    global _current_handlers
    
    # 如果已存在console handler，直接返回
    if _current_handlers['console']:
        return _current_handlers['console']
    
    # 创建新的console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(_global_config['level'])
    console_handler.setFormatter(_get_formatter())
    
    # 保存到当前handlers
    _current_handlers['console'] = console_handler
    
    return console_handler

def _get_file_handler() -> Optional[RotatingFileHandler]:
    """
    获取文件日志处理器
    """
    global _current_handlers
    
    log_file = _global_config['log_file']
    if not log_file:
        return None
    
    # 如果已存在file handler，直接返回
    if _current_handlers['file']:
        return _current_handlers['file']
    
    try:
        # 确保日志文件目录存在
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        
        # 创建RotatingFileHandler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=_global_config['file_max_bytes'],
            backupCount=_global_config['file_backup_count'],
            encoding='utf-8'
        )
        file_handler.setLevel(_global_config['level'])
        file_handler.setFormatter(_get_formatter())
        
        # 保存到当前handlers
        _current_handlers['file'] = file_handler
        
        return file_handler
    except Exception as e:
        # 如果创建文件处理器失败，返回None
        print(f"创建日志文件处理器失败: {e}", file=sys.stderr)
        return None

def set_log_level(level: str) -> None:
    """
    设置全局日志级别
    
    Args:
        level: 日志级别字符串（DEBUG, INFO, WARNING, ERROR, CRITICAL）
    """
    _global_config['level'] = level
    setup_logger()

def get_log_level() -> str:
    """
    获取当前全局日志级别
    
    Returns:
        str: 日志级别字符串
    """
    level = _global_config['level']
    # 如果是整数，转换为字符串
    if isinstance(level, int):
        for level_name, level_value in LOG_LEVEL_MAP.items():
            if level_value == level:
                return level_name
        return 'INFO'  # 默认返回INFO
    return level

def enable_console_logging(enable: bool = True) -> None:
    """
    启用或禁用控制台日志
    
    Args:
        enable: 是否启用
    """
    _global_config['console_enabled'] = enable
    # 如果禁用，清除console handler
    if not enable and _current_handlers['console']:
        _current_handlers['console'] = None
    setup_logger()

def enable_file_logging(log_file: Optional[str] = None) -> None:
    """
    启用文件日志
    
    Args:
        log_file: 日志文件路径，如果为None则使用当前配置的路径
    """
    if log_file:
        _global_config['log_file'] = log_file
    _global_config['file_enabled'] = True
    # 清除file handler以便重新创建
    _current_handlers['file'] = None
    setup_logger()

def disable_console_logging() -> None:
    """
    禁用控制台日志
    """
    enable_console_logging(False)

def disable_file_logging() -> None:
    """
    禁用文件日志
    """
    _global_config['file_enabled'] = False
    # 清除file handler
    if _current_handlers['file']:
        _current_handlers['file'] = None
    setup_logger()


# 提供一个简单的日志装饰器
def log_function_call(logger=None):
    """
    记录函数调用的装饰器
    
    Args:
        logger: 可选的logger实例，如果为None则使用函数模块的logger
        
    Returns:
        function: 装饰后的函数
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # 获取logger
            log = logger
            if log is None:
                log = get_logger(func.__module__)
            
            # 记录函数开始
            start_time = time.time()
            func_name = func.__name__
            log.debug(f"开始调用函数: {func_name}, 参数: {args}, {kwargs}")
            
            try:
                # 执行函数
                result = func(*args, **kwargs)
                
                # 记录函数结束
                end_time = time.time()
                duration = end_time - start_time
                log.debug(f"函数 {func_name} 执行完成，耗时: {duration:.3f}秒")
                
                return result
            except Exception as e:
                # 记录异常
                log.error(f"函数 {func_name} 执行出错: {str(e)}", exc_info=True)
                raise
        
        return wrapper
    
    return decorator


# 初始化根logger
logging.basicConfig(level=logging.WARNING, handlers=[])

# 获取默认logger实例
default_logger = get_logger('java_decompiler')