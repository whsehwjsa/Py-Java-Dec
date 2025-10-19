#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行接口模块
提供命令行参数解析和CLI入口实现
"""

from java_decompiler.cli.parser import parse_arguments
from java_decompiler.cli.main import main

__all__ = [
    "parse_arguments",
    "main"
]