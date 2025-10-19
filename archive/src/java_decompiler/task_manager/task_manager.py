#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
任务管理器实现
管理反编译任务队列和并发执行
"""

import queue
import threading
import uuid
import time
from typing import Dict, List, Optional, Any, Callable
from enum import Enum, auto
from concurrent.futures import ThreadPoolExecutor, as_completed

from java_decompiler.logger.logger import get_logger
from java_decompiler.core.processor import DecompilationProcessor
from java_decompiler.exceptions import (
    DecompilationError,
    BatchDecompilationError
)

logger = get_logger(__name__)


class TaskStatus(Enum):
    """
    任务状态枚举
    """
    PENDING = auto()      # 等待执行
    RUNNING = auto()      # 正在执行
    COMPLETED = auto()    # 执行完成
    FAILED = auto()       # 执行失败
    CANCELLED = auto()    # 已取消


class DecompilationTask:
    """
    反编译任务类
    """
    def __init__(self, input_path: str, output_path: str,
                 engine_name: str = None, options: Dict[str, Any] = None,
                 priority: int = 0, task_id: str = None):
        """
        初始化反编译任务
        
        Args:
            input_path: 输入文件或目录路径
            output_path: 输出目录路径
            engine_name: 反编译引擎名称
            options: 反编译选项
            priority: 任务优先级，数字越大优先级越高
            task_id: 任务ID，如果为None则自动生成
        """
        self.task_id = task_id or str(uuid.uuid4())
        self.input_path = input_path
        self.output_path = output_path
        self.engine_name = engine_name
        self.options = options or {}
        self.priority = priority
        
        # 任务状态信息
        self.status = TaskStatus.PENDING
        self.start_time = None
        self.end_time = None
        self.error_message = None
        self.result = None
        
        # 进度信息
        self.progress = 0.0  # 0.0 - 100.0
        self.current_file = None
        self.total_files = 0
        self.completed_files = 0
        
    def __lt__(self, other):
        """
        用于优先级队列的比较，优先级高的任务排在前面
        """
        return self.priority > other.priority
    
    def start(self):
        """
        标记任务开始执行
        """
        self.status = TaskStatus.RUNNING
        self.start_time = time.time()
        logger.debug(f"任务开始执行: {self.task_id}, 输入: {self.input_path}")
    
    def complete(self, result: Any = None):
        """
        标记任务完成
        
        Args:
            result: 任务执行结果
        """
        self.status = TaskStatus.COMPLETED
        self.end_time = time.time()
        self.result = result
        self.progress = 100.0
        logger.debug(f"任务执行完成: {self.task_id}, 耗时: {self.duration:.3f}秒")
    
    def fail(self, error_message: str):
        """
        标记任务失败
        
        Args:
            error_message: 错误消息
        """
        self.status = TaskStatus.FAILED
        self.end_time = time.time()
        self.error_message = error_message
        logger.debug(f"任务执行失败: {self.task_id}, 错误: {error_message}")
    
    def cancel(self):
        """
        取消任务
        """
        if self.status == TaskStatus.PENDING:
            self.status = TaskStatus.CANCELLED
            logger.debug(f"任务已取消: {self.task_id}")
            return True
        return False
    
    def update_progress(self, progress: float, current_file: str = None,
                       completed: int = None, total: int = None):
        """
        更新任务进度
        
        Args:
            progress: 进度百分比 (0-100)
            current_file: 当前正在处理的文件
            completed: 已完成的文件数量
            total: 文件总数量
        """
        self.progress = min(100.0, max(0.0, progress))
        if current_file:
            self.current_file = current_file
        if completed is not None:
            self.completed_files = completed
        if total is not None:
            self.total_files = total
    
    @property
    def duration(self) -> Optional[float]:
        """
        获取任务执行时间
        
        Returns:
            Optional[float]: 执行时间（秒），如果任务未开始则返回None
        """
        if self.start_time is None:
            return None
        
        end = self.end_time or time.time()
        return end - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将任务信息转换为字典
        
        Returns:
            Dict[str, Any]: 任务信息字典
        """
        return {
            'task_id': self.task_id,
            'input_path': self.input_path,
            'output_path': self.output_path,
            'engine_name': self.engine_name,
            'priority': self.priority,
            'status': self.status.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration': self.duration,
            'progress': self.progress,
            'current_file': self.current_file,
            'completed_files': self.completed_files,
            'total_files': self.total_files,
            'error_message': self.error_message
        }


class TaskManager:
    """
    任务管理器
    """
    def __init__(self, max_workers: int = None):
        """
        初始化任务管理器
        
        Args:
            max_workers: 最大工作线程数，如果为None则使用CPU核心数
        """
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, DecompilationTask] = {}
        self.completed_tasks: Dict[str, DecompilationTask] = {}
        self.max_workers = max_workers
        self.executor = None
        self.lock = threading.RLock()  # 可重入锁，保护任务状态更新
        self.shutdown = False
        
    def add_task(self, task: DecompilationTask) -> str:
        """
        添加任务到队列
        
        Args:
            task: 反编译任务
            
        Returns:
            str: 任务ID
        """
        with self.lock:
            if self.shutdown:
                raise RuntimeError("任务管理器已关闭")
                
            self.task_queue.put(task)
            self.active_tasks[task.task_id] = task
            logger.debug(f"任务已添加到队列: {task.task_id}")
            
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[DecompilationTask]:
        """
        获取任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[DecompilationTask]: 任务对象，如果不存在则返回None
        """
        with self.lock:
            # 先从活跃任务中查找
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            # 再从已完成任务中查找
            return self.completed_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        with self.lock:
            task = self.get_task(task_id)
            if task and task.cancel():
                # 从活跃任务列表中移除已取消的任务
                if task_id in self.active_tasks:
                    del self.active_tasks[task_id]
                return True
            return False
    
    def get_active_tasks(self) -> List[DecompilationTask]:
        """
        获取所有活跃任务
        
        Returns:
            List[DecompilationTask]: 活跃任务列表
        """
        with self.lock:
            return list(self.active_tasks.values())
    
    def get_completed_tasks(self) -> List[DecompilationTask]:
        """
        获取所有已完成任务
        
        Returns:
            List[DecompilationTask]: 已完成任务列表
        """
        with self.lock:
            return list(self.completed_tasks.values())
    
    def execute_next_task(self) -> Optional[DecompilationTask]:
        """
        执行队列中的下一个任务
        
        Returns:
            Optional[DecompilationTask]: 执行的任务对象，如果队列为空则返回None
        """
        try:
            # 尝试获取下一个任务
            task = self.task_queue.get(block=False)
            
            try:
                # 执行任务
                self._execute_task_internal(task)
                return task
            except Exception as e:
                # 如果执行过程中出错，标记任务失败
                with self.lock:
                    task.fail(str(e))
                    self._move_to_completed(task)
                raise
        except queue.Empty:
            # 队列为空
            return None
    
    def _execute_task_internal(self, task: DecompilationTask):
        """
        内部执行任务的方法
        
        Args:
            task: 要执行的任务
        """
        # 更新任务状态
        with self.lock:
            task.start()
        
        try:
            # 创建进度回调函数
            def progress_callback(progress, current_file=None, completed=None, total=None):
                with self.lock:
                    task.update_progress(progress, current_file, completed, total)
            
            # 创建处理器并执行反编译
            processor = DecompilationProcessor()
            result = processor.decompile(
                task.input_path,
                task.output_path,
                engine_name=task.engine_name,
                options=task.options,
                progress_callback=progress_callback
            )
            
            # 标记任务完成
            with self.lock:
                task.complete(result)
                self._move_to_completed(task)
                
        except Exception as e:
            # 标记任务失败
            with self.lock:
                task.fail(str(e))
                self._move_to_completed(task)
            raise
    
    def _move_to_completed(self, task: DecompilationTask):
        """
        将任务从活跃列表移动到已完成列表
        
        Args:
            task: 任务对象
        """
        if task.task_id in self.active_tasks:
            del self.active_tasks[task.task_id]
        self.completed_tasks[task.task_id] = task
        
    def execute_all_tasks(self, max_concurrent: int = None):
        """
        执行队列中所有任务
        
        Args:
            max_concurrent: 最大并发任务数，如果为None则使用初始化时的配置
        """
        # 创建线程池
        max_workers = max_concurrent or self.max_workers
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有任务
            futures = []
            while not self.task_queue.empty() and not self.shutdown:
                try:
                    task = self.task_queue.get(block=False)
                    future = executor.submit(self._execute_task_internal, task)
                    futures.append(future)
                except queue.Empty:
                    break
                except Exception as e:
                    logger.error(f"提交任务时出错: {str(e)}")
            
            # 等待所有任务完成
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"任务执行出错: {str(e)}")
    
    def shutdown_manager(self, wait: bool = True):
        """
        关闭任务管理器
        
        Args:
            wait: 是否等待所有任务完成
        """
        with self.lock:
            self.shutdown = True
        
        # 如果有执行器正在运行，关闭它
        if self.executor:
            self.executor.shutdown(wait=wait)


# 创建全局任务管理器实例
_global_task_manager = None


def create_task(input_path: str, output_path: str,
                engine_name: str = None, options: Dict[str, Any] = None,
                priority: int = 0) -> str:
    """
    创建反编译任务
    
    Args:
        input_path: 输入文件或目录路径
        output_path: 输出目录路径
        engine_name: 反编译引擎名称
        options: 反编译选项
        priority: 任务优先级
        
    Returns:
        str: 任务ID
    """
    global _global_task_manager
    
    # 懒加载任务管理器
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    
    # 创建任务
    task = DecompilationTask(
        input_path=input_path,
        output_path=output_path,
        engine_name=engine_name,
        options=options,
        priority=priority
    )
    
    # 添加到任务管理器
    return _global_task_manager.add_task(task)


def execute_task(task_id: str) -> Dict[str, Any]:
    """
    执行指定任务
    
    Args:
        task_id: 任务ID
        
    Returns:
        Dict[str, Any]: 任务结果
    """
    global _global_task_manager
    
    if _global_task_manager is None:
        raise RuntimeError("任务管理器未初始化")
    
    # 获取任务
    task = _global_task_manager.get_task(task_id)
    if not task:
        raise ValueError(f"任务不存在: {task_id}")
    
    # 如果任务已在队列中，执行队列中的下一个任务
    if task.status == TaskStatus.PENDING:
        _global_task_manager.execute_next_task()
    # 否则直接执行任务
    elif task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
        # 创建新任务执行
        new_task = DecompilationTask(
            input_path=task.input_path,
            output_path=task.output_path,
            engine_name=task.engine_name,
            options=task.options,
            priority=task.priority
        )
        _global_task_manager.add_task(new_task)
        _global_task_manager.execute_next_task()
        task = new_task
    
    # 等待任务完成
    while task.status == TaskStatus.RUNNING:
        time.sleep(0.1)
    
    # 返回任务结果
    result = task.to_dict()
    if task.status == TaskStatus.FAILED:
        raise DecompilationError(
            task.input_path,
            task.engine_name,
            task.error_message
        )
    
    return result


def execute_batch_tasks(tasks: List[Dict[str, Any]],
                       max_concurrent: int = None) -> Dict[str, Any]:
    """
    批量执行多个任务
    
    Args:
        tasks: 任务配置列表
        max_concurrent: 最大并发任务数
        
    Returns:
        Dict[str, Any]: 批量执行结果
    """
    global _global_task_manager
    
    # 懒加载任务管理器
    if _global_task_manager is None:
        _global_task_manager = TaskManager()
    
    # 创建任务
    task_ids = []
    for task_config in tasks:
        task_id = create_task(
            input_path=task_config['input_path'],
            output_path=task_config['output_path'],
            engine_name=task_config.get('engine_name'),
            options=task_config.get('options'),
            priority=task_config.get('priority', 0)
        )
        task_ids.append(task_id)
    
    # 执行所有任务
    _global_task_manager.execute_all_tasks(max_concurrent=max_concurrent)
    
    # 收集结果
    results = []
    failed_tasks = []
    
    for task_id in task_ids:
        task = _global_task_manager.get_task(task_id)
        if task:
            task_result = task.to_dict()
            results.append(task_result)
            if task.status == TaskStatus.FAILED:
                failed_tasks.append({
                    'task_id': task.task_id,
                    'input_path': task.input_path,
                    'error': task.error_message
                })
    
    # 如果有失败的任务，抛出异常
    if failed_tasks:
        raise BatchDecompilationError(
            total_files=len(tasks),
            success_count=len(results) - len(failed_tasks),
            failed_files=failed_tasks
        )
    
    return {
        'total_tasks': len(tasks),
        'success_count': len(results) - len(failed_tasks),
        'failed_count': len(failed_tasks),
        'results': results
    }