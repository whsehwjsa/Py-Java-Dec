"""工具函数模块"""

import os
import sys
from pathlib import Path
from typing import Optional, Dict

# 获取当前文件所在目录
current_dir = Path(__file__).parent
# 添加当前目录到Python路径以便导入
sys.path.append(str(current_dir))

# 导入反编译工具相关模块
from cfr import CFRDecompiler
from fernflower import FernFlowerDecompiler
from jadx import JADXDecompiler


def validate_paths(input_path: str, output_dir: str) -> None:
    """验证输入和输出路径
    
    Args:
        input_path: 输入路径
        output_dir: 输出目录
        
    Raises:
        FileNotFoundError: 输入路径不存在
        PermissionError: 输出目录无写入权限
        ValueError: 其他路径验证错误
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"输入路径不存在：{input_path}")
    
    # 确保输出目录存在
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        raise OSError(f"无法创建输出目录：{output_dir}，错误：{str(e)}")
    
    # 检查写入权限
    if not os.access(output_dir, os.W_OK):
        raise PermissionError(f"输出目录无写入权限：{output_dir}")
    
    # 尝试写入一个临时文件来验证权限
    test_file = os.path.join(output_dir, ".test_write.txt")
    try:
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
    except Exception as e:
        raise PermissionError(f"无法写入输出目录：{output_dir}，错误：{str(e)}")


def parse_tool_options(options_str: Optional[str], tool_name: str) -> Dict[str, str]:
    """解析反编译工具额外选项字符串
    
    Args:
        options_str: 格式为 "key1=value1,key2=value2" 的选项字符串
        tool_name: 工具名称（用于错误提示）
        
    Returns:
        解析后的选项字典
    """
    options = {}
    if not options_str:
        return options
    
    try:
        for option in options_str.split(","):
            if "=" in option:
                key, value = option.split("=", 1)
                options[key.strip()] = value.strip()
    except Exception as e:
        raise ValueError(f"解析{tool_name}选项失败：{str(e)}")
    
    return options


def get_decompiler(args):
    """根据命令行参数获取适当的反编译工具实例"""
    # 确保只能选择一种反编译工具
    tool_count = sum([
        args.fernflower,
        args.jadx
    ])
    
    if tool_count > 1:
        raise ValueError("只能选择一种反编译工具：--fernflower 或 --jadx")
    
    # 默认使用CFR
    if not args.fernflower and not args.jadx:
        options = parse_tool_options(args.tool_options or args.cfr_options, "CFR")
        return CFRDecompiler(
            verbose=args.verbose,
            deobfuscate=args.deobfuscate,
            cfr_path=args.cfr_path,
            max_workers=args.threads,
            timeout=args.timeout,
            additional_options=options
        )
    
    # 使用FernFlower
    elif args.fernflower:
        options = parse_tool_options(args.tool_options or args.fernflower_options, "FernFlower")
        return FernFlowerDecompiler(
            verbose=args.verbose,
            deobfuscate=args.deobfuscate,
            fernflower_path=args.fernflower_path,
            max_workers=args.threads,
            timeout=args.timeout,
            additional_options=options
        )
    
    # 使用JADX
    elif args.jadx:
        options = parse_tool_options(args.tool_options or args.jadx_options, "JADX")
        return JADXDecompiler(
            verbose=args.verbose,
            deobfuscate=args.deobfuscate,
            jadx_path=args.jadx_path,
            max_workers=args.threads,
            timeout=args.timeout,
            additional_options=options
        )