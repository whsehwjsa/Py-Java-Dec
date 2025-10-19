#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CLI入口实现
处理命令行参数并执行相应的反编译操作
"""

import os
import sys
import time
import json
from typing import Optional, Dict, Any

from java_decompiler import __version__
from java_decompiler.cli.parser import parse_arguments
from java_decompiler.config.config_manager import load_config, save_config
from java_decompiler.core.processor import DecompilationProcessor, check_java_environment
from java_decompiler.core.decompiler_manager import DecompilerManager, get_available_engines
from java_decompiler.engines.engine_manager import set_default_engine
from java_decompiler.logger.logger import get_logger, setup_logger
from java_decompiler.exceptions import (
    JavaDecompilerError,
    FileNotFoundError,
    InvalidInputError,
    EngineNotFoundError,
    JavaRuntimeError
)
from java_decompiler.utils.file_utils import (
    is_class_file,
    is_jar_file,
    is_apk_file
)
from java_decompiler.utils.path_utils import normalize_path
from java_decompiler.performance.stats_collector import StatsCollector
from java_decompiler.diagnostics import DiagnosticTool

logger = get_logger(__name__)


def main() -> int:
    """
    CLI主函数
    
    Returns:
        int: 退出代码，0表示成功，非0表示失败
    """
    try:
        # 解析命令行参数
        args = parse_arguments()
        
        # 设置日志级别
        log_level = "INFO"
        if args.quiet:
            log_level = "ERROR"
        elif args.verbose:
            log_level = "DEBUG"
        
        # 配置日志
        setup_logger(level=log_level, log_file=args.log_file)
        
        # 加载配置
        config = load_config(args.config)
        
        # 合并命令行参数到配置
        config = _merge_args_to_config(args, config)
        
        # 处理特殊命令
        if args.list_engines:
            return _list_available_engines(config)
        
        if args.diagnostic:
            return _run_diagnostic(config)
        
        # 处理反编译命令
        if args.input_path:
            return _run_decompilation(args, config)
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("用户中断操作")
        return 130  # SIGINT
    except JavaDecompilerError as e:
        logger.error(f"错误: {str(e)}")
        return 1
    except Exception as e:
        logger.error(f"未预期的错误: {str(e)}", exc_info=True)
        return 2


def _merge_args_to_config(args: argparse.Namespace, config: Dict[str, Any]) -> Dict[str, Any]:
    """
    将命令行参数合并到配置字典中
    
    Args:
        args: 命令行参数
        config: 配置字典
        
    Returns:
        Dict: 更新后的配置字典
    """
    # 合并引擎配置
    if args.engine_config:
        config.setdefault("engines", {}).update(args.engine_config)
    
    # 设置线程数
    if args.threads > 0:
        config["threads"] = args.threads
    
    return config


def _list_available_engines(config: Dict[str, Any]) -> int:
    """
    列出所有可用的反编译引擎
    
    Args:
        config: 配置字典
        
    Returns:
        int: 退出代码
    """
    print(f"Java Decompiler v{__version__} - 可用引擎列表")
    print("=" * 60)
    
    # 首先检查Java环境
    if not check_java_environment():
        print("✗ Java环境不可用，请安装JRE或JDK")
        print("=" * 60)
        return 1
    
    engines = get_available_engines(config)
    
    available_count = 0
    
    for name, info in engines.items():
        status = "✓ 可用" if info["available"] else "✗ 不可用"
        if info["available"]:
            available_count += 1
            
        print(f"- {name:<12} [{status}] - {info['description']} (v{info['version']})")
        
        # 如果有详细的元数据信息，显示更多细节
        if info.get("metadata"):
            metadata = info["metadata"]
            if hasattr(metadata, "supported_file_types") and metadata.supported_file_types:
                file_types = ", ".join(metadata.supported_file_types)
                print(f"  支持文件类型: {file_types}")
            if hasattr(metadata, "description") and metadata.description:
                print(f"  描述: {metadata.description}")
    
    print("=" * 60)
    print(f"总计: {available_count}/{len(engines)} 个引擎可用")
    
    if available_count == 0:
        print("\n警告: 没有可用的反编译引擎，请确保工具路径配置正确。")
        return 1
    
    return 0


def _run_diagnostic(config: Dict[str, Any]) -> int:
    """
    运行诊断工具
    
    Args:
        config: 配置字典
        
    Returns:
        int: 退出代码
    """
    print(f"Java Decompiler v{__version__} - 系统诊断")
    print("=" * 60)
    
    try:
        diagnostic = DiagnosticTool(config)
        results = diagnostic.run_full_diagnostic()
        
        # 打印诊断结果
        print("\n[系统环境检查]")
        print(f"  Python版本: {results['python_version']}")
        print(f"  Java环境: {'可用' if results['java_available'] else '不可用'}")
        if not results['java_available']:
            print("    错误: 请安装Java运行环境 (JRE) 1.8或更高版本")
        else:
            print(f"    版本: {results['java_version']}")
        
        print("\n[工具路径检查]")
        for tool, status in results['tools_available'].items():
            if status['available']:
                print(f"  ✓ {tool}: {status['path']}")
            else:
                print(f"  ✗ {tool}: 未找到 ({status['error']})")
        
        print("\n[引擎可用性检查]")
        for engine, status in results['engines_available'].items():
            if status['available']:
                print(f"  ✓ {engine}: 可用")
            else:
                print(f"  ✗ {engine}: 不可用 ({status['error']})")
        
        print("\n[配置检查]")
        if results['config_errors']:
            for error in results['config_errors']:
                print(f"  ✗ {error}")
        else:
            print("  ✓ 配置文件正常")
        
        print("\n[权限检查]")
        if results['permission_errors']:
            for error in results['permission_errors']:
                print(f"  ✗ {error}")
        else:
            print("  ✓ 权限正常")
        
        print("\n" + "=" * 60)
        
        # 生成诊断报告
        if results['has_errors']:
            print("诊断完成，但发现问题。建议修复上述错误后再使用反编译工具。")
            return 1
        else:
            print("诊断完成，系统环境正常！")
            return 0
            
    except Exception as e:
        print(f"诊断过程中出错: {str(e)}")
        return 1


def _run_decompilation(args: argparse.Namespace, config: Dict[str, Any]) -> int:
    """
    执行反编译操作
    
    Args:
        args: 命令行参数
        config: 配置字典
        
    Returns:
        int: 退出代码
    """
    # 首先检查Java环境
    if not check_java_environment():
        raise JavaRuntimeError("未检测到Java环境，请安装JRE或JDK 1.8或更高版本")
        
    # 验证输入路径
    input_path = normalize_path(args.input_path)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入路径不存在: {input_path}")
    
    # 确定输出路径
    output_path = _determine_output_path(args.input_path, args.output_path, args.engine)
    output_path = normalize_path(output_path)
    
    # 检查输出路径
    if os.path.exists(output_path) and not args.force:
        if os.path.isdir(output_path):
            logger.warning(f"输出目录已存在: {output_path}")
        else:
            raise InvalidInputError(f"输出文件已存在: {output_path} (使用 --force 强制覆盖)")
    
    print(f"Java Decompiler v{__version__}")
    print(f"输入: {input_path}")
    print(f"输出: {output_path}")
    
    # 创建处理器
    processor = DecompilationProcessor(config)
    
    start_time = time.time()
    
    # 进度回调函数
    def progress_callback(status: Dict[str, Any]):
        if status.get("status") == "started":
            print("开始反编译...")
        elif status.get("status") == "processing":
            processed = status.get("processed", 0)
            total = status.get("total", 0)
            progress = status.get("progress", 0)
            if total > 0 and processed % 5 == 0:  # 每处理5个文件显示一次进度
                print(f"进度: {processed}/{total} ({progress:.1%})")
        elif status.get("status") == "completed":
            print("反编译完成！")
    
    # 执行反编译
    try:
        if os.path.isfile(input_path):
            # 处理单个文件
            if is_class_file(input_path) or is_jar_file(input_path) or is_apk_file(input_path):
                # 如果指定了默认引擎，设置它
                if args.engine:
                    set_default_engine(args.engine)
                
                results = processor.decompile_file(
                    input_path,
                    output_path,
                    args.engine,
                    args.engine_config,
                    progress_callback
                )
                
                if results["success"]:
                    print(f"文件反编译成功！耗时: {results['duration']:.2f}秒")
                else:
                    print(f"文件反编译失败: {results['error']}")
                    return 1
            else:
                raise InvalidInputError(f"不支持的文件类型: {input_path}")
                
        else:  # os.path.isdir(input_path)
            # 处理目录
            # 如果指定了默认引擎，设置它
            if args.engine:
                set_default_engine(args.engine)
                
            results = processor.decompile_directory(
                input_path,
                output_path,
                args.engine,
                args.engine_config,
                args.recursive,
                None,
                progress_callback
            )
            
            print(f"\n反编译统计:")
            print(f"  总文件数: {results['total_files']}")
            print(f"  成功: {results['success_count']}")
            print(f"  失败: {results['failed_count']}")
            print(f"  总耗时: {results['duration']:.2f}秒")
            
            if results['failed_count'] > 0:
                print("\n失败文件列表:")
                for i, failed in enumerate(results['failed_files'], 1):
                    print(f"  {i}. {failed['file']} - {failed['error']}")
                return 1
                
    except KeyboardInterrupt:
        print("\n反编译操作被用户中断")
        return 130
    except JavaRuntimeError as e:
        print(f"\nJava环境错误: {str(e)}")
        return 1
    except Exception as e:
        print(f"\n反编译过程中出错: {str(e)}")
        raise
    
    return 0


def _determine_output_path(input_path: str, output_path: Optional[str], engine: Optional[str]) -> str:
    """
    确定输出路径
    
    Args:
        input_path: 输入路径
        output_path: 用户指定的输出路径（可能为None）
        engine: 使用的引擎名称
        
    Returns:
        str: 确定的输出路径
    """
    if output_path:
        return output_path
    
    # 如果未指定输出路径，根据输入路径生成
    base_name = os.path.basename(input_path)
    dir_name = os.path.dirname(input_path) or "."
    
    if os.path.isfile(input_path):
        # 对于文件，替换扩展名或添加后缀
        name, ext = os.path.splitext(base_name)
        if engine:
            suffix = f"_decompiled_{engine}"
        else:
            suffix = "_decompiled"
            
        if ext.lower() in [".class"]:
            # 类文件直接替换扩展名为.java
            return os.path.join(dir_name, name + ".java")
        else:
            # 其他文件（如JAR, APK）创建对应的目录
            return os.path.join(dir_name, name + suffix)
    else:
        # 对于目录，创建一个新目录
        if engine:
            suffix = f"_decompiled_{engine}"
        else:
            suffix = "_decompiled"
            
        return os.path.join(dir_name, base_name + suffix)


if __name__ == "__main__":
    sys.exit(main())