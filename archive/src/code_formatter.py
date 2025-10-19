#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java代码格式化模块
用于对反编译后的Java代码进行格式化和美化
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


class JavaCodeFormatter:
    """
    Java代码格式化工具
    支持多种格式化选项和自定义格式化规则
    """
    
    def __init__(self, 
                 verbose: bool = False,
                 formatter_jar_path: Optional[str] = None):
        """
        初始化代码格式化工具
        
        Args:
            verbose: 是否显示详细日志
            formatter_jar_path: 外部格式化工具JAR文件路径（可选）
        """
        self.verbose = verbose
        self.formatter_jar_path = formatter_jar_path
        self._default_java_style = {
            'indent_size': 4,
            'indent_char': ' ',
            'max_line_length': 120,
            'break_before_brace': 'function,class',
            'keep_array_indentation': False,
            'keep_function_indentation': False,
            'space_after_anon_function': True,
            'space_after_named_function': True
        }
    
    def log(self, message: str) -> None:
        """输出日志信息"""
        if self.verbose:
            print(f"[格式化器] {message}")
    
    def format_file(self, file_path: str, output_path: Optional[str] = None, 
                   style: Optional[dict] = None) -> bool:
        """
        格式化单个Java文件
        
        Args:
            file_path: 要格式化的Java文件路径
            output_path: 格式化后的输出文件路径，如果为None则覆盖原文件
            style: 格式化样式配置
            
        Returns:
            格式化是否成功
        """
        if not os.path.exists(file_path):
            self.log(f"文件不存在: {file_path}")
            return False
        
        if not file_path.endswith('.java'):
            self.log(f"不支持的文件类型: {file_path}")
            return False
        
        # 如果未指定输出路径，则覆盖原文件
        if output_path is None:
            output_path = file_path
        
        # 如果未指定样式，则使用默认样式
        if style is None:
            style = self._default_java_style
        
        try:
            # 读取原始文件内容
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # 使用Python进行基本格式化
            formatted_content = self._basic_format(content, style)
            
            # 写入格式化后的内容
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
            
            self.log(f"成功格式化文件: {file_path}")
            return True
            
        except Exception as e:
            self.log(f"格式化文件失败: {e}")
            return False
    
    def format_directory(self, dir_path: str, recursive: bool = True,
                        style: Optional[dict] = None) -> dict:
        """
        格式化目录中的所有Java文件
        
        Args:
            dir_path: 要处理的目录路径
            recursive: 是否递归处理子目录
            style: 格式化样式配置
            
        Returns:
            包含处理结果的字典，格式为 {'success': [], 'failed': []}
        """
        if not os.path.exists(dir_path):
            self.log(f"目录不存在: {dir_path}")
            return {'success': [], 'failed': []}
        
        result = {'success': [], 'failed': []}
        
        if recursive:
            # 递归遍历目录
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        if self.format_file(file_path, style=style):
                            result['success'].append(file_path)
                        else:
                            result['failed'].append(file_path)
        else:
            # 只处理当前目录
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path) and file.endswith('.java'):
                    if self.format_file(file_path, style=style):
                        result['success'].append(file_path)
                    else:
                        result['failed'].append(file_path)
        
        self.log(f"目录格式化完成: 成功{len(result['success'])}个，失败{len(result['failed'])}个")
        return result
    
    def _basic_format(self, content: str, style: dict) -> str:
        """
        使用Python进行基本的Java代码格式化
        
        Args:
            content: 原始代码内容
            style: 格式化样式配置
            
        Returns:
            格式化后的代码内容
        """
        # 分割成行
        lines = content.split('\n')
        formatted_lines = []
        
        # 获取缩进配置
        indent_size = style.get('indent_size', 4)
        indent_char = style.get('indent_char', ' ')
        indent_str = indent_char * indent_size
        
        # 当前缩进级别
        current_indent = 0
        
        for line in lines:
            # 去除行首尾空白
            stripped_line = line.strip()
            
            # 如果行为空，保持为空行
            if not stripped_line:
                formatted_lines.append('')
                continue
            
            # 处理缩进减少的情况（遇到 '}'）
            if stripped_line.startswith('}') or stripped_line.startswith('case') or stripped_line.startswith('default:'):
                current_indent = max(0, current_indent - 1)
            
            # 添加缩进
            indented_line = indent_str * current_indent + stripped_line
            formatted_lines.append(indented_line)
            
            # 处理缩进增加的情况（遇到 '{'）
            if stripped_line.endswith('{'):
                current_indent += 1
        
        # 组合成字符串
        return '\n'.join(formatted_lines)
    
    def create_style_config(self, **kwargs) -> dict:
        """
        创建格式化样式配置
        
        Args:
            **kwargs: 样式参数
            
        Returns:
            样式配置字典
        """
        style = self._default_java_style.copy()
        style.update(kwargs)
        return style