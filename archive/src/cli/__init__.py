#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行界面模块
提供命令行参数解析和程序入口
"""

from .argument_parser import parse_arguments, ArgumentParser
from .main import main

__all__ = ['parse_arguments', 'ArgumentParser', 'main']