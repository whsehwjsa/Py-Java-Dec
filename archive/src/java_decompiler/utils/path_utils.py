#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
路径处理工具函数
提供路径标准化、相对路径计算等功能
"""

import os
import platform
import re
from typing import Optional

from java_decompiler.exceptions import PathError
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)


def normalize_path(path: str) -> str:
    """
    标准化路径，处理相对路径、用户目录扩展等
    
    Args:
        path: 输入路径
        
    Returns:
        str: 标准化后的绝对路径
        
    Raises:
        PathError: 路径处理错误
    """
    try:
        # 扩展用户目录 ~
        expanded_path = os.path.expanduser(path)
        
        # 获取绝对路径
        absolute_path = os.path.abspath(expanded_path)
        
        # 规范化路径分隔符
        # Windows使用\，Unix/Linux/Mac使用/
        if platform.system() == "Windows":
            normalized_path = re.sub(r'[\\/]+', '\\', absolute_path)
        else:
            normalized_path = re.sub(r'[\\/]+', '/', absolute_path)
        
        return normalized_path
    except Exception as e:
        raise PathError(f"路径标准化失败 '{path}': {str(e)}")

def get_relative_path(path: str, base: str) -> str:
    """
    计算相对路径
    
    Args:
        path: 目标路径
        base: 基准路径
        
    Returns:
        str: 相对路径
        
    Raises:
        PathError: 路径处理错误
    """
    try:
        # 先标准化两个路径
        norm_path = normalize_path(path)
        norm_base = normalize_path(base)
        
        # 计算相对路径
        relative_path = os.path.relpath(norm_path, norm_base)
        
        return relative_path
    except Exception as e:
        raise PathError(f"计算相对路径失败 '{path}' -> '{base}': {str(e)}")

def ensure_parent_directory(file_path: str) -> None:
    """
    确保文件的父目录存在
    
    Args:
        file_path: 文件路径
        
    Raises:
        PathError: 路径处理错误
    """
    try:
        # 获取父目录路径
        parent_dir = os.path.dirname(file_path)
        
        # 如果父目录不为空，则创建
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
            logger.debug(f"确保父目录存在: {parent_dir}")
    except Exception as e:
        raise PathError(f"创建父目录失败 '{file_path}': {str(e)}")

def get_unique_filename(file_path: str) -> str:
    """
    获取唯一的文件名，如果文件已存在则添加数字后缀
    
    Args:
        file_path: 原始文件路径
        
    Returns:
        str: 唯一的文件路径
    """
    # 如果文件不存在，直接返回原始路径
    if not os.path.exists(file_path):
        return file_path
    
    # 分离文件名和扩展名
    base_dir = os.path.dirname(file_path)
    base_name = os.path.basename(file_path)
    name, ext = os.path.splitext(base_name)
    
    # 查找可用的文件名
    counter = 1
    new_file_path = file_path
    
    while os.path.exists(new_file_path):
        # 格式: name_1.ext, name_2.ext, ...
        new_name = f"{name}_{counter}{ext}"
        new_file_path = os.path.join(base_dir, new_name)
        counter += 1
    
    logger.debug(f"文件已存在，返回唯一文件名: {new_file_path}")
    return new_file_path

def is_path_absolute(path: str) -> bool:
    """
    检查路径是否为绝对路径
    
    Args:
        path: 要检查的路径
        
    Returns:
        bool: 是否为绝对路径
    """
    return os.path.isabs(path)

def is_safe_path(path: str, base_dir: Optional[str] = None) -> bool:
    """
    检查路径是否安全（防止路径遍历攻击）
    
    Args:
        path: 要检查的路径
        base_dir: 基准目录，如果指定，则检查路径是否在基准目录内
        
    Returns:
        bool: 路径是否安全
    """
    try:
        # 标准化路径
        norm_path = normalize_path(path)
        
        # 如果指定了基准目录，检查路径是否在基准目录内
        if base_dir:
            norm_base = normalize_path(base_dir)
            # 确保基准目录以路径分隔符结尾
            if not norm_base.endswith(os.path.sep):
                norm_base += os.path.sep
            
            # 检查路径是否以基准目录开头
            return norm_path.startswith(norm_base)
        
        # 如果没有指定基准目录，至少确保路径是绝对路径
        return is_path_absolute(norm_path)
    except Exception:
        # 如果处理过程中出错，认为路径不安全
        return False

def join_paths(*paths) -> str:
    """
    安全地连接多个路径组件
    
    Args:
        *paths: 路径组件
        
    Returns:
        str: 连接后的路径
    """
    try:
        # 使用os.path.join连接路径
        joined_path = os.path.join(*paths)
        
        # 标准化路径
        return normalize_path(joined_path)
    except Exception as e:
        logger.warning(f"连接路径时出错: {str(e)}")
        # 如果出错，简单地用当前平台的分隔符连接
        separator = os.path.sep
        return separator.join(paths)

def get_path_separator() -> str:
    """
    获取当前操作系统的路径分隔符
    
    Returns:
        str: 路径分隔符
    """
    return os.path.sep

def get_file_extension(file_path: str, include_dot: bool = True) -> str:
    """
    获取文件扩展名
    
    Args:
        file_path: 文件路径
        include_dot: 是否包含点号
        
    Returns:
        str: 文件扩展名
    """
    _, ext = os.path.splitext(file_path)
    if not include_dot and ext:
        ext = ext[1:]  # 去掉点号
    return ext.lower()

def get_filename(file_path: str, include_extension: bool = True) -> str:
    """
    获取文件名
    
    Args:
        file_path: 文件路径
        include_extension: 是否包含扩展名
        
    Returns:
        str: 文件名
    """
    filename = os.path.basename(file_path)
    if not include_extension:
        filename = os.path.splitext(filename)[0]
    return filename

def find_common_path(paths: list) -> str:
    """
    查找多个路径的公共前缀
    
    Args:
        paths: 路径列表
        
    Returns:
        str: 公共路径前缀
    """
    if not paths:
        return ""
    
    # 标准化所有路径
    norm_paths = [normalize_path(path) for path in paths]
    
    # 获取路径分隔符
    separator = get_path_separator()
    
    # 分割路径为组件
    components_list = [path.split(separator) for path in norm_paths]
    
    # 找出公共组件
    common_components = []
    min_len = min(len(components) for components in components_list)
    
    for i in range(min_len):
        current_components = [components[i] for components in components_list]
        if all(comp == current_components[0] for comp in current_components):
            common_components.append(current_components[0])
        else:
            break
    
    # 重新组合成路径
    common_path = separator.join(common_components)
    
    # 如果是空字符串，返回当前目录
    if not common_path:
        return separator if separator == '/' else '.' + separator
    
    return common_path