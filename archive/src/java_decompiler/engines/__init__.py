#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译引擎实现模块
包含各种Java反编译引擎的具体实现和管理功能
"""

from java_decompiler.engines.engine_base import DecompilerEngine, EngineMetadata, EngineOption
from java_decompiler.engines.engine_manager import (
    get_available_engines,
    get_engine_by_name,
    register_engine,
    unregister_engine,
    list_engine_names
)
from java_decompiler.engines.cfr import CFRDecompiler
from java_decompiler.engines.fernflower import FernFlowerDecompiler
from java_decompiler.engines.jadx import JADXDecompiler

__all__ = [
    "DecompilerEngine",
    "EngineMetadata",
    "EngineOption",
    "get_available_engines",
    "get_engine_by_name",
    "register_engine",
    "unregister_engine",
    "list_engine_names",
    "CFRDecompiler",
    "FernFlowerDecompiler",
    "JADXDecompiler"
]