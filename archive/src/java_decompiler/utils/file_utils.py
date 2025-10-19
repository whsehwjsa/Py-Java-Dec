#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件处理工具函数
提供文件类型检测、目录操作和JAR处理等功能
"""

import os
import shutil
import tempfile
import zipfile
from typing import List, Optional
from pathlib import Path

from java_decompiler.exceptions import FileOperationError
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)

# 尝试导入magic库，如果不可用则提供替代方案
try:
    import magic  # 需要python-magic库
except ImportError:
    logger.warning("python-magic库未安装，将使用基于文件扩展名的文件类型检测")
    magic = None

# 文件类型魔术数字/签名
CLASS_FILE_MAGIC = b'\xca\xfe\xba\xbe'  # Java类文件魔数
ZIP_MAGIC = b'PK\x03\x04'  # ZIP/JAR文件魔数
APK_MAGIC = b'PK\x03\x04'  # APK文件也是ZIP格式

# 文件扩展名映射
FILE_EXTENSIONS = {
    "class": [".class"],
    "jar": [".jar", ".war", ".ear", ".jmod"],
    "apk": [".apk"]
}

def ensure_directory(directory: str) -> None:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        directory: 目录路径
        
    Raises:
        FileOperationError: 无法创建目录
    """
    try:
        os.makedirs(directory, exist_ok=True)
    except Exception as e:
        raise FileOperationError(f"无法创建目录 '{directory}': {str(e)}")

def is_class_file(file_path: str) -> bool:
    """
    检查文件是否为Java类文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为Java类文件
    """
    # 快速检查文件扩展名
    if not file_path.lower().endswith(".class"):
        return False
        
    # 检查文件是否存在且可读
    if not os.path.isfile(file_path):
        return False
    
    try:
        # 读取文件开头的魔数进行确认
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == CLASS_FILE_MAGIC
    except Exception:
        # 如果读取文件失败，尝试使用python-magic
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            return "java" in file_type or "x-java" in file_type
        except Exception:
            # 如果都失败，只依赖文件扩展名
            return file_path.lower().endswith(".class")

def is_jar_file(file_path: str) -> bool:
    """
    检查文件是否为JAR文件或JAR相关格式（WAR、EAR等）
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为JAR文件
    """
    # 快速检查文件扩展名
    ext = os.path.splitext(file_path)[1].lower()
    if ext in FILE_EXTENSIONS["jar"]:
        # 进一步验证文件内容
        return _is_zip_file(file_path)
    return False

def is_apk_file(file_path: str) -> bool:
    """
    检查文件是否为APK文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为APK文件
    """
    # 快速检查文件扩展名
    if not file_path.lower().endswith(".apk"):
        return False
    
    # 进一步验证文件内容
    if not _is_zip_file(file_path):
        return False
        
    # 检查APK文件是否包含AndroidManifest.xml
    try:
        with zipfile.ZipFile(file_path, "r") as zip_ref:
            return "AndroidManifest.xml" in zip_ref.namelist()
    except Exception:
        return False

def _is_zip_file(file_path: str) -> bool:
    """
    检查文件是否为ZIP格式（JAR、APK等都是ZIP格式）
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否为ZIP文件
    """
    # 检查文件是否存在且可读
    if not os.path.isfile(file_path):
        return False
    
    try:
        # 读取文件开头的魔数进行确认
        with open(file_path, "rb") as f:
            header = f.read(4)
        return header == ZIP_MAGIC
    except Exception:
        # 如果读取文件失败，尝试使用python-magic
        try:
            mime = magic.Magic(mime=True)
            file_type = mime.from_file(file_path)
            return "zip" in file_type
        except Exception:
            # 如果都失败，尝试用zipfile打开
            try:
                with zipfile.ZipFile(file_path, "r") as _:
                    return True
            except zipfile.BadZipFile:
                return False
            except Exception:
                return False

def extract_jar(jar_path: str, output_dir: str) -> bool:
    """
    解压JAR文件
    
    Args:
        jar_path: JAR文件路径
        output_dir: 输出目录
        
    Returns:
        bool: 解压是否成功
        
    Raises:
        FileOperationError: 解压失败
    """
    if not os.path.exists(jar_path):
        raise FileOperationError(f"JAR文件不存在: {jar_path}")
        
    if not is_jar_file(jar_path) and not is_apk_file(jar_path):
        raise FileOperationError(f"不是有效的JAR或APK文件: {jar_path}")
        
    # 确保输出目录存在
    ensure_directory(output_dir)
    
    try:
        with zipfile.ZipFile(jar_path, "r") as zip_ref:
            zip_ref.extractall(output_dir)
        logger.debug(f"成功解压文件到: {output_dir}")
        return True
    except Exception as e:
        raise FileOperationError(f"解压文件失败 '{jar_path}': {str(e)}")

def get_files_by_extension(directory: str, extension: str, recursive: bool = True) -> List[str]:
    """
    获取目录中所有指定扩展名的文件
    
    Args:
        directory: 目录路径
        extension: 文件扩展名，带点号，如".class"
        recursive: 是否递归子目录
        
    Returns:
        List[str]: 文件路径列表
    """
    if not os.path.exists(directory) or not os.path.isdir(directory):
        logger.warning(f"目录不存在或不是有效目录: {directory}")
        return []
    
    file_paths = []
    extension = extension.lower()
    
    if recursive:
        # 递归搜索
        for root, _, files in os.walk(directory):
            for file in files:
                if file.lower().endswith(extension):
                    file_paths.append(os.path.join(root, file))
    else:
        # 非递归搜索
        try:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path) and file.lower().endswith(extension):
                    file_paths.append(file_path)
        except Exception as e:
            logger.warning(f"扫描目录时出错 '{directory}': {str(e)}")
    
    return file_paths

def create_temp_directory(suffix: Optional[str] = None, prefix: Optional[str] = "java_decompiler_") -> str:
    """
    创建临时目录
    
    Args:
        suffix: 临时目录名称后缀
        prefix: 临时目录名称前缀
        
    Returns:
        str: 临时目录路径
        
    Raises:
        FileOperationError: 创建临时目录失败
    """
    try:
        # 创建临时目录
        temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix)
        return temp_dir
    except Exception as e:
        raise FileOperationError(f"创建临时目录失败: {str(e)}")

def cleanup_temp_directory(temp_dir: str) -> None:
    """
    清理临时目录
    
    Args:
        temp_dir: 临时目录路径
    """
    if os.path.exists(temp_dir) and os.path.isdir(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            logger.debug(f"已清理临时目录: {temp_dir}")
        except Exception as e:
            logger.warning(f"清理临时目录时出错 '{temp_dir}': {str(e)}")

def copy_file(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    复制文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        overwrite: 是否覆盖已存在的文件
        
    Returns:
        bool: 复制是否成功
        
    Raises:
        FileOperationError: 复制失败
    """
    # 检查源文件
    if not os.path.exists(src):
        raise FileOperationError(f"源文件不存在: {src}")
        
    if not os.path.isfile(src):
        raise FileOperationError(f"源路径不是文件: {src}")
        
    # 检查目标文件
    if os.path.exists(dst):
        if os.path.isdir(dst):
            # 如果目标是目录，将源文件名添加到目标路径
            dst = os.path.join(dst, os.path.basename(src))
            
        if os.path.exists(dst) and not overwrite:
            raise FileOperationError(f"目标文件已存在: {dst}")
            
    # 确保目标文件的父目录存在
    ensure_directory(os.path.dirname(dst))
    
    try:
        shutil.copy2(src, dst)
        logger.debug(f"已复制文件: {src} -> {dst}")
        return True
    except Exception as e:
        raise FileOperationError(f"复制文件失败 '{src}' -> '{dst}': {str(e)}")

def move_file(src: str, dst: str, overwrite: bool = False) -> bool:
    """
    移动文件
    
    Args:
        src: 源文件路径
        dst: 目标文件路径
        overwrite: 是否覆盖已存在的文件
        
    Returns:
        bool: 移动是否成功
        
    Raises:
        FileOperationError: 移动失败
    """
    # 检查源文件
    if not os.path.exists(src):
        raise FileOperationError(f"源文件不存在: {src}")
        
    if not os.path.isfile(src):
        raise FileOperationError(f"源路径不是文件: {src}")
        
    # 检查目标文件
    if os.path.exists(dst):
        if os.path.isdir(dst):
            # 如果目标是目录，将源文件名添加到目标路径
            dst = os.path.join(dst, os.path.basename(src))
            
        if os.path.exists(dst) and not overwrite:
            raise FileOperationError(f"目标文件已存在: {dst}")
            
    # 确保目标文件的父目录存在
    ensure_directory(os.path.dirname(dst))
    
    try:
        shutil.move(src, dst)
        logger.debug(f"已移动文件: {src} -> {dst}")
        return True
    except Exception as e:
        raise FileOperationError(f"移动文件失败 '{src}' -> '{dst}': {str(e)}")