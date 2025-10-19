#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能分析器
提供代码执行时间测量和分析功能
"""

import time
import functools
from typing import Any, Callable, Dict, Optional, Union
import psutil


class Profiler:
    """
    性能分析器类
    用于测量代码块执行时间和资源使用情况
    """
    
    def __init__(self):
        """
        初始化性能分析器
        """
        self.records: Dict[str, Dict[str, Any]] = {}
        self.start_times: Dict[str, float] = {}
        self.process = psutil.Process()
    
    def start(self, label: str) -> None:
        """
        开始计时
        
        Args:
            label: 计时标签
        """
        # 记录开始时间和内存使用情况
        self.start_times[label] = time.time()
        
        # 初始化记录
        if label not in self.records:
            self.records[label] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float('inf'),
                "max_time": 0.0,
                "total_memory": 0,
                "avg_time": 0.0
            }
    
    def stop(self, label: str) -> float:
        """
        停止计时
        
        Args:
            label: 计时标签
            
        Returns:
            float: 执行时间（秒）
        """
        if label not in self.start_times:
            raise ValueError(f"未找到标签 '{label}' 的开始时间")
        
        # 计算执行时间
        elapsed_time = time.time() - self.start_times[label]
        
        # 更新记录
        record = self.records[label]
        record["count"] += 1
        record["total_time"] += elapsed_time
        record["min_time"] = min(record["min_time"], elapsed_time)
        record["max_time"] = max(record["max_time"], elapsed_time)
        record["avg_time"] = record["total_time"] / record["count"]
        
        # 尝试获取内存使用信息（可选）
        try:
            mem_info = self.process.memory_info()
            record["total_memory"] = max(record.get("total_memory", 0), mem_info.rss)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
        
        # 删除开始时间
        del self.start_times[label]
        
        return elapsed_time
    
    def reset(self, label: Optional[str] = None) -> None:
        """
        重置计时记录
        
        Args:
            label: 计时标签，如果为None则重置所有记录
        """
        if label is not None:
            if label in self.records:
                del self.records[label]
            if label in self.start_times:
                del self.start_times[label]
        else:
            self.records.clear()
            self.start_times.clear()
    
    def get_stats(self, label: Optional[str] = None) -> Dict[str, Any]:
        """
        获取计时统计信息
        
        Args:
            label: 计时标签，如果为None则返回所有标签的统计信息
            
        Returns:
            Dict[str, Any]: 统计信息
        """
        if label is not None:
            if label not in self.records:
                raise ValueError(f"未找到标签 '{label}' 的记录")
            return self.records[label].copy()
        else:
            return {k: v.copy() for k, v in self.records.items()}
    
    def __enter__(self) -> 'Profiler':
        """
        支持上下文管理器
        """
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文管理器时重置所有记录
        """
        self.reset()


class TimerContext:
    """
    计时器上下文管理器
    """
    
    def __init__(self, profiler: Profiler, label: str):
        """
        初始化计时器上下文
        
        Args:
            profiler: 性能分析器实例
            label: 计时标签
        """
        self.profiler = profiler
        self.label = label
        self.elapsed_time = 0.0
    
    def __enter__(self) -> 'TimerContext':
        """
        进入上下文时开始计时
        """
        self.profiler.start(self.label)
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文时停止计时
        """
        self.elapsed_time = self.profiler.stop(self.label)


def timing(label: Optional[str] = None):
    """
    性能计时装饰器
    
    Args:
        label: 计时标签，如果为None则使用函数名
        
    Returns:
        Callable: 装饰后的函数
    """
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # 初始化分析器（每个函数独立）
        func_profiler = Profiler()
        timer_label = label if label is not None else func.__name__
        
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # 使用上下文管理器计时
            with TimerContext(func_profiler, timer_label):
                result = func(*args, **kwargs)
            
            # 将性能统计附加到函数对象上，以便外部访问
            if not hasattr(wrapper, '_performance_stats'):
                wrapper._performance_stats = func_profiler.get_stats()
            else:
                wrapper._performance_stats = func_profiler.get_stats()
            
            return result
        
        # 添加重置统计的方法
        def reset_stats() -> None:
            """重置性能统计"""
            func_profiler.reset()
            if hasattr(wrapper, '_performance_stats'):
                delattr(wrapper, '_performance_stats')
        
        wrapper.reset_stats = reset_stats
        
        return wrapper
    
    return decorator