#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CFR反编译引擎实现
使用CFR Java反编译器进行反编译操作
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List, Tuple
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
from java_decompiler.utils.filename_utils import parse_java_class_filename, get_java_file_name
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)


class CFRDecompiler(DecompilerEngine):
    """
    CFR反编译引擎实现类
    CFR是一款功能强大的Java反编译器，支持Java 8及以上版本
    """
    
    # CFR引擎元数据
    metadata = EngineMetadata(
        name="cfr",
        display_name="CFR",
        description="现代Java反编译器，专注于生成可编译的代码",
        jar_file="cfr-0.152.jar",
        main_class="org.benf.cfr.reader.Main",
        version="0.152",
        supports_class_files=True,
        supports_jar_files=True,
        supports_apk_files=False
    )
    
    # CFR支持的配置选项
    supported_options = [
        EngineOption(name="comments", description="是否显示注释", default_value=True, value_type=bool),
        EngineOption(name="decodeenumswitch", description="解码枚举开关", default_value=True, value_type=bool),
        EngineOption(name="decodelambdas", description="解码lambda表达式", default_value=True, value_type=bool),
        EngineOption(name="denull", description="优化null检查", default_value=True, value_type=bool),
        EngineOption(name="modernize", description="现代化语法", default_value=True, value_type=bool),
        EngineOption(name="removeboilerplate", description="移除样板代码", default_value=True, value_type=bool),
        EngineOption(name="showinferrable", description="显示可推断类型", default_value=False, value_type=bool),
        EngineOption(name="stringbuilder", description="使用StringBuilder", default_value=True, value_type=bool),
        EngineOption(name="tryresources", description="使用try-with-resources", default_value=True, value_type=bool),
        EngineOption(name="target", description="目标Java版本", default_value=None, value_type=str)
    ]
    """
    CFR反编译器实现
    CFR是一款功能强大的Java反编译器，支持Java 8及以上版本
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化CFR引擎
        
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
    
    def _build_decompile_args(self, input_path: str, output_dir: str, 
                             options: Dict[str, Any]) -> List[str]:
        """
        构建CFR命令行参数
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            options: 配置选项
            
        Returns:
            List[str]: 命令行参数列表
        """
        args = [input_path]
        
        # 添加输出目录参数
        args.extend(['--outputdir', output_dir])
        
        # 添加其他选项
        for key, value in options.items():
            # 跳过已处理的选项
            if key == 'outputdir':
                continue
                
            # 格式化为CFR参数格式
            arg_name = f"--{key}"
            
            # 对于布尔值选项
            if isinstance(value, bool):
                if value:
                    args.append(arg_name)
            elif value is not None:
                args.extend([arg_name, str(value)])
        
        return args
    
    def _get_output_file_path(self, input_path: str, output_dir: str) -> str:
        """
        获取输出文件路径
        
        Args:
            input_path: 输入文件路径
            output_dir: 输出目录
            
        Returns:
            str: 输出文件路径
        """
        # 使用filename_utils获取正确的Java文件名，支持匿名内部类
        base_name = os.path.basename(input_path)
        java_name = get_java_file_name(base_name)
        
        return os.path.join(output_dir, java_name)
    
    def decompile_file(self, input_path: str, output_dir: str, **kwargs) -> str:
        """
        使用CFR反编译单个文件
        
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
            raise InputFileError(f"CFR不支持的文件类型: {input_path}")
        
        # 准备输出目录
        output_dir = self.prepare_output_directory(output_dir)
        
        # 合并配置选项
        options = self._merge_options(kwargs)
        
        # 构建命令行参数
        args = self._build_decompile_args(input_path, output_dir, options)
        
        # 执行反编译
        exit_code, stdout, stderr = self.run_java_process(args, **kwargs)
        
        # 检查结果
        if exit_code != 0:
            raise DecompilationError(
                f"CFR反编译失败，退出码: {exit_code}, 错误信息: {stderr}")
        
        # 确定输出文件名
        output_file = self._get_output_file_path(input_path, output_dir)
        
        # 检查输出文件是否存在
        if not os.path.exists(output_file):
            # CFR可能将输出写入到stdout，尝试捕获
            if stdout.strip():
                try:
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(stdout)
                    logger.debug(f"从标准输出写入结果到 {output_file}")
                except Exception as e:
                    raise DecompilationError(f"无法写入反编译结果: {str(e)}")
            else:
                raise DecompilationError(f"反编译失败，未生成输出文件: {output_file}")
        
        logger.info(f"成功反编译文件: {input_path} -> {output_file}")
        return output_file
    
    def decompile_jar(self, jar_path: str, output_dir: str, **kwargs) -> str:
        """
        使用CFR反编译JAR文件
        
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
        
        # 构建命令行参数
        args = self._build_decompile_args(jar_path, output_dir, options)
        
        # 执行反编译
        exit_code, stdout, stderr = self.run_java_process(args, **kwargs)
        
        # 检查结果
        if exit_code != 0:
            raise DecompilationError(
                f"CFR反编译JAR失败，退出码: {exit_code}, 错误信息: {stderr}")
        
        # 检查输出目录是否有生成的文件
        java_files = find_files_with_extension(output_dir, '.java')
        if not java_files:
            # CFR可能需要特殊处理JAR文件
            logger.debug("尝试使用替代方法反编译JAR文件")
            return self._decompile_jar_alternative(jar_path, output_dir, options, kwargs)
        
        logger.info(f"成功反编译JAR文件: {jar_path} -> {output_dir}")
        return output_dir
    
    def _decompile_jar_alternative(self, jar_path: str, output_dir: str,
                                 options: Dict[str, Any], 
                                 process_kwargs: Dict[str, Any]) -> str:
        """
        替代方法：解压JAR文件然后逐个反编译class文件
        
        Args:
            jar_path: JAR文件路径
            output_dir: 输出目录
            options: 配置选项
            process_kwargs: 进程参数
            
        Returns:
            str: 反编译后的目录路径
        """
        # 创建临时目录解压JAR
        temp_dir = self.get_temp_directory()
        
        try:
            # 解压JAR文件
            extract_jar_file(jar_path, temp_dir)
            
            # 查找所有class文件
            class_files = find_files_with_extension(temp_dir, '.class')
            
            if not class_files:
                raise DecompilationError("JAR文件中未找到class文件")
            
            # 逐个反编译class文件
            success_count = 0
            for class_file in class_files:
                try:
                    # 计算相对路径，保持包结构
                    rel_path = os.path.relpath(class_file, temp_dir)
                    
                    # 构建输出子目录
                    output_subdir = os.path.join(
                        output_dir,
                        os.path.dirname(rel_path)
                    )
                    os.makedirs(output_subdir, exist_ok=True)
                    
                    # 反编译单个文件
                    self.decompile_file(class_file, output_subdir, **process_kwargs)
                    success_count += 1
                    
                except Exception as e:
                    logger.warning(f"反编译 {class_file} 失败: {str(e)}")
            
            if success_count == 0:
                raise DecompilationError("所有class文件反编译失败")
            
            logger.info(f"成功反编译 {success_count} 个文件 (共 {len(class_files)} 个)")
            return output_dir
            
        finally:
            # 清理临时文件
            self.cleanup_temp_files(temp_dir)
    
    def get_supported_options(self) -> List[EngineOption]:
        """
        获取CFR支持的配置选项
        
        Returns:
            List[EngineOption]: 支持的选项列表
        """
        return self.supported_options.copy()