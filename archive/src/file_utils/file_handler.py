#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件处理工具函数
提供文件和目录操作的实用函数
"""

import os
import shutil
import zipfile
from pathlib import Path
from typing import List, Optional, Set, Iterator

# 支持的文件扩展名
SUPPORTED_EXTENSIONS = {'.class', '.jar', '.zip', '.war', '.ear'}

def ensure_directory(path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        path: 目录路径
        
    Returns:
        bool: 是否成功创建或目录已存在
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception:
        return False

def get_file_extension(file_path: str) -> str:
    """
    获取文件扩展名（小写）
    
    Args:
        file_path: 文件路径
        
    Returns:
        str: 小写的文件扩展名（包含点）
    """
    _, ext = os.path.splitext(file_path)
    return ext.lower()

def is_class_file(file_path: str) -> bool:
    """
    检查文件是否为class文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为class文件
    """
    return get_file_extension(file_path) == '.class'

def is_jar_file(file_path: str) -> bool:
    """
    检查文件是否为jar文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为jar文件
    """
    ext = get_file_extension(file_path)
    return ext in ('.jar', '.war', '.ear')

def is_valid_file(file_path: str) -> bool:
    """
    检查文件是否存在且为有效的文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为有效文件
    """
    return os.path.isfile(file_path) and os.path.exists(file_path)

def copy_file(src_path: str, dst_path: str) -> bool:
    """
    复制文件
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径
        
    Returns:
        bool: 是否成功复制
    """
    try:
        # 确保目标目录存在
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            ensure_directory(dst_dir)
        
        shutil.copy2(src_path, dst_path)
        return True
    except Exception:
        return False

def move_file(src_path: str, dst_path: str) -> bool:
    """
    移动文件
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径
        
    Returns:
        bool: 是否成功移动
    """
    try:
        # 确保目标目录存在
        dst_dir = os.path.dirname(dst_path)
        if dst_dir:
            ensure_directory(dst_dir)
        
        shutil.move(src_path, dst_path)
        return True
    except Exception:
        return False

def delete_file(file_path: str) -> bool:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否成功删除
    """
    try:
        if os.path.exists(file_path) and os.path.isfile(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

def get_relative_path(file_path: str, base_dir: str) -> str:
    """
    获取文件相对于基准目录的路径
    
    Args:
        file_path: 文件路径
        base_dir: 基准目录
        
    Returns:
        str: 相对路径
    """
    try:
        return os.path.relpath(file_path, base_dir)
    except ValueError:
        # 在不同驱动器上时，返回原路径
        return file_path

def normalize_path(path: str) -> str:
    """
    规范化路径
    
    Args:
        path: 路径字符串
        
    Returns:
        str: 规范化后的路径
    """
    return os.path.normpath(os.path.abspath(os.path.expanduser(path)))

def collect_files_by_extension(
    directory: str, 
    extensions: Set[str], 
    recursive: bool = True
) -> Iterator[str]:
    """
    收集指定扩展名的文件
    
    Args:
        directory: 要搜索的目录
        extensions: 要匹配的扩展名集合（小写，包含点）
        recursive: 是否递归搜索子目录
        
    Yields:
        str: 匹配的文件路径
    """
    if recursive:
        for root, _, files in os.walk(directory):
            for file in files:
                if get_file_extension(file) in extensions:
                    yield os.path.join(root, file)
    else:
        for entry in os.scandir(directory):
            if entry.is_file() and get_file_extension(entry.name) in extensions:
                yield entry.path

def extract_jar(
    jar_path: str, 
    extract_dir: str, 
    filter_extensions: Optional[Set[str]] = None
) -> List[str]:
    """
    解压JAR文件
    
    Args:
        jar_path: JAR文件路径
        extract_dir: 解压目录
        filter_extensions: 要提取的文件扩展名集合（小写，包含点），None表示提取所有文件
        
    Returns:
        List[str]: 提取的文件路径列表
    """
    extracted_files = []
    
    try:
        # 确保解压目录存在
        ensure_directory(extract_dir)
        
        with zipfile.ZipFile(jar_path, 'r') as zip_ref:
            # 获取所有文件列表
            all_files = zip_ref.namelist()
            
            # 根据扩展名过滤文件
            if filter_extensions:
                files_to_extract = [
                    f for f in all_files 
                    if get_file_extension(f) in filter_extensions
                ]
            else:
                files_to_extract = all_files
            
            # 解压选定的文件
            for file in files_to_extract:
                try:
                    zip_ref.extract(file, extract_dir)
                    extracted_files.append(os.path.join(extract_dir, file))
                except Exception:
                    # 忽略无法提取的文件
                    pass
    
    except Exception:
        # 解压失败，返回空列表
        pass
    
    return extracted_files