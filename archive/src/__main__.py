#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java 反编译工具主程序入口
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

from cli.argument_parser import parse_arguments
from exceptions import (
    JavaEnvironmentError,
    ToolNotFoundError,
    DecompilationError,
    InvalidInputError,
    OutputDirectoryError
)
from diagnostics.diagnostic_tool import DiagnosticTool
from file_utils.file_handler import (
    ensure_directory,
    is_valid_file,
    is_class_file,
    is_jar_file,
    collect_files_by_extension,
    normalize_path
)
from logger.logger import setup_logger, get_logger
from task_manager.task_runner import TaskRunner
from task_manager.thread_pool import ThreadPool
from performance.stats_collector import StatsCollector
from performance.profiler import timing

# 导入反编译工具相关模块
from utils import get_decompiler, check_java_environment

__version__ = "1.0.0"
logger = get_logger(__name__)

def print_version() -> None:
    """
    打印版本信息
    """
    print(f"Java 反编译工具 v{__version__}")
    print("支持 CFR、FernFlower 和 JADX 多种反编译引擎")
    print("\n使用方法: java-decompiler [options] <input>...")
    print("运行 'java-decompiler --help' 获取更多信息")

def validate_input(input_paths: List[str]) -> List[str]:
    """
    验证输入路径
    
    Args:
        input_paths: 输入路径列表
        
    Returns:
        List[str]: 规范化的有效输入路径列表
        
    Raises:
        InvalidInputError: 当输入路径无效时
    """
    valid_paths = []
    
    for path in input_paths:
        norm_path = normalize_path(path)
        
        if not os.path.exists(norm_path):
            raise InvalidInputError(norm_path, f"路径不存在: {norm_path}")
        
        valid_paths.append(norm_path)
    
    return valid_paths

def collect_input_files(input_paths: List[str], recursive: bool = False) -> List[str]:
    """
    收集要处理的输入文件
    
    Args:
        input_paths: 输入路径列表
        recursive: 是否递归搜索子目录
        
    Returns:
        List[str]: 要处理的文件列表
    """
    files_to_process = []
    supported_extensions = {'.class', '.jar', '.war', '.ear', '.zip'}
    
    for path in input_paths:
        if os.path.isfile(path):
            # 单个文件
            files_to_process.append(path)
        elif os.path.isdir(path):
            # 目录，收集支持的文件
            collected = list(collect_files_by_extension(
                path, 
                supported_extensions,
                recursive=recursive
            ))
            files_to_process.extend(collected)
    
    return files_to_process

@timing("process_file")
def process_single_file(
    input_file: str,
    output_dir: str,
    engine: str = "auto",
    threads: int = 1,
    timeout: int = 300,
    **kwargs
) -> Optional[str]:
    """
    处理单个文件
    
    Args:
        input_file: 输入文件路径
        output_dir: 输出目录
        engine: 反编译引擎
        threads: 线程数
        timeout: 超时时间
        **kwargs: 其他参数
        
    Returns:
        Optional[str]: 输出文件路径，如果失败则返回None
        
    Raises:
        Exception: 处理过程中的异常
    """
    # 获取反编译工具实例
    decompiler = get_decompiler(
        engine=engine,
        threads=threads,
        timeout=timeout,
        **kwargs
    )
    
    # 执行反编译
    output_file = decompiler.decompile(input_file, output_dir)
    
    return output_file

def batch_process_files(
    files: List[str],
    output_dir: str,
    engine: str = "auto",
    threads: int = 4,
    timeout: int = 300,
    **kwargs
) -> StatsCollector:
    """
    批量处理文件
    
    Args:
        files: 文件列表
        output_dir: 输出目录
        engine: 反编译引擎
        threads: 线程数
        timeout: 超时时间
        **kwargs: 其他参数
        
    Returns:
        StatsCollector: 统计收集器，包含处理结果统计
    """
    # 初始化统计收集器
    stats = StatsCollector()
    
    # 如果只有少量文件，使用简单的线程池
    if len(files) <= threads:
        # 直接使用线程池
        with ThreadPool(max_workers=threads) as pool:
            # 定义处理函数
            def process_with_stats(file_path):
                try:
                    result = process_single_file(
                        file_path, output_dir, engine, 1, timeout, **kwargs
                    )
                    if result:
                        stats.record_success(file_path)
                        logger.info(f"成功反编译: {file_path}")
                    else:
                        stats.record_failure(file_path, "反编译返回空结果")
                        logger.error(f"反编译失败: {file_path}")
                except Exception as e:
                    stats.record_failure(file_path, str(e))
                    logger.error(f"处理文件 {file_path} 时出错: {e}")
            
            # 提交所有任务
            futures = [
                pool.submit(process_with_stats, file_path) 
                for file_path in files
            ]
            
            # 等待所有任务完成
            for future in futures:
                try:
                    future.result()
                except Exception:
                    pass
    else:
        # 使用任务运行器进行更复杂的管理
        runner = TaskRunner(max_workers=threads, timeout=timeout)
        
        # 添加所有任务
        for file_path in files:
            runner.add_task(
                process_single_file,
                file_path,
                output_dir,
                engine=engine,
                threads=1,  # 每个任务使用1个线程
                timeout=timeout,
                **kwargs
            )
        
        # 运行所有任务
        results = runner.run_all()
        
        # 收集结果
        for result in results:
            if result.status == "completed":
                stats.record_success(result.input_file)
                logger.info(f"成功反编译: {result.input_file}")
            else:
                error_msg = result.error or "未知错误"
                stats.record_failure(result.input_file, error_msg)
                logger.error(f"反编译失败 {result.input_file}: {error_msg}")
    
    return stats

def run_tests(args) -> bool:
    """
    运行测试模式
    
    Args:
        args: 命令行参数
        
    Returns:
        bool: 测试是否通过
    """
    logger.info("开始测试模式...")
    
    # 检查Java环境
    try:
        java_available, java_version = check_java_environment()
        if java_available:
            logger.info(f"Java 环境可用: {java_version}")
        else:
            logger.error("未检测到Java环境，请安装JDK/JRE 8或更高版本")
            return False
    except Exception as e:
        logger.error(f"检查Java环境时出错: {e}")
        return False
    
    # 检查反编译引擎
    engine_tests = []
    
    # 只测试指定的引擎或全部测试
    if args.all:
        engines = ['cfr', 'fernflower', 'jadx']
    else:
        engines = ['cfr']  # 默认只测试CFR
    
    for engine in engines:
        try:
            kwargs = {}
            if hasattr(args, f"{engine}_path"):
                engine_path = getattr(args, f"{engine}_path")
                if engine_path:
                    kwargs[f"{engine}_path"] = engine_path
            
            # 尝试获取反编译工具实例
            decompiler = get_decompiler(engine=engine, **kwargs)
            logger.info(f"成功初始化 {engine.upper()} 反编译引擎")
            engine_tests.append((engine, True))
        except Exception as e:
            logger.warning(f"初始化 {engine.upper()} 反编译引擎失败: {e}")
            engine_tests.append((engine, False))
    
    # 总结测试结果
    success_count = sum(1 for _, success in engine_tests if success)
    logger.info(f"测试完成: {success_count}/{len(engine_tests)} 引擎可用")
    
    return success_count > 0

def main() -> int:
    """
    主函数
    
    Returns:
        int: 退出代码
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 处理诊断模式
        if hasattr(args, 'diagnostic') and args.diagnostic:
            diagnostic_tool = DiagnosticTool()
            diagnostic_tool.run()
            return 0
        
        # 设置日志级别
        log_level = "INFO"
        if args.debug:
            log_level = "DEBUG"
        elif args.quiet:
            log_level = "ERROR"
        setup_logger(level=log_level)
        
        # 处理版本显示
        if args.version:
            print_version()
            return 0
        
        # 运行测试模式
        if args.test:
            success = run_tests(args)
            return 0 if success else 1
        
        # 验证Java环境
        try:
            java_available, _ = check_java_environment()
            if not java_available:
                raise JavaEnvironmentError("未检测到Java环境，请安装JDK/JRE 8或更高版本")
        except Exception as e:
            logger.error(f"Java环境检查失败: {e}")
            return 1
        
        # 验证输入路径
        try:
            input_paths = validate_input(args.input)
        except InvalidInputError as e:
            logger.error(str(e))
            return 1
        
        # 收集要处理的文件
        files_to_process = collect_input_files(input_paths, args.recursive)
        
        if not files_to_process:
            logger.warning("未找到可处理的文件")
            return 0
        
        # 确保输出目录存在
        try:
            ensure_directory(args.output_dir)
        except Exception as e:
            raise OutputDirectoryError(args.output_dir, f"创建输出目录失败: {e}")
        
        # 准备反编译参数
        decompiler_kwargs = {
            "deobfuscate": args.deobfuscate,
            "engine_options": args.engine_options,
        }
        
        # 添加工具路径参数
        for engine in ["cfr", "fernflower", "jadx"]:
            path_attr = f"{engine}_path"
            if hasattr(args, path_attr) and getattr(args, path_attr):
                decompiler_kwargs[path_attr] = getattr(args, path_attr)
        
        # 批量处理文件
        logger.info(f"开始处理 {len(files_to_process)} 个文件...")
        stats = batch_process_files(
            files_to_process,
            args.output_dir,
            engine=args.engine,
            threads=args.threads,
            timeout=args.timeout,
            **decompiler_kwargs
        )
        
        # 打印统计信息
        logger.info(f"处理完成: {stats}")
        
        # 返回退出代码
        if stats.get("failed_files", 0) > 0:
            # 有失败但也有成功，返回警告代码
            return 2 if stats.get("successful_files", 0) > 0 else 1
        
        return 0
        
    except JavaEnvironmentError as e:
        logger.error(str(e))
        return 1
    except ToolNotFoundError as e:
        logger.error(str(e))
        return 1
    except (InvalidInputError, OutputDirectoryError) as e:
        logger.error(str(e))
        return 1
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130  # SIGINT
    except Exception as e:
        logger.error(f"发生未预期的错误: {e}")
        if args.debug:
            import traceback
            logger.debug(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())