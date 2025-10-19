#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
性能分析器实现
用于监控和分析反编译过程的性能
"""

import time
import json
import os
import psutil
from typing import Dict, List, Optional, Any
from datetime import datetime

from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)

# 性能统计数据
_performance_stats: Dict[str, List[Dict[str, Any]]] = {}

# 是否启用性能分析
_performance_enabled = False

def enable_performance_tracking(enable: bool = True) -> None:
    """
    启用或禁用性能跟踪
    
    Args:
        enable: 是否启用性能跟踪
    """
    global _performance_enabled
    _performance_enabled = enable
    logger.info(f"性能跟踪已{'启用' if enable else '禁用'}")

def is_performance_tracking_enabled() -> bool:
    """
    检查性能跟踪是否启用
    
    Returns:
        bool: 是否启用性能跟踪
    """
    return _performance_enabled

def profile_decompilation(engine_name: str, input_file: str,
                         decompile_func, *args, **kwargs) -> Any:
    """
    分析反编译函数的性能
    
    Args:
        engine_name: 引擎名称
        input_file: 输入文件路径
        decompile_func: 反编译函数
        *args: 函数参数
        **kwargs: 关键字参数
        
    Returns:
        Any: 反编译函数的返回值
    """
    # 如果未启用性能跟踪，直接执行函数
    if not _performance_enabled:
        return decompile_func(*args, **kwargs)
    
    # 初始化引擎的统计数据列表
    if engine_name not in _performance_stats:
        _performance_stats[engine_name] = []
    
    # 记录开始时间和内存
    start_time = time.time()
    start_memory = _get_current_memory_usage()
    
    try:
        # 执行反编译函数
        result = decompile_func(*args, **kwargs)
        
        # 记录结束时间和内存
        end_time = time.time()
        end_memory = _get_current_memory_usage()
        
        # 计算性能指标
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        # 记录性能数据
        performance_data = {
            'timestamp': datetime.now().isoformat(),
            'input_file': os.path.basename(input_file),
            'duration_seconds': round(duration, 3),
            'memory_mb': round(memory_used / (1024 * 1024), 2),
            'success': True,
            'error_message': None
        }
        
        _performance_stats[engine_name].append(performance_data)
        logger.debug(f"反编译性能数据 - 引擎: {engine_name}, 文件: {input_file}, "  
                    f"耗时: {duration:.3f}秒, 内存: {memory_used/(1024*1024):.2f}MB")
        
        return result
        
    except Exception as e:
        # 记录异常情况下的性能数据
        end_time = time.time()
        end_memory = _get_current_memory_usage()
        
        duration = end_time - start_time
        memory_used = end_memory - start_memory
        
        performance_data = {
            'timestamp': datetime.now().isoformat(),
            'input_file': os.path.basename(input_file),
            'duration_seconds': round(duration, 3),
            'memory_mb': round(memory_used / (1024 * 1024), 2),
            'success': False,
            'error_message': str(e)
        }
        
        _performance_stats[engine_name].append(performance_data)
        logger.debug(f"反编译性能数据(失败) - 引擎: {engine_name}, 文件: {input_file}, "  
                    f"耗时: {duration:.3f}秒, 内存: {memory_used/(1024*1024):.2f}MB")
        
        raise

def get_performance_stats(engine_name: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]:
    """
    获取性能统计数据
    
    Args:
        engine_name: 可选的引擎名称，如果指定则只返回该引擎的数据
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: 性能统计数据
    """
    if engine_name:
        return {
            engine_name: _performance_stats.get(engine_name, [])
        }
    return _performance_stats.copy()

def reset_performance_stats(engine_name: Optional[str] = None) -> None:
    """
    重置性能统计数据
    
    Args:
        engine_name: 可选的引擎名称，如果指定则只重置该引擎的数据
    """
    if engine_name:
        if engine_name in _performance_stats:
            _performance_stats[engine_name] = []
            logger.info(f"已重置引擎 {engine_name} 的性能统计数据")
    else:
        _performance_stats.clear()
        logger.info("已重置所有性能统计数据")

def save_performance_report(output_file: str) -> None:
    """
    保存性能报告到文件
    
    Args:
        output_file: 输出文件路径
    """
    if not _performance_stats:
        logger.warning("没有性能统计数据可保存")
        return
    
    # 计算汇总统计信息
    report_data = {
        'generated_at': datetime.now().isoformat(),
        'total_engines': len(_performance_stats),
        'summary': {},
        'detailed_data': _performance_stats
    }
    
    # 为每个引擎计算汇总数据
    for engine_name, records in _performance_stats.items():
        if not records:
            continue
            
        # 计算成功和失败的数量
        success_count = sum(1 for r in records if r['success'])
        failure_count = len(records) - success_count
        
        # 计算平均、最大、最小时间
        durations = [r['duration_seconds'] for r in records]
        avg_duration = sum(durations) / len(durations) if durations else 0
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        
        # 计算平均、最大、最小内存
        memories = [r['memory_mb'] for r in records]
        avg_memory = sum(memories) / len(memories) if memories else 0
        max_memory = max(memories) if memories else 0
        min_memory = min(memories) if memories else 0
        
        report_data['summary'][engine_name] = {
            'total_runs': len(records),
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': (success_count / len(records)) * 100 if records else 0,
            'avg_duration_seconds': round(avg_duration, 3),
            'max_duration_seconds': round(max_duration, 3),
            'min_duration_seconds': round(min_duration, 3),
            'avg_memory_mb': round(avg_memory, 2),
            'max_memory_mb': round(max_memory, 2),
            'min_memory_mb': round(min_memory, 2)
        }
    
    try:
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存到JSON文件
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"性能报告已保存到: {output_file}")
        
    except Exception as e:
        logger.error(f"保存性能报告失败: {str(e)}")

def compare_engines_performance() -> Dict[str, Any]:
    """
    比较不同引擎的性能
    
    Returns:
        Dict[str, Any]: 比较结果
    """
    if len(_performance_stats) < 2:
        logger.warning("至少需要两个引擎的性能数据才能进行比较")
        return {}
    
    comparison_results = {
        'fastest_engine': None,
        'most_memory_efficient': None,
        'highest_success_rate': None,
        'engine_details': {}
    }
    
    # 初始化最佳值
    best_duration = float('inf')
    best_memory = float('inf')
    best_success_rate = 0
    
    # 计算每个引擎的统计数据
    for engine_name, records in _performance_stats.items():
        if not records:
            continue
            
        # 计算成功和失败的数量
        success_count = sum(1 for r in records if r['success'])
        failure_count = len(records) - success_count
        success_rate = (success_count / len(records)) * 100 if records else 0
        
        # 计算平均时间和内存
        durations = [r['duration_seconds'] for r in records]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        memories = [r['memory_mb'] for r in records]
        avg_memory = sum(memories) / len(memories) if memories else 0
        
        # 保存引擎详情
        comparison_results['engine_details'][engine_name] = {
            'total_runs': len(records),
            'success_count': success_count,
            'failure_count': failure_count,
            'success_rate': round(success_rate, 2),
            'avg_duration_seconds': round(avg_duration, 3),
            'avg_memory_mb': round(avg_memory, 2)
        }
        
        # 更新最佳引擎
        if avg_duration < best_duration:
            best_duration = avg_duration
            comparison_results['fastest_engine'] = engine_name
            
        if avg_memory < best_memory:
            best_memory = avg_memory
            comparison_results['most_memory_efficient'] = engine_name
            
        if success_rate > best_success_rate:
            best_success_rate = success_rate
            comparison_results['highest_success_rate'] = engine_name
    
    logger.info(f"引擎性能比较结果: 最快引擎={comparison_results['fastest_engine']}, "  
                f"内存效率最高={comparison_results['most_memory_efficient']}, "  
                f"成功率最高={comparison_results['highest_success_rate']}")
    
    return comparison_results

def _get_current_memory_usage() -> int:
    """
    获取当前进程的内存使用量（字节）
    
    Returns:
        int: 内存使用量（字节）
    """
    try:
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return memory_info.rss  # 返回物理内存使用量
    except (ImportError, AttributeError):
        # 如果psutil不可用，返回0
        return 0

# 默认启用性能分析
enable_performance_tracking(True)