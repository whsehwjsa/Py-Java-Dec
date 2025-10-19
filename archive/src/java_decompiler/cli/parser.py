#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行参数解析器
定义和处理命令行参数
"""

import argparse
import sys
import os
from typing import Optional, Dict, Any

from java_decompiler import __version__
from java_decompiler.config.config_manager import load_config


def parse_arguments(args: Optional[list] = None) -> argparse.Namespace:
    """
    解析命令行参数
    
    Args:
        args: 要解析的参数列表，如果为None则使用sys.argv[1:]
        
    Returns:
        argparse.Namespace: 解析后的参数命名空间
    """
    # 创建参数解析器
    parser = argparse.ArgumentParser(
        prog="java-decompiler",
        description="反编译工具，支持CFR、FernFlower和JADX",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # 位置参数
    parser.add_argument(
        "input_path",
        nargs="?",
        help="输入文件或目录路径（.class, .jar, .war, .ear, .apk 或包含这些文件的目录）"
    )
    
    parser.add_argument(
        "output_path",
        nargs="?",
        help="输出文件或目录路径（如果未指定，将在输入路径同目录下创建输出）"
    )
    
    # 引擎选择
    engine_group = parser.add_argument_group("引擎选择")
    engine_group.add_argument(
        "--engine",
        "-e",
        choices=["cfr", "fernflower", "jadx"],
        default=None,
        help="指定反编译引擎\n"  
             "cfr: 高性能反编译器，适合大多数场景\n"  
             "fernflower: IntelliJ IDEA内置的反编译器\n"  
             "jadx: 特别适合Android应用分析\n"  
             "(默认: 自动选择最佳引擎)"
    )
    
    # 输出选项
    output_group = parser.add_argument_group("输出选项")
    output_group.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        default=True,
        help="递归处理子目录中的文件 (默认: 启用)"
    )
    
    output_group.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="禁用递归处理"
    )
    
    output_group.add_argument(
        "--force",
        "-f",
        action="store_true",
        default=False,
        help="强制覆盖已存在的输出文件"
    )
    
    # 配置选项
    config_group = parser.add_argument_group("配置选项")
    config_group.add_argument(
        "--config",
        "-c",
        type=str,
        default=None,
        help="配置文件路径"
    )
    
    config_group.add_argument(
        "--threads",
        "-t",
        type=int,
        default=0,
        help="线程数，0表示自动检测 (默认: 0)"
    )
    
    # 引擎特定选项
    specific_group = parser.add_argument_group("引擎特定选项")
    
    # CFR特定选项
    specific_group.add_argument(
        "--cfr-path",
        type=str,
        default=None,
        help="CFR JAR文件路径"
    )
    
    specific_group.add_argument(
        "--cfr-options",
        type=str,
        default="",
        help="CFR额外选项，格式: 'option1=value1,option2=value2'"
    )
    
    # FernFlower特定选项
    specific_group.add_argument(
        "--fernflower-path",
        type=str,
        default=None,
        help="FernFlower JAR文件路径"
    )
    
    # JADX特定选项
    specific_group.add_argument(
        "--jadx-path",
        type=str,
        default=None,
        help="JADX目录路径"
    )
    
    specific_group.add_argument(
        "--deobfuscate",
        action="store_true",
        default=False,
        help="启用反混淆 (主要用于JADX)"
    )
    
    # 日志和调试选项
    log_group = parser.add_argument_group("日志和调试选项")
    log_group.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        default=False,
        help="输出详细日志信息"
    )
    
    log_group.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        default=False,
        help="仅输出错误信息"
    )
    
    log_group.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="日志文件路径"
    )
    
    # 诊断和信息选项
    about_group = parser.add_argument_group("诊断和信息选项")
    about_group.add_argument(
        "--list-engines",
        action="store_true",
        default=False,
        help="列出所有可用的反编译引擎"
    )
    
    about_group.add_argument(
        "--version",
        "-V",
        action="store_true",
        default=False,
        help="显示版本信息并退出"
    )
    
    about_group.add_argument(
        "--diagnostic",
        action="store_true",
        default=False,
        help="运行诊断工具检查系统环境和配置"
    )
    
    # 解析参数
    parsed_args = parser.parse_args(args)
    
    # 特殊情况处理
    if parsed_args.version:
        print(f"Java Decompiler v{__version__}")
        sys.exit(0)
    
    # 如果既没有指定输入/输出路径，也没有指定列表引擎或诊断模式，则显示帮助
    if (not parsed_args.input_path and 
        not parsed_args.output_path and 
        not parsed_args.list_engines and 
        not parsed_args.diagnostic):
        parser.print_help()
        sys.exit(1)
    
    # 处理引擎特定选项，转换为配置字典
    parsed_args.engine_config = _build_engine_config(parsed_args)
    
    return parsed_args


def _build_engine_config(args: argparse.Namespace) -> Dict[str, Any]:
    """
    从命令行参数构建引擎配置字典
    
    Args:
        args: 解析后的命令行参数
        
    Returns:
        Dict: 引擎配置字典
    """
    engine_config = {}
    
    # CFR配置
    if args.cfr_path:
        engine_config.setdefault("cfr", {})["path"] = args.cfr_path
    
    if args.cfr_options:
        cfr_options = {}
        # 解析选项字符串 'option1=value1,option2=value2'
        for opt_pair in args.cfr_options.split(","):
            if "=" in opt_pair:
                key, value = opt_pair.split("=", 1)
                cfr_options[key.strip()] = value.strip()
        if cfr_options:
            engine_config.setdefault("cfr", {}).update(cfr_options)
    
    # FernFlower配置
    if args.fernflower_path:
        engine_config.setdefault("fernflower", {})["path"] = args.fernflower_path
    
    # JADX配置
    if args.jadx_path:
        engine_config.setdefault("jadx", {})["path"] = args.jadx_path
    
    if args.deobfuscate:
        engine_config.setdefault("jadx", {})["deobfuscation"] = True
    
    # 线程配置
    if args.threads > 0:
        # 应用到所有引擎
        for engine in ["cfr", "fernflower", "jadx"]:
            engine_config.setdefault(engine, {})["threads"] = args.threads
    
    return engine_config