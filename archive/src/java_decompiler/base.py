#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译器基类接口
定义所有反编译器引擎必须实现的接口
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class JavaDecompiler(ABC):
    """
    反编译器基类，所有具体反编译器引擎的抽象基类
    
    提供统一的反编译接口，各引擎实现类需继承此类并实现所有抽象方法
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化反编译器
        
        Args:
            config: 反编译器配置字典，包含引擎特定配置项
        """
        self.config = config or {}
        self.engine_name = "base"
        self.engine_version = "unknown"
    
    @abstractmethod
    def check_availability(self) -> bool:
        """
        检查反编译引擎是否可用
        
        Returns:
            bool: 引擎是否可用
        """
        pass
    
    @abstractmethod
    def decompile_file(self, input_path: str, output_path: str) -> bool:
        """
        反编译单个文件
        
        Args:
            input_path: 输入文件路径（.class文件）
            output_path: 输出文件路径（.java文件）
            
        Returns:
            bool: 反编译是否成功
            
        Raises:
            DecompilationError: 反编译过程中出现错误
        """
        pass
    
    @abstractmethod
    def decompile_jar(self, jar_path: str, output_dir: str, exclude_patterns: Optional[list] = None) -> bool:
        """
        反编译JAR文件
        
        Args:
            jar_path: JAR文件路径
            output_dir: 输出目录
            exclude_patterns: 排除的文件模式列表
            
        Returns:
            bool: 反编译是否成功
        """
        pass
    
    @abstractmethod
    def get_supported_options(self) -> Dict[str, Any]:
        """
        获取引擎支持的配置选项
        
        Returns:
            Dict: 支持的选项字典，键为选项名，值为默认值
        """
        pass
    
    def set_option(self, option: str, value: Any) -> None:
        """
        设置反编译器选项
        
        Args:
            option: 选项名
            value: 选项值
        """
        self.config[option] = value
    
    def get_option(self, option: str, default: Any = None) -> Any:
        """
        获取反编译器选项
        
        Args:
            option: 选项名
            default: 默认值
            
        Returns:
            Any: 选项值或默认值
        """
        return self.config.get(option, default)
    
    def get_info(self) -> Dict[str, str]:
        """
        获取反编译器信息
        
        Returns:
            Dict: 包含引擎名称、版本等信息的字典
        """
        return {
            "name": self.engine_name,
            "version": self.engine_version,
            "type": "Java Decompiler"
        }
    
    def validate_input(self, input_path: str) -> bool:
        """
        验证输入文件是否有效
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            bool: 输入是否有效
        """
        import os
        return os.path.exists(input_path) and os.path.isfile(input_path)