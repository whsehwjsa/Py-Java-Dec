#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Java代码依赖分析模块
用于分析Java代码中的类依赖关系、导入语句等
"""

import os
import re
import networkx as nx
import matplotlib.pyplot as plt
from typing import Dict, List, Set, Tuple, Optional
from pathlib import Path


class JavaDependencyAnalyzer:
    """
    Java代码依赖分析工具
    可以分析Java源代码中的类依赖关系，并生成依赖图
    """
    
    def __init__(self, verbose: bool = False):
        """
        初始化依赖分析工具
        
        Args:
            verbose: 是否显示详细日志
        """
        self.verbose = verbose
        self._import_pattern = re.compile(r'^\s*import\s+(static\s+)?([\w\.]+(\*|\.\w+))\s*;\s*$')
        self._package_pattern = re.compile(r'^\s*package\s+([\w\.]+)\s*;\s*$')
        self._class_pattern = re.compile(r'^\s*(?:public\s+|private\s+|protected\s+|static\s+)*class\s+(\w+)')
        self._interface_pattern = re.compile(r'^\s*(?:public\s+|private\s+|protected\s+|static\s+)*interface\s+(\w+)')
    
    def log(self, message: str) -> None:
        """输出日志信息"""
        if self.verbose:
            print(f"[依赖分析器] {message}")
    
    def analyze_file(self, file_path: str) -> Dict:
        """
        分析单个Java文件的依赖关系
        
        Args:
            file_path: Java文件路径
            
        Returns:
            包含分析结果的字典，格式为：
            {
                'file': 文件路径,
                'package': 包名,
                'classes': [类名列表],
                'interfaces': [接口名列表],
                'imports': [导入列表],
                'static_imports': [静态导入列表]
            }
        """
        if not os.path.exists(file_path):
            self.log(f"文件不存在: {file_path}")
            return {}
        
        if not file_path.endswith('.java'):
            self.log(f"不支持的文件类型: {file_path}")
            return {}
        
        result = {
            'file': file_path,
            'package': None,
            'classes': [],
            'interfaces': [],
            'imports': [],
            'static_imports': []
        }
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.readlines()
            
            for line in content:
                # 匹配包声明
                package_match = self._package_pattern.match(line)
                if package_match:
                    result['package'] = package_match.group(1)
                    
                # 匹配导入声明
                import_match = self._import_pattern.match(line)
                if import_match:
                    is_static = import_match.group(1) is not None
                    import_path = import_match.group(2)
                    
                    if is_static:
                        result['static_imports'].append(import_path)
                    else:
                        result['imports'].append(import_path)
                
                # 匹配类声明
                class_match = self._class_pattern.match(line)
                if class_match:
                    result['classes'].append(class_match.group(1))
                
                # 匹配接口声明
                interface_match = self._interface_pattern.match(line)
                if interface_match:
                    result['interfaces'].append(interface_match.group(1))
                    
            self.log(f"成功分析文件: {file_path}, 找到{len(result['classes'])}个类, {len(result['interfaces'])}个接口")
            return result
            
        except Exception as e:
            self.log(f"分析文件失败: {e}")
            return {}
    
    def analyze_directory(self, dir_path: str, recursive: bool = True) -> List[Dict]:
        """
        分析目录中的所有Java文件
        
        Args:
            dir_path: 目录路径
            recursive: 是否递归处理子目录
            
        Returns:
            包含所有文件分析结果的列表
        """
        if not os.path.exists(dir_path):
            self.log(f"目录不存在: {dir_path}")
            return []
        
        results = []
        
        if recursive:
            # 递归遍历目录
            for root, _, files in os.walk(dir_path):
                for file in files:
                    if file.endswith('.java'):
                        file_path = os.path.join(root, file)
                        analysis = self.analyze_file(file_path)
                        if analysis:
                            results.append(analysis)
        else:
            # 只处理当前目录
            for file in os.listdir(dir_path):
                file_path = os.path.join(dir_path, file)
                if os.path.isfile(file_path) and file.endswith('.java'):
                    analysis = self.analyze_file(file_path)
                    if analysis:
                        results.append(analysis)
        
        self.log(f"目录分析完成: 共分析{len(results)}个Java文件")
        return results
    
    def build_dependency_graph(self, analysis_results: List[Dict]) -> nx.DiGraph:
        """
        根据分析结果构建依赖图
        
        Args:
            analysis_results: 分析结果列表
            
        Returns:
            依赖关系有向图 (networkx.DiGraph)
        """
        graph = nx.DiGraph()
        
        # 为每个类和接口创建节点
        for result in analysis_results:
            package = result.get('package', '')
            
            # 添加类节点
            for class_name in result.get('classes', []):
                full_name = f"{package}.{class_name}" if package else class_name
                graph.add_node(full_name, type='class', file=result['file'])
            
            # 添加接口节点
            for interface_name in result.get('interfaces', []):
                full_name = f"{package}.{interface_name}" if package else interface_name
                graph.add_node(full_name, type='interface', file=result['file'])
        
        # 创建依赖边
        for result in analysis_results:
            package = result.get('package', '')
            current_classes = result.get('classes', [])
            current_interfaces = result.get('interfaces', [])
            all_imports = result.get('imports', [])
            
            # 为当前文件中的每个类/接口添加到导入的依赖边
            for import_path in all_imports:
                # 处理通配符导入
                if '*' in import_path:
                    import_base = import_path[:-1]  # 移除 '*'
                    # 查找匹配的类和接口
                    for node in graph.nodes():
                        if node.startswith(import_base) and node != import_base:
                            # 为当前文件中的每个类/接口添加边
                            for class_name in current_classes:
                                source = f"{package}.{class_name}" if package else class_name
                                if source in graph.nodes():
                                    graph.add_edge(source, node)
                            for interface_name in current_interfaces:
                                source = f"{package}.{interface_name}" if package else interface_name
                                if source in graph.nodes():
                                    graph.add_edge(source, node)
                else:
                    # 精确导入
                    imported_class = import_path.split('.')[-1]
                    # 为当前文件中的每个类/接口添加边
                    for class_name in current_classes:
                        source = f"{package}.{class_name}" if package else class_name
                        if source in graph.nodes() and import_path in graph.nodes():
                            graph.add_edge(source, import_path)
                    for interface_name in current_interfaces:
                        source = f"{package}.{interface_name}" if package else interface_name
                        if source in graph.nodes() and import_path in graph.nodes():
                            graph.add_edge(source, import_path)
        
        self.log(f"依赖图构建完成: {len(graph.nodes())}个节点, {len(graph.edges())}条边")
        return graph
    
    def visualize_dependency_graph(self, graph: nx.DiGraph, output_file: Optional[str] = None) -> None:
        """
        可视化依赖图
        
        Args:
            graph: 依赖关系图
            output_file: 输出文件路径，如果为None则直接显示
        """
        try:
            plt.figure(figsize=(12, 12))
            
            # 使用spring布局算法
            pos = nx.spring_layout(graph, k=0.15, iterations=20)
            
            # 按类型设置节点颜色
            colors = []
            for node in graph.nodes():
                node_type = graph.nodes[node].get('type', 'class')
                colors.append('lightblue' if node_type == 'class' else 'lightgreen')
            
            # 绘制图形
            nx.draw_networkx_nodes(graph, pos, node_size=500, node_color=colors, alpha=0.8)
            nx.draw_networkx_edges(graph, pos, width=1.0, alpha=0.5, arrowsize=20)
            nx.draw_networkx_labels(graph, pos, font_size=8, font_weight='bold')
            
            plt.title('Java Class Dependency Graph')
            plt.axis('off')
            
            if output_file:
                plt.savefig(output_file, format='png', dpi=300, bbox_inches='tight')
                self.log(f"依赖图已保存到: {output_file}")
            else:
                plt.show()
                
        except Exception as e:
            self.log(f"可视化依赖图失败: {e}")
    
    def find_cycles(self, graph: nx.DiGraph) -> List[List[str]]:
        """
        查找依赖图中的循环依赖
        
        Args:
            graph: 依赖关系图
            
        Returns:
            循环依赖列表
        """
        try:
            cycles = list(nx.simple_cycles(graph))
            self.log(f"找到{len(cycles)}个循环依赖")
            return cycles
        except Exception as e:
            self.log(f"查找循环依赖失败: {e}")
            return []
    
    def find_unused_imports(self, analysis_result: Dict) -> List[str]:
        """
        查找未使用的导入
        
        Args:
            analysis_result: 单个文件的分析结果
            
        Returns:
            未使用的导入列表
        """
        # 这是一个简化实现，实际使用可能需要更复杂的代码解析
        # 这里我们只是检查导入的类名是否在文件内容中出现
        try:
            with open(analysis_result['file'], 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            unused_imports = []
            for import_path in analysis_result.get('imports', []):
                # 跳过通配符导入的检查
                if '*' in import_path:
                    continue
                
                # 获取导入的类名
                class_name = import_path.split('.')[-1]
                
                # 简单检查类名是否在文件内容中出现
                # 注意：这不是一个完美的方法，可能会有误报
                if class_name not in content:
                    unused_imports.append(import_path)
            
            self.log(f"找到{len(unused_imports)}个未使用的导入")
            return unused_imports
            
        except Exception as e:
            self.log(f"查找未使用的导入失败: {e}")
            return []