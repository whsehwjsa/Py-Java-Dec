#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行参数解析器
提供增强的参数解析功能，支持丰富的命令行选项
"""

import argparse
import sys
from pathlib import Path


class ArgumentParser(argparse.ArgumentParser):
    """
    增强版命令行参数解析器
    """
    
    def error(self, message):
        """
        重写错误处理方法，显示错误信息和帮助
        """
        self.print_usage(sys.stderr)
        self.exit(2, f"\n错误: {message}\n")


def parse_arguments():
    """
    解析命令行参数
    
    Returns:
        argparse.Namespace: 解析后的参数命名空间
    """
    parser = ArgumentParser(
        description="Java 反编译工具 - 支持CFR、FernFlower和JADX多种引擎",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
示例:
  # 使用默认引擎反编译单个文件
  %(prog)s File.class
  
  # 使用特定引擎反编译JAR文件
  %(prog)s -e cfr app.jar -o output_dir
  
  # 多线程处理目录中的所有class文件
  %(prog)s -t 4 -r classes_dir -o output_dir
  
  # 使用自定义工具路径
  %(prog)s app.jar -o output_dir --fernflower-path /path/to/fernflower.jar --jadx-path /path/to/jadx.jar
        """
    )
    
    # 输入参数组
    input_group = parser.add_argument_group('输入选项')
    input_group.add_argument(
        'input',
        nargs='+',
        help='输入文件或目录路径'
    )
    input_group.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='递归处理子目录'
    )
    
    # 输出参数组
    output_group = parser.add_argument_group('输出选项')
    output_group.add_argument(
        '-o', '--output',
        dest='output_dir',
        default=Path.cwd().joinpath('decompiled'),
        help='输出目录路径，默认为当前目录下的decompiled目录'
    )
    output_group.add_argument(
        '-f', '--force',
        action='store_true',
        help='强制覆盖已存在的输出文件'
    )
    output_group.add_argument(
        '--flat',
        action='store_true',
        help='使用扁平目录结构，不保留原有的目录层级'
    )
    
    # 引擎参数组
    engine_group = parser.add_argument_group('引擎选项')
    engine_group.add_argument(
        '-e', '--engine',
        choices=['cfr', 'fernflower', 'jadx', 'auto'],
        default='auto',
        help='选择反编译引擎，默认自动选择'
    )
    engine_group.add_argument(
        '--engine-options',
        type=str,
        default='',
        help='传递给反编译引擎的额外选项，以空格分隔'
    )
    engine_group.add_argument(
        '--deobfuscate',
        action='store_true',
        help='启用反混淆功能（如果引擎支持）'
    )
    
    # 工具路径参数组
    path_group = parser.add_argument_group('工具路径选项')
    path_group.add_argument(
        '--cfr-path',
        type=str,
        help='CFR JAR文件路径'
    )
    path_group.add_argument(
        '--fernflower-path',
        type=str,
        help='FernFlower JAR文件路径'
    )
    path_group.add_argument(
        '--jadx-path',
        type=str,
        help='JADX JAR文件路径'
    )
    
    # 性能参数组
    performance_group = parser.add_argument_group('性能选项')
    performance_group.add_argument(
        '-t', '--threads',
        type=int,
        default=4,
        help='线程数量，默认为4'
    )
    performance_group.add_argument(
        '--timeout',
        type=int,
        default=300,
        help='单个文件的反编译超时时间（秒），默认为300秒'
    )
    
    # 配置参数组
    config_group = parser.add_argument_group('配置选项')
    config_group.add_argument(
        '-c', '--config',
        type=str,
        help='配置文件路径'
    )
    config_group.add_argument(
        '--save-config',
        action='store_true',
        help='保存当前配置到配置文件'
    )
    
    # 调试和日志参数组
    debug_group = parser.add_argument_group('调试和日志选项')
    debug_group.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='显示详细日志信息'
    )
    debug_group.add_argument(
        '--debug',
        action='store_true',
        help='显示调试信息'
    )
    debug_group.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，只输出错误信息'
    )
    
    # 测试参数组
    test_group = parser.add_argument_group('测试选项')
    test_group.add_argument(
        '--test',
        action='store_true',
        help='运行测试模式，验证配置和环境'
    )
    test_group.add_argument(
        '--all',
        action='store_true',
        help='测试所有反编译引擎'
    )
    
    # 关于参数组
    about_group = parser.add_argument_group('关于选项')
    about_group.add_argument(
        '-V', '--version',
        action='store_true',
        help='显示版本信息'
    )
    
    about_group.add_argument(
        '--diagnostic',
        action='store_true',
        help='运行诊断工具，检查系统环境和配置'
    )
    
    # 解析参数
    args = parser.parse_args()
    
    # 处理路径参数，确保使用绝对路径
    for attr_name in ['output_dir', 'config']:
        if hasattr(args, attr_name) and getattr(args, attr_name):
            setattr(args, attr_name, str(Path(getattr(args, attr_name)).absolute()))
    
    # 处理工具路径参数
    for attr_name in ['cfr_path', 'fernflower_path', 'jadx_path']:
        if hasattr(args, attr_name) and getattr(args, attr_name):
            setattr(args, attr_name, str(Path(getattr(args, attr_name)).absolute()))
    
    # 解析引擎选项字符串为列表
    if args.engine_options:
        args.engine_options = args.engine_options.split()
    else:
        args.engine_options = []
    
    return args