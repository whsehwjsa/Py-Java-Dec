#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java 反编译工具包
提供多种反编译引擎的统一接口和便捷工具
"""

import os
from pathlib import Path

# 设置包路径
PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
__version__ = "1.0.0"

# 核心模块导入
from java_decompiler.base import JavaDecompiler
from java_decompiler.core.decompiler_manager import get_decompiler, check_java_environment

# 引擎相关组件
from java_decompiler.engines.engine_base import DecompilerEngine, EngineMetadata, EngineOption
from java_decompiler.engines.engine_manager import (
    register_engine, unregister_engine, set_default_engine,
    get_engine_instance, get_available_engines, get_engine_metadata
)

# 异常类
from java_decompiler.exceptions import (
    DecompilerError,
    JavaEnvironmentError,
    ToolNotFoundError,
    DecompilationError,
    InvalidInputError,
    OutputDirectoryError,
    ConfigurationError
)

# 工具函数
from java_decompiler.utils.file_utils import ensure_directory, is_class_file, is_jar_file, extract_jar
from java_decompiler.utils.path_utils import normalize_path

# 日志
from java_decompiler.logger.logger import setup_logger, get_logger

# 配置
from java_decompiler.config.config_manager import ConfigManager, DEFAULT_CONFIG

# 任务管理
from java_decompiler.task_manager.task_runner import TaskRunner, TaskResult, TaskStatus

# 性能分析
from java_decompiler.performance.profiler import Profiler, timing
from java_decompiler.performance.stats_collector import StatsCollector

# 诊断工具
from java_decompiler.diagnostics.diagnostic_tool import DiagnosticTool

# 命令行入口
from java_decompiler.cli.main import main
from java_decompiler.cli.parser import parse_arguments

__all__ = [
    # 核心类和函数
    "JavaDecompiler",
    "get_decompiler",
    "check_java_environment",
    # 引擎相关组件
    "DecompilerEngine",
    "EngineMetadata",
    "EngineOption",
    "register_engine",
    "unregister_engine",
    "set_default_engine",
    "get_engine_instance",
    "get_available_engines",
    "get_engine_metadata",
    # 异常类
    "DecompilerError",
    "JavaEnvironmentError",
    "ToolNotFoundError",
    "DecompilationError",
    "InvalidInputError",
    "OutputDirectoryError",
    "ConfigurationError",
    # 工具函数
    "ensure_directory",
    "is_class_file",
    "is_jar_file",
    "extract_jar",
    "normalize_path",
    # 日志
    "setup_logger",
    "get_logger",
    # 配置
    "ConfigManager",
    "DEFAULT_CONFIG",
    # 任务管理
    "TaskRunner",
    "TaskResult",
    "TaskStatus",
    # 性能分析
    "Profiler",
    "timing",
    "StatsCollector",
    # 诊断工具
    "DiagnosticTool",
    # 命令行
    "main",
    "parse_arguments",
    # 常量
    "__version__",
    "PACKAGE_DIR"
]