#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FernFlower反编译引擎实现
使用FernFlower Java反编译器进行反编译操作
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List
from pathlib import Path

from java_decompiler.engines.engine_base import (
    DecompilerEngine, EngineMetadata, EngineOption
)
from java_decompiler.exceptions import (
    DecompilationError, InputFileError, OutputDirError
)
from java_decompiler.utils.file_utils import (
    extract_jar_file, is_java_class_file, is_jar_file, find_files_with_extension
)
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)


class FernFlowerDecompiler(DecompilerEngine):
    """
    FernFlower反编译引擎实现类
    FernFlower是IntelliJ IDEA内置的Java反编译器，性能优秀
    """
    
    # FernFlower引擎元数据
    metadata = EngineMetadata(
        name="fernflower",
        display_name="FernFlower",
        description="IntelliJ IDEA内置的Java反编译器，生成高质量代码",
        jar_file="fernflower.jar",
        main_class="org.jetbrains.java.decompiler.main.decompiler.ConsoleDecompiler",
        version="1.0.0",
        supports_class_files=True,
        supports_jar_files=True,
        supports_apk_files=False
    )
    
    # FernFlower支持的配置选项
    supported_options = [
        EngineOption(name="dgs", description="反编译泛型签名", default_value=True, value_type=bool),
        EngineOption(name="hdc", description="隐藏桥接方法", default_value=False, value_type=bool),
        EngineOption(name="hes", description="隐藏合成类成员", default_value=False, value_type=bool),
        EngineOption(name="ind", description="缩进空格数", default_value=4, value_type=int),
        EngineOption(name="mpm", description="最大化性能", default_value=False, value_type=bool),
        EngineOption(name="ren", description="重命名标识符策略", default_value="0", value_type=str),
        EngineOption(name="urc", description="使用原始类文件", default_value=True, value_type=bool),
        EngineOption(name="nns", description="允许不为非静态内部类生成构造函数", default_value=True, value_type=bool),
        EngineOption(name="pll", description="反编译带实现的方法", default_value=True, value_type=bool),
        EngineOption(name="log", description="写入日志文件", default_value=False, value_type=bool)
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化FernFlower引擎
        
        Args:
            config: 引擎配置
        """
        super().__init__(config)
        # 获取引擎特定配置
        self.engine_config = config or {}
    
    def _merge_options(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        合并配置选项
        
        Args:
            kwargs: 额外选项
            
        Returns:
            Dict[str, Any]: 合并后的选项
        """
        # 从引擎配置获取默认选项
        options = self.engine_config.copy()
        
        # 合并kwargs中的选项
        for key, value in kwargs.items():
            if key not in ['max_memory', 'timeout']:
                options[key] = value
        
        # 验证并规范化选项
        return self.validate_options(options)
    
    def _build_options_string(self, options: Dict[str, Any]) -> str:
        """
        构建FernFlower选项字符串
        
        Args:
            options: 配置选项
            
        Returns:
            str: 选项字符串
        """
        option_list = []
        for key, value in options.items():
            # 转换值为适当的字符串格式
            if isinstance(value, bool):
                value_str = '1' if value else '0'
            else:
                value_str = str(value)
            option_list.append(f"{key}={value_str}")
        return ",".join(option_list)
    
    def decompile_file(self, input_path: str, output_dir: str, **kwargs) -> str:
        """
        使用FernFlower反编译单个文件
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            **kwargs: 额外选项
            
        Returns:
            str: 反编译后的文件路径
            
        Raises:
            DecompilationError: 反编译失败时抛出
            InputFileError: 输入文件无效时抛出
            OutputDirError: 输出目录无效时抛出
        """
        # 验证输入文件
        if not self.validate_input(input_path):
            raise InputFileError(f"FernFlower不支持的文件类型: {input_path}")
        
        # 准备输出目录
        output_dir = self.prepare_output_directory(output_dir)
        
        # 合并配置选项
        options = self._merge_options(kwargs)
        options_string = self._build_options_string(options)
        
        # 获取最终输出文件路径
        input_filename = os.path.basename(input_path)
        class_name = os.path.splitext(input_filename)[0]
        output_file = os.path.join(output_dir, f"{class_name}.java")
        
        try:
            # FernFlower需要输出到目录，然后移动文件
            temp_output_dir = self.get_temp_directory()
            
            # 构建命令行参数
            args = [
                f"-{options_string}",
                input_path,
                temp_output_dir
            ]
            
            # 执行反编译
            exit_code, stdout, stderr = self.run_java_process(args, **kwargs)
            
            # 检查结果
            if exit_code != 0:
                raise DecompilationError(
                    f"FernFlower反编译失败，退出码: {exit_code}, 错误信息: {stderr}")
            
            # 获取反编译后的文件
            temp_java_file = os.path.join(temp_output_dir, f"{class_name}.java")
            
            # 检查文件是否生成
            if os.path.exists(temp_java_file):
                shutil.copy2(temp_java_file, output_file)
            else:
                # 搜索输出目录中的java文件
                java_files = list(Path(temp_output_dir).glob("*.java"))
                if java_files:
                    shutil.copy2(java_files[0], output_file)
                else:
                    raise DecompilationError("未生成反编译后的Java文件")
            
            logger.info(f"成功反编译文件: {input_path} -> {output_file}")
            return output_file
            
        finally:
            # 清理临时目录
            self.cleanup_temp_files(temp_output_dir)
    
    def decompile_jar(self, jar_path: str, output_dir: str, **kwargs) -> str:
        """
        使用FernFlower反编译JAR文件
        
        Args:
            jar_path: JAR文件路径
            output_dir: 输出目录
            **kwargs: 额外选项
            
        Returns:
            str: 反编译后的目录路径
            
        Raises:
            DecompilationError: 反编译失败时抛出
            InputFileError: 输入文件无效时抛出
            OutputDirError: 输出目录无效时抛出
        """
        # 验证输入文件
        if not is_jar_file(jar_path):
            raise InputFileError(f"不是有效的JAR文件: {jar_path}")
        
        # 准备输出目录
        output_dir = self.prepare_output_directory(output_dir)
        
        # 合并配置选项
        options = self._merge_options(kwargs)
        options_string = self._build_options_string(options)
        
        try:
            # 构建命令行参数
            args = [
                f"-{options_string}",
                jar_path,
                output_dir
            ]
            
            # 执行反编译
            exit_code, stdout, stderr = self.run_java_process(args, **kwargs)
            
            # 检查结果
            if exit_code != 0:
                raise DecompilationError(
                    f"FernFlower反编译JAR失败，退出码: {exit_code}, 错误信息: {stderr}")
            
            # FernFlower会在输出目录生成一个.jar文件，需要解压
            output_jar = os.path.join(output_dir, f"{os.path.splitext(os.path.basename(jar_path))[0]}.jar")
            if os.path.exists(output_jar):
                # 创建临时目录解压
                temp_dir = self.get_temp_directory()
                try:
                    extract_jar_file(output_jar, temp_dir)
                    
                    # 复制解压后的文件到输出目录
                    java_files = find_files_with_extension(temp_dir, '.java')
                    for java_file in java_files:
                        rel_path = os.path.relpath(java_file, temp_dir)
                        dst = os.path.join(output_dir, rel_path)
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(java_file, dst)
                    
                    # 清理临时JAR文件
                    os.remove(output_jar)
                    
                    logger.info(f"成功解压反编译后的JAR到: {output_dir}")
                    
                finally:
                    # 清理临时目录
                    self.cleanup_temp_files(temp_dir)
            
            # 检查输出目录是否有Java文件
            java_files = find_files_with_extension(output_dir, '.java')
            if not java_files:
                raise DecompilationError("反编译完成但未找到生成的Java文件")
            
            logger.info(f"成功反编译JAR文件: {jar_path} -> {output_dir} (共 {len(java_files)} 个Java文件)")
            return output_dir
            
        except Exception as e:
            if isinstance(e, DecompilationError):
                raise
            raise DecompilationError(f"反编译JAR文件时出错: {str(e)}")
    
    def get_supported_options(self) -> List[EngineOption]:
        """
        获取FernFlower支持的配置选项
        
        Returns:
            List[EngineOption]: 支持的选项列表
        """
        return self.supported_options.copy()