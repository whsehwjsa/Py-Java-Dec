#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务运行器
管理和执行反编译任务，支持并行处理
"""

import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from .thread_pool import ThreadPool
from ..file_utils.file_handler import ensure_directory
from ..logger.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """
    任务状态枚举
    """
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class TaskResult:
    """
    任务结果数据类
    """
    task_id: str
    status: TaskStatus
    input_file: str
    output_file: Optional[str] = None
    error: Optional[str] = None
    elapsed_time: float = 0.0
    result: Optional[Any] = None


class TaskRunner:
    """
    任务运行器
    管理反编译任务的执行
    """
    
    def __init__(self, max_workers: int = 4, timeout: int = 300):
        """
        初始化任务运行器
        
        Args:
            max_workers: 最大工作线程数
            timeout: 任务超时时间（秒）
        """
        self.max_workers = max_workers
        self.timeout = timeout
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.next_task_id = 0
        self.task_lock = None
    
    def add_task(
        self,
        func: Callable[..., Any],
        input_file: str,
        output_dir: str,
        **kwargs: Any
    ) -> str:
        """
        添加任务到队列
        
        Args:
            func: 要执行的函数
            input_file: 输入文件路径
            output_dir: 输出目录
            **kwargs: 传递给函数的额外参数
            
        Returns:
            str: 任务ID
        """
        task_id = f"task_{self.next_task_id}"
        self.next_task_id += 1
        
        # 确保输出目录存在
        ensure_directory(output_dir)
        
        self.tasks[task_id] = {
            "func": func,
            "input_file": input_file,
            "output_dir": output_dir,
            "kwargs": kwargs,
            "status": TaskStatus.PENDING
        }
        
        return task_id
    
    def execute_task(self, task_id: str) -> TaskResult:
        """
        执行单个任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            TaskResult: 任务结果
        """
        if task_id not in self.tasks:
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                input_file="unknown",
                error="任务不存在"
            )
        
        task = self.tasks[task_id]
        task["status"] = TaskStatus.RUNNING
        start_time = time.time()
        
        try:
            # 执行任务函数
            result = task["func"](
                task["input_file"],
                task["output_dir"],
                **task["kwargs"]
            )
            
            elapsed_time = time.time() - start_time
            task["status"] = TaskStatus.COMPLETED
            
            # 处理函数返回的输出文件路径
            output_file = None
            if isinstance(result, str):
                output_file = result
            elif isinstance(result, dict) and "output_file" in result:
                output_file = result["output_file"]
            
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.COMPLETED,
                input_file=task["input_file"],
                output_file=output_file,
                elapsed_time=elapsed_time,
                result=result
            )
            
        except Exception as e:
            elapsed_time = time.time() - start_time
            task["status"] = TaskStatus.FAILED
            error_msg = str(e)
            
            logger.error(f"任务 {task_id} 执行失败: {error_msg}")
            
            return TaskResult(
                task_id=task_id,
                status=TaskStatus.FAILED,
                input_file=task["input_file"],
                error=error_msg,
                elapsed_time=elapsed_time
            )
    
    def run_all(self) -> List[TaskResult]:
        """
        并行执行所有任务
        
        Returns:
            List[TaskResult]: 所有任务的结果列表
        """
        results = []
        
        # 使用线程池执行任务
        with ThreadPool(max_workers=self.max_workers) as pool:
            # 提交所有任务
            futures = [
                pool.submit(self.execute_task, task_id)
                for task_id in self.tasks
            ]
            
            # 收集结果
            for future in futures:
                try:
                    result = future.result(timeout=self.timeout + 10)  # 额外加10秒缓冲
                    results.append(result)
                except Exception as e:
                    # 处理任务超时或其他异常
                    task_id = f"unknown_{len(results)}"
                    results.append(TaskResult(
                        task_id=task_id,
                        status=TaskStatus.FAILED,
                        input_file="unknown",
                        error=f"任务执行异常: {str(e)}"
                    ))
        
        return results
    
    def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[TaskStatus]: 任务状态，任务不存在则返回None
        """
        if task_id in self.tasks:
            return self.tasks[task_id]["status"]
        return None
    
    def get_pending_tasks(self) -> List[str]:
        """
        获取所有待处理的任务ID
        
        Returns:
            List[str]: 待处理任务ID列表
        """
        return [
            task_id for task_id, task in self.tasks.items()
            if task["status"] == TaskStatus.PENDING
        ]
    
    def get_completed_tasks(self) -> List[str]:
        """
        获取所有已完成的任务ID
        
        Returns:
            List[str]: 已完成任务ID列表
        """
        return [
            task_id for task_id, task in self.tasks.items()
            if task["status"] == TaskStatus.COMPLETED
        ]
    
    def get_failed_tasks(self) -> List[str]:
        """
        获取所有失败的任务ID
        
        Returns:
            List[str]: 失败任务ID列表
        """
        return [
            task_id for task_id, task in self.tasks.items()
            if task["status"] in (TaskStatus.FAILED, TaskStatus.TIMEOUT)
        ]
    
    def summary(self, results: List[TaskResult]) -> Dict[str, Any]:
        """
        生成任务执行摘要
        
        Args:
            results: 任务结果列表
            
        Returns:
            Dict[str, Any]: 任务摘要信息
        """
        total = len(results)
        completed = sum(1 for r in results if r.status == TaskStatus.COMPLETED)
        failed = sum(1 for r in results if r.status == TaskStatus.FAILED)
        timeout = sum(1 for r in results if r.status == TaskStatus.TIMEOUT)
        
        # 计算平均执行时间（只考虑已完成的任务）
        completed_times = [r.elapsed_time for r in results if r.status == TaskStatus.COMPLETED]
        avg_time = sum(completed_times) / len(completed_times) if completed_times else 0
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "timeout": timeout,
            "success_rate": (completed / total * 100) if total > 0 else 0,
            "average_time": avg_time,
            "total_time": sum(r.elapsed_time for r in results)
        }
    
    def clear_tasks(self) -> None:
        """
        清空所有任务
        """
        self.tasks.clear()
        self.next_task_id = 0