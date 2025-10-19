#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
线程池实现
提供高效的线程管理和任务调度功能
"""

import queue
import threading
import time
from typing import Any, Callable, List, Optional, Tuple, TypeVar, Generic
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')

class ThreadPool(Generic[T]):
    """
    线程池管理器
    """
    
    def __init__(self, max_workers: int = 4):
        """
        初始化线程池
        
        Args:
            max_workers: 最大线程数量
        """
        self.max_workers = max(max_workers, 1)  # 至少1个线程
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.tasks = []
        self._lock = threading.Lock()
        self._shutdown = False
    
    def submit(self, func: Callable[..., T], *args: Any, **kwargs: Any) -> Any:
        """
        提交任务到线程池
        
        Args:
            func: 要执行的函数
            *args: 函数参数
            **kwargs: 关键字参数
            
        Returns:
            Future: 任务的Future对象
        """
        with self._lock:
            if self._shutdown:
                raise RuntimeError("线程池已关闭，无法提交新任务")
            
            future = self.executor.submit(func, *args, **kwargs)
            self.tasks.append(future)
            return future
    
    def map(self, func: Callable[..., T], iterable: Any) -> List[T]:
        """
        对可迭代对象中的每个元素应用函数
        
        Args:
            func: 要执行的函数
            iterable: 可迭代对象
            
        Returns:
            List: 结果列表
        """
        with self._lock:
            if self._shutdown:
                raise RuntimeError("线程池已关闭，无法提交新任务")
            
            results = list(self.executor.map(func, iterable))
            return results
    
    def wait_completion(self, timeout: Optional[float] = None) -> List[Tuple[bool, Any]]:
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            List[Tuple[bool, Any]]: 每个任务的完成状态和结果
                - bool: 是否成功完成
                - Any: 任务结果或异常
        """
        results = []
        start_time = time.time()
        
        for future in self.tasks:
            # 计算剩余超时时间
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    remaining = 0
                else:
                    remaining = timeout - elapsed
            else:
                remaining = None
                
            try:
                result = future.result(timeout=remaining)
                results.append((True, result))
            except Exception as e:
                results.append((False, e))
        
        return results
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        with self._lock:
            self._shutdown = True
            self.executor.shutdown(wait=wait)
            self.tasks.clear()
    
    def __enter__(self) -> 'ThreadPool':
        """
        支持上下文管理器
        """
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文管理器时关闭线程池
        """
        self.shutdown(wait=True)


class SimpleThreadPool:
    """
    简单线程池实现
    使用队列和工作线程实现
    """
    
    def __init__(self, num_threads: int = 4):
        """
        初始化简单线程池
        
        Args:
            num_threads: 线程数量
        """
        self.task_queue = queue.Queue()
        self.num_threads = max(num_threads, 1)  # 至少1个线程
        self.workers = []
        self.running = False
    
    def start(self) -> None:
        """
        启动线程池
        """
        if self.running:
            return
            
        self.running = True
        for _ in range(self.num_threads):
            worker = threading.Thread(target=self._worker_thread, daemon=True)
            worker.start()
            self.workers.append(worker)
    
    def submit(self, task: Callable[..., Any], *args: Any, **kwargs: Any) -> None:
        """
        提交任务到线程池
        
        Args:
            task: 要执行的任务函数
            *args: 函数参数
            **kwargs: 关键字参数
        """
        if not self.running:
            raise RuntimeError("线程池未启动")
            
        self.task_queue.put((task, args, kwargs))
    
    def _worker_thread(self) -> None:
        """
        工作线程函数
        """
        while self.running:
            try:
                # 使用超时以便能够检查running标志
                task, args, kwargs = self.task_queue.get(timeout=0.1)
                try:
                    task(*args, **kwargs)
                except Exception:
                    # 忽略任务执行错误
                    pass
                finally:
                    self.task_queue.task_done()
            except queue.Empty:
                # 队列为空，继续循环
                continue
    
    def wait_completion(self) -> None:
        """
        等待所有任务完成
        """
        if self.running:
            self.task_queue.join()
    
    def shutdown(self, wait: bool = True) -> None:
        """
        关闭线程池
        
        Args:
            wait: 是否等待所有任务完成
        """
        if wait:
            self.wait_completion()
            
        self.running = False
        
        # 等待所有工作线程结束
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=1.0)  # 设置超时，防止无限等待
        
        self.workers.clear()
    
    def __enter__(self) -> 'SimpleThreadPool':
        """
        支持上下文管理器
        """
        self.start()
        return self
    
    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """
        退出上下文管理器时关闭线程池
        """
        self.shutdown(wait=True)