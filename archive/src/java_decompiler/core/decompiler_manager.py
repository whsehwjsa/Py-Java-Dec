#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译引擎管理器
负责管理、选择和初始化不同的反编译引擎
"""

import os
import importlib
from typing import Dict, List, Optional, Any, Union

from java_decompiler.base import JavaDecompiler
from java_decompiler.engines.engine_base import DecompilerEngine
from java_decompiler.engines.engine_manager import (
    register_engine, unregister_engine, set_default_engine,
    get_engine_instance as get_engine_instance_impl,
    get_available_engines as get_available_engines_impl,
    get_engine_metadata as get_engine_metadata_impl
)
from java_decompiler.exceptions import EngineNotFoundError, ConfigurationError, InvalidInputError
from java_decompiler.utils.path_utils import normalize_path
from java_decompiler.utils.file_utils import is_class_file, is_jar_file, is_apk_file

# 支持的引擎映射
SUPPORTED_ENGINES = {
    "cfr": "java_decompiler.engines.cfr.CFRDecompiler",
    "fernflower": "java_decompiler.engines.fernflower.FernFlowerDecompiler",
    "jadx": "java_decompiler.engines.jadx.JADXDecompiler"
}


class DecompilerManager:
    """
    反编译引擎管理器
    提供引擎注册、选择和创建功能
    集成了新的引擎管理机制
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化反编译引擎管理器
        
        Args:
            config: 全局配置字典
        """
        self.config = config or {}
        self._engines = {}  # 缓存已创建的引擎实例
        self._available_engines = None  # 缓存可用引擎列表
    
    def get_decompiler(self, engine_name: str, engine_config: Optional[Dict[str, Any]] = None) -> Union[JavaDecompiler, DecompilerEngine]:
        """
        获取指定的反编译引擎实例
        
        Args:
            engine_name: 引擎名称
            engine_config: 引擎特定配置
            
        Returns:
            Union[JavaDecompiler, DecompilerEngine]: 反编译引擎实例
            
        Raises:
            EngineNotFoundError: 引擎未找到
            ConfigurationError: 配置错误
        """
        engine_name = engine_name.lower()
        
        # 检查引擎是否缓存
        cache_key = (engine_name, str(engine_config))
        if cache_key in self._engines:
            return self._engines[cache_key]
        
        try:
            # 构建完整配置，包含全局配置和引擎特定配置
            # 注意：我们传递整个配置对象给get_engine_instance_impl，
            # 它会负责提取正确的引擎配置部分
            full_config = self.config.copy() if self.config else {}
            
            # 如果提供了引擎特定配置，更新到full_config中
            if engine_config:
                # 如果全局配置没有engines键，创建它
                if "engines" not in full_config:
                    full_config["engines"] = {}
                
                # 更新特定引擎的配置
                if engine_name not in full_config["engines"]:
                    full_config["engines"][engine_name] = {}
                full_config["engines"][engine_name].update(engine_config)
            
            # 使用新的引擎管理机制获取实例（它现在能处理新的配置结构）
            engine = get_engine_instance_impl(engine_name, full_config)
            
            # 缓存引擎实例
            self._engines[cache_key] = engine
            
            return engine
            
        except Exception as e:
            if isinstance(e, (EngineNotFoundError, ConfigurationError)):
                raise
            raise ConfigurationError(f"获取引擎 {engine_name} 实例时出错: {str(e)}")
    
    def get_available_engines(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有可用的反编译引擎信息
        
        Returns:
            Dict: 可用引擎信息字典
                格式: {engine_name: {"available": bool, "version": str, "description": str, "metadata": EngineMetadata}}
        """
        if self._available_engines is not None:
            return self._available_engines.copy()
        
        # 使用新的引擎管理机制获取可用引擎
        engines_info = get_available_engines_impl()
        
        self._available_engines = engines_info
        return engines_info.copy()
    
    def select_best_engine(self, file_path: Optional[str] = None) -> str:
        """
        根据文件类型和可用性选择最佳引擎
        
        Args:
            file_path: 要反编译的文件路径
            
        Returns:
            str: 最佳引擎名称
            
        Raises:
            EngineNotFoundError: 没有可用的引擎
        """
        available_engines = self.get_available_engines()
        
        # 过滤出可用的引擎
        active_engines = [name for name, info in available_engines.items() if info["available"]]
        
        if not active_engines:
            raise EngineNotFoundError("没有可用的反编译引擎")
        
        # 根据文件类型选择引擎
        if file_path:
            file_ext = os.path.splitext(file_path)[1].lower()
            
            # APK文件优先选择JADX
            if file_ext == ".apk" and "jadx" in active_engines:
                return "jadx"
            
            # JAR文件可以使用任何引擎，但优先选择CFR
            elif file_ext == ".jar" or file_ext == ".war" or file_ext == ".ear":
                if "cfr" in active_engines:
                    return "cfr"
                elif "fernflower" in active_engines:
                    return "fernflower"
                else:
                    return active_engines[0]
            
            # 单个类文件优先选择CFR
            elif file_ext == ".class":
                if "cfr" in active_engines:
                    return "cfr"
                elif "fernflower" in active_engines:
                    return "fernflower"
                else:
                    return active_engines[0]
        
        # 默认优先级：CFR > FernFlower > JADX
        for engine in ["cfr", "fernflower", "jadx"]:
            if engine in active_engines:
                return engine
        
        # 如果没有上述引擎，返回第一个可用引擎
        return active_engines[0]
    
    def clear_cache(self):
        """
        清除引擎实例缓存
        """
        self._engines.clear()
        self._available_engines = None


def get_decompiler(engine_name: str, config: Optional[Dict[str, Any]] = None) -> Union[JavaDecompiler, DecompilerEngine]:
    """
    便捷函数：获取指定的反编译引擎实例
    
    Args:
        engine_name: 引擎名称
        config: 配置字典
        
    Returns:
        Union[JavaDecompiler, DecompilerEngine]: 反编译引擎实例
        
    Raises:
        EngineNotFoundError: 引擎未找到
        ConfigurationError: 配置错误
    """
    manager = DecompilerManager(config)
    return manager.get_decompiler(engine_name)


def check_java_environment() -> bool:
    """
    检查Java环境是否可用
    
    Returns:
        bool: Java环境是否可用
    """
    try:
        import subprocess
        result = subprocess.run(
            ["java", "-version"],
            capture_output=True,
            text=True,
            check=False
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


def get_available_engines(config: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    """
    便捷函数：获取所有可用的反编译引擎
    
    Args:
        config: 配置字典
        
    Returns:
        Dict: 可用引擎信息字典
    """
    manager = DecompilerManager(config)
    return manager.get_available_engines()