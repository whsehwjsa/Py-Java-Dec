#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
反编译任务处理器
负责处理不同类型的反编译任务
"""

import os
import shutil
import tempfile
import time
from typing import Optional, List, Dict, Any, Callable, Union
from pathlib import Path

from java_decompiler.core.decompiler_manager import DecompilerManager, get_available_engines, check_java_environment
from java_decompiler.base import JavaDecompiler
from java_decompiler.engines.engine_base import DecompilerEngine
from java_decompiler.exceptions import (
    DecompilationError, 
    FileNotFoundError,
    InvalidInputError,
    EngineNotFoundError,
    ConfigurationError,
    OutputDirectoryError,
    JavaRuntimeError
)
from java_decompiler.utils.file_utils import (
    ensure_directory,
    is_class_file,
    is_jar_file,
    is_apk_file,
    get_files_by_extension
)
from java_decompiler.utils.path_utils import normalize_path
from java_decompiler.logger.logger import get_logger
from java_decompiler.performance.stats_collector import StatsCollector

logger = get_logger(__name__)


class DecompilationProcessor:
    """
    反编译任务处理器
    处理单个文件、目录和JAR文件的反编译任务
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化反编译处理器
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self.decompiler_manager = DecompilerManager(config)
        self.stats_collector = StatsCollector()
        
        # 处理器配置
        self.max_retries = self.config.get("max_retries", 1)
        self.retry_delay = self.config.get("retry_delay", 1.0)
    
    def decompile_file(self, 
                      input_path: str, 
                      output_path: str, 
                      engine_name: Optional[str] = None,
                      engine_config: Optional[Dict[str, Any]] = None,
                      callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        反编译单个文件
        
        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径
            engine_name: 指定的反编译引擎名称，如果为None则自动选择
            engine_config: 引擎特定配置
            callback: 进度回调函数，接收状态字典
            
        Returns:
            Dict: 反编译结果字典，包含成功状态、时间等信息
        """
        # 验证输入
        input_path = normalize_path(input_path)
        output_path = normalize_path(output_path)
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"输入文件不存在: {input_path}")
        
        if not (is_class_file(input_path) or is_jar_file(input_path) or is_apk_file(input_path)):
            raise InvalidInputError(f"不支持的文件类型: {input_path}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            ensure_directory(output_dir)
        
        # 选择引擎
        if not engine_name:
            try:
                engine_name = self.decompiler_manager.select_best_engine(input_path)
            except Exception as e:
                logger.warning(f"自动选择引擎失败: {str(e)}，尝试获取第一个可用引擎")
                # 尝试获取第一个可用引擎
                available_engines = get_available_engines(self.config)
                available_engine_names = [name for name, info in available_engines.items() if info.get("available", False)]
                if available_engine_names:
                    engine_name = available_engine_names[0]
                else:
                    raise EngineNotFoundError("没有可用的反编译引擎")
        
        logger.info(f"开始反编译文件: {input_path} -> {output_path} (引擎: {engine_name})")
        
        # 初始化结果字典
        result = {
            "input": input_path,
            "output": output_path,
            "engine": engine_name,
            "success": False,
            "duration": 0,
            "retries": 0,
            "error": None
        }
        
        # 调用回调
        if callback:
            callback({"status": "started", **result})
        
        start_time = time.time()
        
        # 尝试反编译，支持重试
        for attempt in range(self.max_retries):
            try:
                # 获取反编译引擎实例
                decompiler = self.decompiler_manager.get_decompiler(engine_name, engine_config)
                
                # 根据引擎类型调用不同的反编译方法
                if is_jar_file(input_path) or is_apk_file(input_path):
                    # 对于JAR/APK文件，输出路径应该是目录
                    if os.path.isfile(output_path):
                        output_path = os.path.dirname(output_path)
                    
                    # 确保输出目录存在
                    ensure_directory(output_path)
                    
                    # 调用反编译方法
                    if isinstance(decompiler, DecompilerEngine):
                        # 新接口
                        decompiler.decompile_jar(input_path, output_path, engine_config)
                    else:
                        # 旧接口
                        decompiler.decompile_jar(input_path, output_path)
                else:
                    # 对于单个类文件
                    if isinstance(decompiler, DecompilerEngine):
                        # 新接口
                        decompiler.decompile_file(input_path, output_path, engine_config)
                    else:
                        # 旧接口
                        decompiler.decompile_file(input_path, output_path)
                
                # 检查输出文件/目录是否存在
                if os.path.exists(output_path):
                    result["success"] = True
                    break
                else:
                    raise DecompilationError(f"反编译成功但输出文件不存在: {output_path}")
                    
            except Exception as e:
                result["error"] = str(e)
                result["retries"] = attempt + 1
                
                logger.warning(f"反编译失败 (尝试 {attempt + 1}/{self.max_retries}): {str(e)}")
                
                # 如果还有重试次数，等待后重试
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
        
        # 计算耗时
        result["duration"] = time.time() - start_time
        
        # 更新统计信息
        self.stats_collector.add_file_decompilation_stats(
            engine_name,
            result["success"],
            result["duration"],
            result["retries"]
        )
        
        # 记录结果
        if result["success"]:
            logger.info(f"文件反编译成功: {input_path} (耗时: {result['duration']:.2f}秒)")
        else:
            logger.error(f"文件反编译失败: {input_path} (错误: {result['error']})")
        
        # 调用回调
        if callback:
            callback({"status": "completed", **result})
        
        return result
    
    def decompile_directory(self, 
                           input_dir: str, 
                           output_dir: str,
                           engine_name: Optional[str] = None,
                           engine_config: Optional[Dict[str, Any]] = None,
                           recursive: bool = True,
                           exclude_patterns: Optional[List[str]] = None,
                           callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        反编译目录中的所有类文件
        
        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            engine_name: 指定的反编译引擎名称，如果为None则自动选择
            engine_config: 引擎特定配置
            recursive: 是否递归处理子目录
            exclude_patterns: 排除的文件模式列表
            callback: 进度回调函数，接收状态字典
            
        Returns:
            Dict: 反编译结果字典，包含成功、失败文件数量等信息
        """
        # 验证输入
        input_dir = normalize_path(input_dir)
        output_dir = normalize_path(output_dir)
        
        if not os.path.exists(input_dir):
            raise FileNotFoundError(f"输入目录不存在: {input_dir}")
        
        if not os.path.isdir(input_dir):
            raise InvalidInputError(f"输入路径不是目录: {input_dir}")
        
        # 确保输出目录存在
        ensure_directory(output_dir)
        
        # 获取所有类文件
        class_files = get_files_by_extension(input_dir, ".class", recursive)
        
        # 如果没有类文件，尝试查找JAR文件
        jar_files = get_files_by_extension(input_dir, ".jar", recursive)
        
        total_files = len(class_files) + len(jar_files)
        
        logger.info(f"发现 {len(class_files)} 个类文件和 {len(jar_files)} 个JAR文件待处理")
        
        # 初始化结果
        results = {
            "input": input_dir,
            "output": output_dir,
            "total_files": total_files,
            "success_count": 0,
            "failed_count": 0,
            "failed_files": [],
            "duration": 0,
            "details": []
        }
        
        # 调用回调
        if callback:
            callback({"status": "started", **results})
        
        start_time = time.time()
        processed_count = 0
        
        # 处理类文件
        for class_file in class_files:
            # 计算相对路径，保持目录结构
            rel_path = os.path.relpath(class_file, input_dir)
            output_file = os.path.join(output_dir, os.path.splitext(rel_path)[0] + ".java")
            
            # 确保输出目录存在
            ensure_directory(os.path.dirname(output_file))
            
            try:
                file_result = self.decompile_file(
                    class_file,
                    output_file,
                    engine_name,
                    engine_config,
                    callback
                )
                
                results["details"].append(file_result)
                
                if file_result["success"]:
                    results["success_count"] += 1
                else:
                    results["failed_count"] += 1
                    results["failed_files"].append({
                        "file": class_file,
                        "error": file_result["error"]
                    })
                    
            except Exception as e:
                results["failed_count"] += 1
                results["failed_files"].append({
                    "file": class_file,
                    "error": str(e)
                })
            
            processed_count += 1
            
            # 更新进度回调
            if callback:
                callback({
                    "status": "processing",
                    "processed": processed_count,
                    "total": total_files,
                    "progress": processed_count / total_files if total_files > 0 else 1.0,
                    **results
                })
        
        # 处理JAR文件
        for jar_file in jar_files:
            # 计算输出目录
            jar_name = os.path.splitext(os.path.basename(jar_file))[0]
            jar_output_dir = os.path.join(output_dir, jar_name)
            
            try:
                # 使用decompile_file处理JAR文件
                file_result = self.decompile_file(
                    jar_file,
                    jar_output_dir,
                    engine_name,
                    engine_config,
                    callback
                )
                
                results["details"].append(file_result)
                
                if file_result["success"]:
                    results["success_count"] += 1
                else:
                    results["failed_count"] += 1
                    results["failed_files"].append({
                        "file": jar_file,
                        "error": file_result["error"]
                    })
                    
            except Exception as e:
                results["failed_count"] += 1
                results["failed_files"].append({
                    "file": jar_file,
                    "error": str(e)
                })
            
            processed_count += 1
            
            # 更新进度回调
            if callback:
                callback({
                    "status": "processing",
                    "processed": processed_count,
                    "total": total_files,
                    "progress": processed_count / total_files if total_files > 0 else 1.0,
                    **results
                })
        
        # 计算耗时
        results["duration"] = time.time() - start_time
        
        # 记录结果
        logger.info(
            f"目录反编译完成: {input_dir} -> {output_dir} "
            f"(成功: {results['success_count']}, 失败: {results['failed_count']}, "
            f"耗时: {results['duration']:.2f}秒)"
        )
        
        # 调用回调
        if callback:
            callback({"status": "completed", **results})
        
        return results


def decompile_file(
    input_path: str, 
    output_path: str, 
    engine_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """
    便捷函数：反编译单个文件
    
    Args:
        input_path: 输入文件路径
        output_path: 输出文件路径
        engine_name: 指定的反编译引擎名称
        config: 配置字典
        callback: 回调函数
        
    Returns:
        Dict: 反编译结果字典
    """
    processor = DecompilationProcessor(config)
    return processor.decompile_file(input_path, output_path, engine_name, config, callback)


def decompile_directory(
    input_dir: str, 
    output_dir: str,
    engine_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    recursive: bool = True,
    exclude_patterns: Optional[List[str]] = None,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """
    便捷函数：反编译目录
    
    Args:
        input_dir: 输入目录路径
        output_dir: 输出目录路径
        engine_name: 指定的反编译引擎名称
        config: 配置字典
        recursive: 是否递归处理
        exclude_patterns: 排除模式
        callback: 回调函数
        
    Returns:
        Dict: 反编译结果字典
    """
    processor = DecompilationProcessor(config)
    return processor.decompile_directory(
        input_dir, output_dir, engine_name, config, recursive, exclude_patterns, callback
    )


def decompile_jar(
    jar_path: str, 
    output_dir: str,
    engine_name: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
    """
    便捷函数：反编译JAR文件
    
    Args:
        jar_path: JAR文件路径
        output_dir: 输出目录路径
        engine_name: 指定的反编译引擎名称
        config: 配置字典
        callback: 回调函数
        
    Returns:
        Dict: 反编译结果字典
    """
    # 首先检查Java环境
    if not check_java_environment():
        raise JavaRuntimeError("未检测到Java环境，请安装JRE或JDK")
    
    processor = DecompilationProcessor(config)
    return processor.decompile_file(jar_path, output_dir, engine_name, config, callback)