#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java反编译工具包 - 综合工具模块
整合代码格式化、依赖分析和代码搜索等功能
"""

import os
from typing import Dict, List, Optional, Union
from pathlib import Path

# 导入反编译引擎
from cfr import CFRDecompiler
from fernflower import FernFlowerDecompiler
from jadx import JADXDecompiler

# 导入新增的工具模块
try:
    from code_formatter import JavaCodeFormatter
except ImportError:
    JavaCodeFormatter = None

try:
    from dependency_analyzer import JavaDependencyAnalyzer
except ImportError:
    JavaDependencyAnalyzer = None

try:
    from code_searcher import JavaCodeSearcher
except ImportError:
    JavaCodeSearcher = None


class JavaDecompilerTools:
    """
    Java反编译综合工具类
    整合反编译、代码格式化、依赖分析和代码搜索等功能
    """
    
    def __init__(self, verbose: bool = False):
        """
        初始化综合工具类
        
        Args:
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self._decompilers = {
            'cfr': CFRDecompiler,
            'fernflower': FernFlowerDecompiler,
            'jadx': JADXDecompiler
        }
        
        # 初始化工具实例
        self.code_formatter = JavaCodeFormatter(verbose=verbose) if JavaCodeFormatter else None
        self.dependency_analyzer = JavaDependencyAnalyzer(verbose=verbose) if JavaDependencyAnalyzer else None
        self.code_searcher = JavaCodeSearcher(verbose=verbose) if JavaCodeSearcher else None
    
    def log(self, message: str) -> None:
        """输出日志信息"""
        if self.verbose:
            print(f"[综合工具] {message}")
    
    def decompile_with_formatting(self, 
                                input_path: str,
                                output_dir: str,
                                engine: str = 'fernflower',
                                format_code: bool = True,
                                format_style: Optional[Dict] = None,
                                **decompiler_kwargs) -> bool:
        """
        反编译文件并可选地格式化代码
        
        Args:
            input_path: 输入文件路径 (class或jar)
            output_dir: 输出目录
            engine: 反编译引擎 ('cfr', 'fernflower', 'jadx')
            format_code: 是否格式化反编译后的代码
            format_style: 格式化样式配置
            **decompiler_kwargs: 传递给反编译引擎的参数
            
        Returns:
            操作是否成功
        """
        if engine not in self._decompilers:
            self.log(f"不支持的反编译引擎: {engine}")
            return False
        
        # 创建反编译引擎实例
        decompiler = self._decompilers[engine](verbose=self.verbose, **decompiler_kwargs)
        
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        self.log(f"开始使用{engine}引擎反编译: {input_path} -> {output_dir}")
        
        # 执行反编译
        success = False
        if input_path.lower().endswith('.jar'):
            success = decompiler.decompile_single_jar(input_path, output_dir)
        elif input_path.lower().endswith('.class'):
            success = decompiler.decompile_single_class(input_path, output_dir)
        else:
            self.log(f"不支持的文件类型: {input_path}")
            return False
        
        # 如果反编译成功且需要格式化代码
        if success and format_code and self.code_formatter:
            self.log(f"开始格式化反编译后的代码")
            format_result = self.code_formatter.format_directory(output_dir, recursive=True, style=format_style)
            self.log(f"代码格式化完成: 成功{len(format_result['success'])}个，失败{len(format_result['failed'])}个")
        
        return success
    
    def analyze_dependencies(self, 
                           input_path: str,
                           output_graph: Optional[str] = None,
                           analyze_before_decompile: bool = False,
                           engine: str = 'fernflower',
                           **decompiler_kwargs) -> Optional[dict]:
        """
        分析Java代码的依赖关系
        
        Args:
            input_path: 输入文件或目录路径 (class, jar或Java源代码目录)
            output_graph: 依赖图输出文件路径
            analyze_before_decompile: 是否先反编译再分析（对于class或jar文件）
            engine: 反编译引擎
            **decompiler_kwargs: 传递给反编译引擎的参数
            
        Returns:
            包含分析结果的字典，如果失败则返回None
        """
        if not self.dependency_analyzer:
            self.log("依赖分析器未初始化")
            return None
        
        # 需要反编译的情况
        if (input_path.lower().endswith('.class') or input_path.lower().endswith('.jar')) and analyze_before_decompile:
            # 创建临时目录用于反编译
            temp_dir = os.path.join(os.path.dirname(input_path), 'temp_analysis')
            os.makedirs(temp_dir, exist_ok=True)
            
            # 反编译文件
            success = self.decompile_with_formatting(input_path, temp_dir, engine=engine, format_code=False, **decompiler_kwargs)
            if not success:
                self.log("反编译失败，无法进行依赖分析")
                return None
            
            # 使用反编译后的目录进行分析
            analyze_dir = temp_dir
        else:
            # 直接分析目录
            analyze_dir = input_path
        
        # 检查是否为目录
        if not os.path.isdir(analyze_dir):
            self.log(f"分析路径必须是目录: {analyze_dir}")
            return None
        
        self.log(f"开始分析依赖关系: {analyze_dir}")
        
        # 执行依赖分析
        analysis_results = self.dependency_analyzer.analyze_directory(analyze_dir)
        
        # 构建依赖图
        if analysis_results:
            graph = self.dependency_analyzer.build_dependency_graph(analysis_results)
            
            # 查找循环依赖
            cycles = self.dependency_analyzer.find_cycles(graph)
            
            # 可视化依赖图
            if output_graph:
                self.dependency_analyzer.visualize_dependency_graph(graph, output_graph)
            
            # 统计信息
            stats = {
                'total_files': len(analysis_results),
                'total_classes': sum(len(r.get('classes', [])) for r in analysis_results),
                'total_interfaces': sum(len(r.get('interfaces', [])) for r in analysis_results),
                'total_nodes': len(graph.nodes()),
                'total_edges': len(graph.edges()),
                'cyclic_dependencies': len(cycles),
                'cycles': cycles
            }
            
            self.log(f"依赖分析完成: {stats}")
            return stats
        
        return None
    
    def search_code(self, 
                   search_dir: str,
                   pattern: str,
                   is_regex: bool = False,
                   case_sensitive: bool = False,
                   recursive: bool = True,
                   search_type: str = 'all') -> List[Dict]:
        """
        搜索代码
        
        Args:
            search_dir: 搜索目录
            pattern: 搜索模式
            is_regex: 是否使用正则表达式
            case_sensitive: 是否区分大小写
            recursive: 是否递归搜索
            search_type: 搜索类型 ('all', 'class', 'method', 'string', 'comment')
            
        Returns:
            搜索结果列表
        """
        if not self.code_searcher:
            self.log("代码搜索器未初始化")
            return []
        
        self.log(f"开始搜索代码: 模式='{pattern}', 类型='{search_type}'")
        
        # 根据搜索类型调用不同的方法
        if search_type == 'class':
            return self.code_searcher.search_class_definitions(
                search_dir=search_dir,
                class_name=pattern,
                case_sensitive=case_sensitive,
                recursive=recursive
            )
        elif search_type == 'method':
            return self.code_searcher.search_method_definitions(
                search_dir=search_dir,
                method_name=pattern,
                case_sensitive=case_sensitive,
                recursive=recursive
            )
        elif search_type == 'string':
            return self.code_searcher.search_string_literals(
                search_dir=search_dir,
                string_pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
                recursive=recursive
            )
        elif search_type == 'comment':
            return self.code_searcher.search_comments(
                search_dir=search_dir,
                pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
                recursive=recursive
            )
        else:  # 'all' 或其他
            return self.code_searcher.search_files(
                search_dir=search_dir,
                pattern=pattern,
                is_regex=is_regex,
                case_sensitive=case_sensitive,
                recursive=recursive
            )
    
    def batch_process(self, 
                     tasks: List[Dict],
                     max_workers: int = 4) -> List[Dict]:
        """
        批量处理多个任务
        
        Args:
            tasks: 任务列表，每个任务是一个字典，包含必要的参数
            max_workers: 最大工作线程数
            
        Returns:
            任务执行结果列表
        """
        import concurrent.futures
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            future_to_task = {}
            for task in tasks:
                task_type = task.get('type', 'decompile')
                
                if task_type == 'decompile':
                    future = executor.submit(
                        self.decompile_with_formatting,
                        input_path=task.get('input_path'),
                        output_dir=task.get('output_dir'),
                        engine=task.get('engine', 'fernflower'),
                        format_code=task.get('format_code', True),
                        format_style=task.get('format_style'),
                        **{k: v for k, v in task.items() if k not in ['type', 'input_path', 'output_dir', 'engine', 'format_code', 'format_style']}
                    )
                elif task_type == 'format':
                    if self.code_formatter:
                        future = executor.submit(
                            self.code_formatter.format_directory,
                            dir_path=task.get('dir_path'),
                            recursive=task.get('recursive', True),
                            style=task.get('style')
                        )
                    else:
                        results.append({'task': task, 'success': False, 'error': '格式化工具未初始化'})
                        continue
                else:
                    results.append({'task': task, 'success': False, 'error': f'不支持的任务类型: {task_type}'})
                    continue
                
                future_to_task[future] = task
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_task):
                task = future_to_task[future]
                try:
                    result = future.result()
                    results.append({'task': task, 'success': True, 'result': result})
                except Exception as e:
                    results.append({'task': task, 'success': False, 'error': str(e)})
        
        return results
    
    def get_available_engines(self) -> List[str]:
        """
        获取所有可用的反编译引擎
        
        Returns:
            引擎名称列表
        """
        return list(self._decompilers.keys())
    
    def get_available_tools(self) -> Dict[str, bool]:
        """
        获取所有可用的工具状态
        
        Returns:
            工具可用性字典
        """
        return {
            'code_formatter': self.code_formatter is not None,
            'dependency_analyzer': self.dependency_analyzer is not None,
            'code_searcher': self.code_searcher is not None
        }