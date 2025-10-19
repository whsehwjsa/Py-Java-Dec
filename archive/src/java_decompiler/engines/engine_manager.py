#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译引擎管理模块
管理所有可用的反编译引擎，提供注册、获取和列出引擎的功能
"""

from typing import Dict, List, Optional, Type
import inspect
import os

from java_decompiler.engines.engine_base import DecompilerEngine
from java_decompiler.exceptions import EngineNotFoundError
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)

# 存储所有已注册的引擎类
_engines_registry: Dict[str, Type[DecompilerEngine]] = {}

# 默认引擎名称
_default_engine_name: Optional[str] = None


def register_engine(engine_class: Type[DecompilerEngine]) -> None:
    """
    注册一个反编译引擎
    
    Args:
        engine_class: 反编译引擎类
        
    Raises:
        TypeError: 当提供的不是DecompilerEngine的子类时抛出
        ValueError: 当引擎元数据不正确时抛出
    """
    # 验证引擎类
    if not inspect.isclass(engine_class) or not issubclass(engine_class, DecompilerEngine):
        raise TypeError("引擎类必须是DecompilerEngine的子类")
    
    # 验证元数据
    if not hasattr(engine_class, 'metadata') or engine_class.metadata is None:
        raise ValueError("引擎类必须定义metadata属性")
    
    engine_name = engine_class.metadata.name
    if not engine_name:
        raise ValueError("引擎元数据必须指定name属性")
    
    # 注册引擎
    _engines_registry[engine_name] = engine_class
    logger.debug(f"已注册引擎: {engine_name} ({engine_class.metadata.display_name})")
    
    # 如果还没有默认引擎，则设置第一个注册的引擎为默认引擎
    global _default_engine_name
    if _default_engine_name is None:
        _default_engine_name = engine_name
        logger.debug(f"设置默认引擎: {engine_name}")


def unregister_engine(engine_name: str) -> None:
    """
    注销一个反编译引擎
    
    Args:
        engine_name: 引擎名称
        
    Raises:
        EngineNotFoundError: 当引擎不存在时抛出
    """
    if engine_name not in _engines_registry:
        raise EngineNotFoundError(f"未找到引擎: {engine_name}")
    
    del _engines_registry[engine_name]
    logger.debug(f"已注销引擎: {engine_name}")
    
    # 如果注销的是默认引擎，则重置默认引擎
    global _default_engine_name
    if _default_engine_name == engine_name:
        _default_engine_name = next(iter(_engines_registry.keys()), None)
        if _default_engine_name:
            logger.debug(f"重置默认引擎为: {_default_engine_name}")
        else:
            logger.debug("没有可用的引擎，默认引擎已重置为None")


def get_available_engines() -> Dict[str, Type[DecompilerEngine]]:
    """
    获取所有可用的引擎
    
    Returns:
        Dict[str, Type[DecompilerEngine]]: 引擎名称到引擎类的映射
    """
    return _engines_registry.copy()


def get_engine_by_name(engine_name: str) -> Type[DecompilerEngine]:
    """
    根据名称获取引擎类
    
    Args:
        engine_name: 引擎名称
        
    Returns:
        Type[DecompilerEngine]: 引擎类
        
    Raises:
        EngineNotFoundError: 当引擎不存在时抛出
    """
    if engine_name not in _engines_registry:
        raise EngineNotFoundError(f"未找到引擎: {engine_name}")
    
    return _engines_registry[engine_name]


def list_engine_names() -> List[str]:
    """
    列出所有可用引擎的名称
    
    Returns:
        List[str]: 引擎名称列表
    """
    return list(_engines_registry.keys())


def get_default_engine_name() -> Optional[str]:
    """
    获取默认引擎名称
    
    Returns:
        Optional[str]: 默认引擎名称，如果没有则返回None
    """
    return _default_engine_name


def set_default_engine(engine_name: str) -> None:
    """
    设置默认引擎
    
    Args:
        engine_name: 引擎名称
        
    Raises:
        EngineNotFoundError: 当引擎不存在时抛出
    """
    if engine_name not in _engines_registry:
        raise EngineNotFoundError(f"未找到引擎: {engine_name}")
    
    global _default_engine_name
    _default_engine_name = engine_name
    logger.debug(f"设置默认引擎为: {engine_name}")


def is_engine_available(engine_name: str) -> bool:
    """
    检查引擎是否可用
    
    Args:
        engine_name: 引擎名称
        
    Returns:
        bool: 是否可用
    """
    return engine_name in _engines_registry


def initialize_engines() -> None:
    """
    初始化所有内置引擎
    自动注册CFR、FernFlower和JADX引擎
    """
    try:
        # 注册CFR引擎
        from java_decompiler.engines.cfr import CFRDecompiler
        register_engine(CFRDecompiler)
    except ImportError:
        logger.warning("无法导入CFR引擎")
    except Exception as e:
        logger.warning(f"注册CFR引擎时出错: {str(e)}")
    
    try:
        # 注册FernFlower引擎
        from java_decompiler.engines.fernflower import FernFlowerDecompiler
        register_engine(FernFlowerDecompiler)
    except ImportError:
        logger.warning("无法导入FernFlower引擎")
    except Exception as e:
        logger.warning(f"注册FernFlower引擎时出错: {str(e)}")
    
    try:
        # 注册JADX引擎
        from java_decompiler.engines.jadx import JADXDecompiler
        register_engine(JADXDecompiler)
    except ImportError:
        logger.warning("无法导入JADX引擎")
    except Exception as e:
        logger.warning(f"注册JADX引擎时出错: {str(e)}")


def get_engine_instance(engine_name: Optional[str] = None, 
                       config: Optional[Dict] = None) -> DecompilerEngine:
    """
    获取引擎实例
    
    Args:
        engine_name: 引擎名称，如果为None则使用默认引擎
        config: 引擎配置，支持新的配置结构（引擎路径在engines.paths下）
        
    Returns:
        DecompilerEngine: 引擎实例
        
    Raises:
        EngineNotFoundError: 当引擎不存在或没有可用引擎时抛出
    """
    # 如果未指定引擎名称，则使用默认引擎
    if engine_name is None:
        engine_name = get_default_engine_name()
        if engine_name is None:
            raise EngineNotFoundError("没有可用的引擎")
    
    # 处理新的配置结构
    engine_config = config.copy() if config else {}
    
    # 如果config中包含engines.paths，提取当前引擎的路径配置
    if 'engines' in engine_config and 'paths' in engine_config['engines']:
        engine_path = engine_config['engines']['paths'].get(engine_name)
        if engine_path:
            # 将路径配置直接添加到引擎配置中
            engine_config['path'] = engine_path
    
    # 如果config中包含engines.{engine_name}，提取引擎特定配置
    if 'engines' in engine_config and engine_name in engine_config['engines']:
        engine_specific_config = engine_config['engines'][engine_name].copy()
        # 移除paths键（如果存在），避免冲突
        engine_specific_config.pop('paths', None)
        # 更新引擎配置
        engine_config.update(engine_specific_config)
    
    # 移除engines键，因为我们已经提取了所需的配置
    engine_config.pop('engines', None)
    
    engine_class = get_engine_by_name(engine_name)
    return engine_class(engine_config)


def filter_engines_by_file_type(file_type: str) -> List[str]:
    """
    根据文件类型过滤引擎
    
    Args:
        file_type: 文件类型，如'.class', '.jar', '.apk'
        
    Returns:
        List[str]: 支持该文件类型的引擎名称列表
    """
    supported_engines = []
    
    for name, engine_class in _engines_registry.items():
        metadata = engine_class.metadata
        
        if file_type == '.class' and metadata.supports_class_files:
            supported_engines.append(name)
        elif file_type == '.jar' and metadata.supports_jar_files:
            supported_engines.append(name)
        elif file_type == '.apk' and metadata.supports_apk_files:
            supported_engines.append(name)
    
    return supported_engines


def get_engine_metadata_dict() -> Dict[str, Dict]:
    """
    获取所有引擎的元数据字典
    
    Returns:
        Dict[str, Dict]: 引擎名称到元数据字典的映射
    """
    metadata_dict = {}
    
    for name, engine_class in _engines_registry.items():
        metadata = engine_class.metadata
        metadata_dict[name] = {
            'name': metadata.name,
            'display_name': metadata.display_name,
            'description': metadata.description,
            'version': metadata.version,
            'jar_file': metadata.jar_file,
            'main_class': metadata.main_class,
            'supported_file_types': [
                '.class' if metadata.supports_class_files else None,
                '.jar' if metadata.supports_jar_files else None,
                '.apk' if metadata.supports_apk_files else None
            ]
        }
        # 过滤掉None值
        metadata_dict[name]['supported_file_types'] = [
            ft for ft in metadata_dict[name]['supported_file_types'] if ft
        ]
    
    return metadata_dict