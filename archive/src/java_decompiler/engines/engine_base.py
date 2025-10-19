#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译引擎基类模块
定义所有反编译引擎必须实现的接口和基础功能
"""

import abc
import subprocess
import os
import shutil
import tempfile
from typing import Dict, List, Optional, Any, Tuple, Union

from java_decompiler.exceptions import (
    EngineNotAvailableError,
    DecompilationError,
    InvalidInputError,
    OutputDirectoryError
)
from java_decompiler.utils.file_utils import (
    is_java_class_file,
    is_jar_file,
    is_apk_file,
    create_directory
)
from java_decompiler.config.config_manager import get_default_config
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)


class EngineOption:
    """
    引擎配置选项类，用于定义引擎支持的配置选项
    """
    def __init__(self,
                 name: str,
                 description: str,
                 default_value: Any,
                 value_type: type = str,
                 required: bool = False,
                 choices: Optional[List[Any]] = None):
        """
        初始化引擎选项
        
        Args:
            name: 选项名称
            description: 选项描述
            default_value: 默认值
            value_type: 值类型
            required: 是否必填
            choices: 可选值列表（如果有）
        """
        self.name = name
        self.description = description
        self.default_value = default_value
        self.value_type = value_type
        self.required = required
        self.choices = choices
    
    def validate(self, value: Any) -> bool:
        """
        验证选项值是否有效
        
        Args:
            value: 要验证的值
            
        Returns:
            bool: 是否有效
        """
        # 检查类型
        if not isinstance(value, self.value_type):
            try:
                value = self.value_type(value)
            except (ValueError, TypeError):
                return False
        
        # 检查可选值
        if self.choices is not None and value not in self.choices:
            return False
        
        return True


class EngineMetadata:
    """
    引擎元数据类，存储引擎的基本信息
    """
    def __init__(self,
                 name: str,
                 display_name: str,
                 description: str,
                 jar_file: str,
                 main_class: str,
                 version: str = "unknown",
                 supports_class_files: bool = True,
                 supports_jar_files: bool = True,
                 supports_apk_files: bool = False):
        """
        初始化引擎元数据
        
        Args:
            name: 引擎唯一名称（英文）
            display_name: 显示名称
            description: 引擎描述
            jar_file: JAR文件路径
            main_class: 主类名
            version: 版本号
            supports_class_files: 是否支持反编译class文件
            supports_jar_files: 是否支持反编译jar文件
            supports_apk_files: 是否支持反编译apk文件
        """
        self.name = name
        self.display_name = display_name
        self.description = description
        self.jar_file = jar_file
        self.main_class = main_class
        self.version = version
        self.supports_class_files = supports_class_files
        self.supports_jar_files = supports_jar_files
        self.supports_apk_files = supports_apk_files


class DecompilerEngine(metaclass=abc.ABCMeta):
    """
    反编译引擎基类，定义所有引擎必须实现的接口
    """
    
    # 引擎元数据
    metadata: EngineMetadata = None
    
    # 支持的选项列表
    supported_options: List[EngineOption] = []
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化引擎
        
        Args:
            config: 引擎配置选项
        """
        self.config = config or get_default_config().get('engines', {}).get('default', {})
        # 验证引擎可执行文件是否存在
        # 注意：这个方法在子类中需要根据具体引擎类型实现
        pass
    
    def _validate_executable(self) -> None:
        """
        验证引擎可执行文件是否存在
        基类实现，子类应该根据具体引擎类型重写
        
        Raises:
            FileNotFoundError: 可执行文件不存在
            EngineNotAvailableError: 引擎不可用
        """
        # 基类实现为空，子类必须重写此方法
        # 以验证特定类型引擎的可执行文件
        pass
    
    def _get_jar_path(self) -> str:
        """
        获取JAR文件的完整路径
        
        Returns:
            str: JAR文件路径
        """
        if self.metadata:
            jar_path = self.metadata.jar_file
            
            # 如果是相对路径，尝试从配置的引擎目录查找
            if not os.path.isabs(jar_path):
                config = get_default_config()
                engines_dir = config.get('engines', {}).get('directory', '')
                if engines_dir:
                    jar_path = os.path.join(engines_dir, jar_path)
            
            return jar_path
        return ''
    
    def validate_input(self, input_path: str) -> bool:
        """
        验证输入文件是否支持
        
        Args:
            input_path: 输入文件路径
            
        Returns:
            bool: 是否支持
            
        Raises:
            InputFileError: 当文件不存在时抛出
        """
        if not os.path.exists(input_path):
            raise InputFileError(f"输入文件不存在: {input_path}")
        
        if not self.metadata:
            return False
        
        if os.path.isdir(input_path):
            # 目录通常包含class文件，所以只要支持class文件就允许
            return self.metadata.supports_class_files
        
        if is_java_class_file(input_path):
            return self.metadata.supports_class_files
        elif is_jar_file(input_path):
            return self.metadata.supports_jar_files
        elif is_apk_file(input_path):
            return self.metadata.supports_apk_files
        
        return False
    
    def validate_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证并规范化选项
        
        Args:
            options: 输入选项
            
        Returns:
            Dict[str, Any]: 验证后的选项
        """
        validated_options = {}
        
        # 创建选项名称到选项对象的映射
        option_map = {opt.name: opt for opt in self.supported_options}
        
        # 处理输入选项
        for key, value in options.items():
            if key in option_map:
                option = option_map[key]
                if option.validate(value):
                    # 转换为正确的类型
                    validated_options[key] = option.value_type(value)
                else:
                    logger.warning(
                        f"选项 {key} 的值 {value} 无效，使用默认值 {option.default_value}")
                    validated_options[key] = option.default_value
            else:
                logger.warning(f"未知选项: {key}")
        
        # 添加未提供的必填选项的默认值
        for option in self.supported_options:
            if option.name not in validated_options:
                validated_options[option.name] = option.default_value
        
        return validated_options
    
    @abc.abstractmethod
    def decompile_file(self, input_path: str, output_dir: str, **kwargs) -> str:
        """
        反编译单个文件
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            **kwargs: 额外选项
            
        Returns:
            str: 反编译后的文件路径
            
        Raises:
            DecompilationError: 反编译失败时抛出
            InvalidInputError: 输入无效时抛出
            OutputDirectoryError: 输出目录问题时抛出
        """
        pass
    
    @abc.abstractmethod
    def decompile_jar(self, jar_path: str, output_dir: str, **kwargs) -> str:
        """
        反编译JAR文件
        
        Args:
            jar_path: JAR文件路径
            output_dir: 输出目录
            **kwargs: 额外选项
            
        Returns:
            str: 反编译后的目录路径
            
        Raises:
            DecompilationError: 反编译失败时抛出
        """
        pass
    
    def run_java_process(self, args: List[str], **kwargs) -> Tuple[int, str, str]:
        """
        运行Java进程
        
        Args:
            args: 命令行参数列表
            **kwargs: 额外的subprocess参数
            
        Returns:
            Tuple[int, str, str]: (退出码, 标准输出, 标准错误)
        """
        jar_path = self._get_jar_path()
        
        # 构建完整的命令
        cmd = [
            'java',
            f'-Xmx{kwargs.get("max_memory", "512m")}',
            '-cp', jar_path,
            self.metadata.main_class
        ] + args
        
        logger.debug(f"运行命令: {' '.join(cmd)}")
        
        try:
            # 执行命令
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                **kwargs
            )
            
            stdout, stderr = process.communicate(timeout=kwargs.get('timeout', 300))
            
            return process.returncode, stdout, stderr
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise DecompilationError(f"反编译超时")
        except Exception as e:
            raise DecompilationError(f"执行Java进程时出错: {str(e)}")
    
    def prepare_output_directory(self, output_dir: str, force: bool = False) -> str:
        """
        准备输出目录
        
        Args:
            output_dir: 输出目录路径
            force: 是否强制覆盖已存在的目录
            
        Returns:
            str: 规范化后的输出目录路径
            
        Raises:
            OutputDirError: 当目录无法创建或访问时抛出
        """
        output_dir = os.path.abspath(output_dir)
        
        try:
            if os.path.exists(output_dir):
                if force:
                    if os.path.isfile(output_dir):
                        os.remove(output_dir)
                    else:
                        shutil.rmtree(output_dir)
                elif not os.path.isdir(output_dir):
                    raise OutputDirError(f"输出路径已存在但不是目录: {output_dir}")
            
            create_directory(output_dir)
            return output_dir
            
        except Exception as e:
            raise OutputDirError(f"无法创建输出目录: {str(e)}")
    
    def get_temp_directory(self) -> str:
        """
        获取临时目录
        
        Returns:
            str: 临时目录路径
        """
        return tempfile.mkdtemp(prefix=f"decompiler_{self.metadata.name}_")
    
    def cleanup_temp_files(self, temp_dir: str) -> None:
        """
        清理临时文件
        
        Args:
            temp_dir: 临时目录路径
        """
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"清理临时目录: {temp_dir}")
            except Exception as e:
                logger.warning(f"无法清理临时目录 {temp_dir}: {str(e)}")
    
    def format_options(self, options: Dict[str, Any]) -> str:
        """
        格式化选项为命令行参数格式
        
        Args:
            options: 选项字典
            
        Returns:
            str: 格式化后的选项字符串
        """
        return ','.join([f"{k}={v}" for k, v in options.items()])
    
    def get_supported_file_types(self) -> List[str]:
        """
        获取支持的文件类型
        
        Returns:
            List[str]: 文件类型列表
        """
        if not self.metadata:
            return []
            
        file_types = []
        if self.metadata.supports_class_files:
            file_types.append('.class')
        if self.metadata.supports_jar_files:
            file_types.append('.jar')
        if self.metadata.supports_apk_files:
            file_types.append('.apk')
        return file_types