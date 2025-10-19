#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件名处理工具函数
提供Java类文件名解析、转换等功能，特别支持匿名内部类文件名处理
"""

import os
import re
from typing import Tuple, Optional

# 匿名内部类文件名模式匹配（如：Outer$1.class, Outer$Inner$2.class）
ANONYMOUS_INNER_CLASS_PATTERN = re.compile(r'^(\w+(?:\$\w+)*)\$(\d+)(\.class)?$')
# 命名内部类文件名模式匹配（如：Outer$Inner.class）
NAMED_INNER_CLASS_PATTERN = re.compile(r'^(\w+(?:\$\w+)*)\$(\w+)(\.class)?$')

def parse_java_class_filename(filename: str) -> Tuple[str, str, bool]:
    """
    解析Java类文件名，识别普通类、命名内部类和匿名内部类
    
    Args:
        filename: 类文件名（可以包含或不包含.class扩展名）
        
    Returns:
        Tuple[str, str, bool]: (基础类名, 内部类标识符, 是否为匿名内部类)
        - 对于普通类：('ClassName', '', False)
        - 对于命名内部类：('OuterClass', 'InnerClass', False)
        - 对于匿名内部类：('OuterClass', '1', True)
    """
    # 移除可能的扩展名
    base_name = filename
    if filename.endswith('.class'):
        base_name = filename[:-6]
    
    # 检查是否为匿名内部类
    anonymous_match = ANONYMOUS_INNER_CLASS_PATTERN.match(base_name)
    if anonymous_match:
        outer_name = anonymous_match.group(1)
        inner_id = anonymous_match.group(2)
        return (outer_name, inner_id, True)
    
    # 检查是否为命名内部类
    named_match = NAMED_INNER_CLASS_PATTERN.match(base_name)
    if named_match:
        outer_name = named_match.group(1)
        inner_name = named_match.group(2)
        return (outer_name, inner_name, False)
    
    # 普通类
    return (base_name, '', False)

def get_java_file_name(class_filename: str) -> str:
    """
    根据类文件名获取对应的Java文件名
    
    Args:
        class_filename: 类文件名（可以包含或不包含路径）
        
    Returns:
        str: 对应的Java文件名（不包含路径）
    """
    # 提取文件名部分（去除路径）
    filename = os.path.basename(class_filename)
    
    # 解析类文件名
    base_class_name, inner_class_id, is_anonymous = parse_java_class_filename(filename)
    
    # 对于匿名内部类和命名内部类，Java代码都在外部类的.java文件中
    # 因此返回外部类的Java文件名
    return f"{base_class_name}.java"

def get_package_from_path(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    从文件路径推断Java包名
    
    Args:
        file_path: 类文件或Java文件的路径
        base_dir: 基础目录路径（如果提供，则相对于此目录计算包名）
        
    Returns:
        str: Java包名
    """
    # 获取文件的目录部分
    dir_path = os.path.dirname(file_path)
    
    if base_dir:
        # 计算相对于基础目录的路径
        try:
            rel_path = os.path.relpath(dir_path, base_dir)
            # 将路径分隔符替换为点
            return rel_path.replace(os.path.sep, '.')
        except ValueError:
            # 如果在不同驱动器上，无法计算相对路径
            pass
    
    # 如果没有提供基础目录或无法计算相对路径，返回空包名
    return ''

def get_class_name_with_package(file_path: str, base_dir: Optional[str] = None) -> str:
    """
    获取包含包名的完整类名
    
    Args:
        file_path: 类文件路径
        base_dir: 基础目录路径
        
    Returns:
        str: 完整的类名（包含包名）
    """
    # 获取包名
    package = get_package_from_path(file_path, base_dir)
    
    # 解析类文件名
    filename = os.path.basename(file_path)
    base_class_name, _, _ = parse_java_class_filename(filename)
    
    # 组合包名和类名
    if package:
        return f"{package}.{base_class_name}"
    else:
        return base_class_name