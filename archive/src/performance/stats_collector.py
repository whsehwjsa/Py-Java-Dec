#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
统计收集器
收集和管理反编译过程的统计数据
"""

import threading
import time
from typing import Any, Dict, List, Optional, Union


class StatsCollector:
    """
    统计数据收集器
    线程安全地收集和管理统计数据
    """
    
    def __init__(self):
        """
        初始化统计收集器
        """
        self._stats: Dict[str, Union[int, float, str, List[Any], Dict[str, Any]]] = {}
        self._lock = threading.RLock()  # 使用可重入锁
        self._start_time = time.time()
    
    def add(self, key: str, value: Union[int, float]) -> None:
        """
        增加指定键的数值
        
        Args:
            key: 统计键名
            value: 要增加的值
        """
        with self._lock:
            if key not in self._stats:
                self._stats[key] = 0
            self._stats[key] += value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置指定键的值
        
        Args:
            key: 统计键名
            value: 要设置的值
        """
        with self._lock:
            self._stats[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取指定键的值
        
        Args:
            key: 统计键名
            default: 默认值，当键不存在时返回
            
        Returns:
            Any: 键对应的值或默认值
        """
        with self._lock:
            return self._stats.get(key, default)
    
    def increment(self, key: str, step: int = 1) -> None:
        """
        递增指定键的值
        
        Args:
            key: 统计键名
            step: 递增量，默认为1
        """
        self.add(key, step)
    
    def append(self, key: str, value: Any) -> None:
        """
        向列表类型的键添加值
        
        Args:
            key: 统计键名
            value: 要添加的值
        """
        with self._lock:
            if key not in self._stats:
                self._stats[key] = []
            elif not isinstance(self._stats[key], list):
                raise TypeError(f"键 '{key}' 的值不是列表类型")
            self._stats[key].append(value)
    
    def update_dict(self, key: str, update_dict: Dict[str, Any]) -> None:
        """
        更新字典类型的键
        
        Args:
            key: 统计键名
            update_dict: 要更新的字典
        """
        with self._lock:
            if key not in self._stats:
                self._stats[key] = {}
            elif not isinstance(self._stats[key], dict):
                raise TypeError(f"键 '{key}' 的值不是字典类型")
            self._stats[key].update(update_dict)
    
    def record_success(self, file_path: str) -> None:
        """
        记录成功反编译的文件
        
        Args:
            file_path: 文件路径
        """
        self.increment('successful_files')
        self.append('processed_files', file_path)
    
    def record_failure(self, file_path: str, error_msg: str) -> None:
        """
        记录反编译失败的文件
        
        Args:
            file_path: 文件路径
            error_msg: 错误信息
        """
        self.increment('failed_files')
        self.append('failed_details', {'file': file_path, 'error': error_msg})
    
    def record_time(self, operation: str, duration: float) -> None:
        """
        记录操作时间
        
        Args:
            operation: 操作名称
            duration: 持续时间（秒）
        """
        time_key = f'time_{operation}'
        count_key = f'count_{operation}'
        
        with self._lock:
            # 记录总时间
            self.add(time_key, duration)
            # 记录操作次数
            self.increment(count_key)
            
            # 计算平均时间
            total_time = self._stats.get(time_key, 0)
            count = self._stats.get(count_key, 1)
            self._stats[f'avg_time_{operation}'] = total_time / count
    
    def get_duration(self) -> float:
        """
        获取自收集器创建以来的时间
        
        Returns:
            float: 经过的时间（秒）
        """
        return time.time() - self._start_time
    
    def get_summary(self) -> Dict[str, Any]:
        """
        获取统计摘要
        
        Returns:
            Dict[str, Any]: 统计摘要字典
        """
        with self._lock:
            summary = self._stats.copy()
            
            # 添加总处理时间
            summary['total_duration'] = self.get_duration()
            
            # 添加总文件数和成功率
            successful = summary.get('successful_files', 0)
            failed = summary.get('failed_files', 0)
            total = successful + failed
            
            summary['total_files'] = total
            if total > 0:
                summary['success_rate'] = (successful / total) * 100
            else:
                summary['success_rate'] = 0
            
            return summary
    
    def clear(self) -> None:
        """
        清空所有统计数据
        """
        with self._lock:
            self._stats.clear()
            self._start_time = time.time()
    
    def __str__(self) -> str:
        """
        返回统计信息的字符串表示
        
        Returns:
            str: 统计信息字符串
        """
        summary = self.get_summary()
        lines = ["统计摘要:"]
        
        # 格式化常见统计项
        for key, value in summary.items():
            if key == 'successful_files':
                lines.append(f"成功反编译文件数: {value}")
            elif key == 'failed_files':
                lines.append(f"失败文件数: {value}")
            elif key == 'total_files':
                lines.append(f"总文件数: {value}")
            elif key == 'success_rate':
                lines.append(f"成功率: {value:.2f}%")
            elif key == 'total_duration':
                lines.append(f"总耗时: {value:.2f}秒")
        
        # 添加自定义统计项
        custom_stats = [
            (k, v) for k, v in summary.items() 
            if k not in ['successful_files', 'failed_files', 'total_files', 
                        'success_rate', 'total_duration', 'processed_files', 
                        'failed_details']
        ]
        
        if custom_stats:
            lines.append("\n其他统计:")
            for key, value in custom_stats:
                # 格式化数值
                if isinstance(value, float):
                    value_str = f"{value:.4f}"
                else:
                    value_str = str(value)
                lines.append(f"{key}: {value_str}")
        
        return "\n".join(lines)
    
    def get_all_stats(self) -> Dict[str, Any]:
        """
        获取所有统计数据的副本
        
        Returns:
            Dict[str, Any]: 统计数据字典副本
        """
        with self._lock:
            return self._stats.copy()