#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java代码搜索模块
用于在Java源代码中进行关键词搜索和模式匹配
"""

import os
import re
import fnmatch
from typing import List, Dict, Pattern, Optional, Set
from pathlib import Path


class JavaCodeSearcher:
    """
    Java代码搜索工具
    支持在Java文件中进行关键词搜索、正则表达式匹配等功能
    """
    
    def __init__(self, verbose: bool = False):
        """
        初始化代码搜索工具
        
        Args:
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self._java_extensions = ['.java']
    
    def log(self, message: str) -> None:
        """输出日志信息"""
        if self.verbose:
            print(f"[代码搜索器] {message}")
    
    def search_files(self, 
                    search_dir: str,
                    pattern: str,
                    is_regex: bool = False,
                    case_sensitive: bool = False,
                    recursive: bool = True,
                    file_pattern: str = '*.java') -> List[Dict]:
        """
        在指定目录中搜索文件
        
        Args:
            search_dir: 搜索目录
            pattern: 搜索模式，可以是关键词或正则表达式
            is_regex: pattern是否是正则表达式
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            file_pattern: 文件匹配模式
            
        Returns:
            搜索结果列表，每个结果包含文件名、行号和匹配内容
        """
        if not os.path.exists(search_dir):
            self.log(f"搜索目录不存在: {search_dir}")
            return []
        
        results = []
        
        # 编译正则表达式
        if is_regex:
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex_pattern = re.compile(pattern, flags)
            except re.error as e:
                self.log(f"无效的正则表达式: {e}")
                return []
        else:
            # 对于普通关键词搜索，转义正则特殊字符
            escaped_pattern = re.escape(pattern)
            flags = 0 if case_sensitive else re.IGNORECASE
            regex_pattern = re.compile(escaped_pattern, flags)
        
        self.log(f"开始搜索: 目录='{search_dir}', 模式='{pattern}', 正则={is_regex}, 大小写敏感={case_sensitive}")
        
        # 搜索文件
        if recursive:
            for root, _, files in os.walk(search_dir):
                for file in files:
                    if fnmatch.fnmatch(file, file_pattern):
                        file_path = os.path.join(root, file)
                        file_results = self._search_in_file(file_path, regex_pattern)
                        results.extend(file_results)
        else:
            for file in os.listdir(search_dir):
                file_path = os.path.join(search_dir, file)
                if os.path.isfile(file_path) and fnmatch.fnmatch(file, file_pattern):
                    file_results = self._search_in_file(file_path, regex_pattern)
                    results.extend(file_results)
        
        self.log(f"搜索完成: 找到{len(results)}个匹配项")
        return results
    
    def _search_in_file(self, file_path: str, pattern: Pattern) -> List[Dict]:
        """
        在单个文件中搜索
        
        Args:
            file_path: 文件路径
            pattern: 编译后的正则表达式
            
        Returns:
            搜索结果列表
        """
        results = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
            
            for line_num, line in enumerate(lines, 1):
                if pattern.search(line):
                    results.append({
                        'file': file_path,
                        'line': line_num,
                        'content': line.rstrip('\n\r')
                    })
                    
        except Exception as e:
            self.log(f"读取文件失败 '{file_path}': {e}")
        
        return results
    
    def search_class_definitions(self, 
                                search_dir: str,
                                class_name: str,
                                case_sensitive: bool = False,
                                recursive: bool = True) -> List[Dict]:
        """
        搜索类定义
        
        Args:
            search_dir: 搜索目录
            class_name: 类名，可以使用通配符
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            
        Returns:
            类定义搜索结果列表
        """
        # 将类名转换为正则表达式模式
        if '*' in class_name or '?' in class_name:
            # 对于包含通配符的类名，使用fnmatch转换为正则
            regex_pattern = fnmatch.translate(class_name)
        else:
            # 对于精确类名，创建匹配类定义的正则
            regex_pattern = r'\b(class|interface|enum)\s+' + re.escape(class_name) + r'\b'
        
        return self.search_files(
            search_dir=search_dir,
            pattern=regex_pattern,
            is_regex=True,
            case_sensitive=case_sensitive,
            recursive=recursive
        )
    
    def search_method_definitions(self, 
                                search_dir: str,
                                method_name: str,
                                case_sensitive: bool = False,
                                recursive: bool = True) -> List[Dict]:
        """
        搜索方法定义
        
        Args:
            search_dir: 搜索目录
            method_name: 方法名，可以使用通配符
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            
        Returns:
            方法定义搜索结果列表
        """
        # 将方法名转换为正则表达式模式
        if '*' in method_name or '?' in method_name:
            # 对于包含通配符的方法名，使用fnmatch转换为正则
            regex_pattern = fnmatch.translate(method_name) + r'\s*\([^)]*\)'
        else:
            # 对于精确方法名，创建匹配方法定义的正则
            regex_pattern = r'\b\w+\s+\b' + re.escape(method_name) + r'\b\s*\([^)]*\)'
        
        return self.search_files(
            search_dir=search_dir,
            pattern=regex_pattern,
            is_regex=True,
            case_sensitive=case_sensitive,
            recursive=recursive
        )
    
    def search_string_literals(self, 
                             search_dir: str,
                             string_pattern: str,
                             is_regex: bool = False,
                             case_sensitive: bool = False,
                             recursive: bool = True) -> List[Dict]:
        """
        搜索字符串字面量
        
        Args:
            search_dir: 搜索目录
            string_pattern: 字符串模式
            is_regex: string_pattern是否是正则表达式
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            
        Returns:
            字符串字面量搜索结果列表
        """
        # 匹配Java中的字符串字面量
        if is_regex:
            # 如果是正则表达式，需要确保它匹配的是字符串字面量内部的内容
            base_pattern = r'"([^"]*' + string_pattern + r'[^"]*)"'
        else:
            # 对于普通字符串，转义并搜索它在字符串字面量中的出现
            escaped_pattern = re.escape(string_pattern)
            base_pattern = r'"([^"]*' + escaped_pattern + r'[^"]*)"'
        
        return self.search_files(
            search_dir=search_dir,
            pattern=base_pattern,
            is_regex=True,
            case_sensitive=case_sensitive,
            recursive=recursive
        )
    
    def search_comments(self, 
                       search_dir: str,
                       pattern: str,
                       is_regex: bool = False,
                       case_sensitive: bool = False,
                       recursive: bool = True) -> List[Dict]:
        """
        搜索注释
        
        Args:
            search_dir: 搜索目录
            pattern: 搜索模式
            is_regex: pattern是否是正则表达式
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            
        Returns:
            注释搜索结果列表
        """
        # 匹配Java中的单行注释和多行注释
        if is_regex:
            # 对于正则表达式，需要构建匹配注释内容的模式
            single_line_pattern = r'//.*(' + pattern + r')'
            multi_line_pattern = r'/\*[\s\S]*?(' + pattern + r')[\s\S]*?\*/'
            full_pattern = f'{single_line_pattern}|{multi_line_pattern}'
        else:
            # 对于普通字符串，转义并搜索它在注释中的出现
            escaped_pattern = re.escape(pattern)
            single_line_pattern = r'//.*(' + escaped_pattern + r')'
            multi_line_pattern = r'/\*[\s\S]*?(' + escaped_pattern + r')[\s\S]*?\*/'
            full_pattern = f'{single_line_pattern}|{multi_line_pattern}'
        
        return self.search_files(
            search_dir=search_dir,
            pattern=full_pattern,
            is_regex=True,
            case_sensitive=case_sensitive,
            recursive=recursive
        )
    
    def count_occurrences(self, 
                         search_dir: str,
                         pattern: str,
                         is_regex: bool = False,
                         case_sensitive: bool = False,
                         recursive: bool = True,
                         file_pattern: str = '*.java') -> Dict[str, int]:
        """
        计算模式在文件中的出现次数
        
        Args:
            search_dir: 搜索目录
            pattern: 搜索模式
            is_regex: pattern是否是正则表达式
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索子目录
            file_pattern: 文件匹配模式
            
        Returns:
            包含每个文件中出现次数的字典
        """
        results = self.search_files(
            search_dir=search_dir,
            pattern=pattern,
            is_regex=is_regex,
            case_sensitive=case_sensitive,
            recursive=recursive,
            file_pattern=file_pattern
        )
        
        # 统计每个文件中的出现次数
        counts = {}
        for result in results:
            file_path = result['file']
            counts[file_path] = counts.get(file_path, 0) + 1
        
        return counts
    
    def format_search_results(self, results: List[Dict], max_lines: int = 10) -> str:
        """
        格式化搜索结果为可读字符串
        
        Args:
            results: 搜索结果列表
            max_lines: 显示的最大行数
            
        Returns:
            格式化的结果字符串
        """
        if not results:
            return "没有找到匹配项"
        
        formatted_lines = [f"找到{len(results)}个匹配项:"]
        
        # 按文件分组
        grouped_results = {}
        for result in results:
            file_path = result['file']
            if file_path not in grouped_results:
                grouped_results[file_path] = []
            grouped_results[file_path].append(result)
        
        # 格式化每个文件的结果
        total_lines = 0
        for file_path, file_results in grouped_results.items():
            formatted_lines.append(f"\n{file_path}:")
            
            for result in file_results:
                total_lines += 1
                if total_lines > max_lines:
                    formatted_lines.append(f"... 还有{len(results) - max_lines}个匹配项未显示")
                    return '\n'.join(formatted_lines)
                
                formatted_lines.append(f"  第{result['line']}行: {result['content']}")
        
        return '\n'.join(formatted_lines)