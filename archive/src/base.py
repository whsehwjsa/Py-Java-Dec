"""Java反编译工具基类模块"""

import os
import sys
import shutil
import time
import concurrent.futures
from typing import List, Optional, Dict, Set, Tuple

# 尝试导入tqdm以添加进度条显示，如不可用则使用简单的进度显示
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None


class JavaDecompiler:
    """Java反编译工具基类"""
    
    def __init__(self, 
                 verbose: bool = False, 
                 deobfuscate: bool = False,
                 max_workers: int = 4,
                 timeout: Optional[int] = 300,
                 additional_options: Optional[Dict[str, str]] = None):
        """
        初始化反编译工具
        
        Args:
            verbose: 是否显示详细日志
            deobfuscate: 是否启用反混淆
            max_workers: 最大工作线程数
            timeout: 单个文件的反编译超时时间(秒)
            additional_options: 额外的配置选项
        """
        self.verbose = verbose
        self.deobfuscate = deobfuscate
        self.max_workers = max_workers
        self.timeout = timeout
        self.additional_options = additional_options or {}
        self.processed_files = 0
        self.total_files = 0
        self._check_java_env()
    
    def _check_java_env(self) -> None:
        if not shutil.which("java"):
            raise EnvironmentError(
                "未找到Java运行时环境，请先安装JRE或JDK：\n"
                "下载地址：https://www.oracle.com/java/technologies/downloads/"
            )

    def log(self, message: str) -> None:
        if self.verbose:
            print(f"[*] {message}")
            
    def _collect_files(self, input_path: str) -> List[Tuple[str, str]]:
        """收集需要反编译的文件
        
        Args:
            input_path: 输入路径
            
        Returns:
            文件路径和类型的列表，类型为'jar'或'class'
        """
        files_to_process = []
        
        if os.path.isfile(input_path):
            if input_path.endswith(".jar"):
                files_to_process.append((input_path, "jar"))
            elif input_path.endswith(".class"):
                files_to_process.append((input_path, "class"))
            else:
                self.log(f"不支持的文件类型：{input_path}")
        
        elif os.path.isdir(input_path):
            self.log(f"扫描目录：{input_path} 中的class和jar文件")
            for root, _, files in os.walk(input_path):
                for file in files:
                    if file.endswith(".jar"):
                        files_to_process.append((os.path.join(root, file), "jar"))
                    elif file.endswith(".class"):
                        files_to_process.append((os.path.join(root, file), "class"))
        
        return files_to_process
    
    def _process_file(self, file_info: Tuple[str, str], output_dir: str) -> bool:
        """处理单个文件
        
        Args:
            file_info: (文件路径, 文件类型)元组
            output_dir: 输出目录
            
        Returns:
            处理是否成功
        """
        file_path, file_type = file_info
        if file_type == "jar":
            return self.decompile_single_jar(file_path, output_dir, silent=True)
        elif file_type == "class":
            return self.decompile_single_class(file_path, output_dir, silent=True)
        return False
    
    def decompile_path(self, input_path: str, output_dir: str, use_multithreading: bool = True) -> Dict[str, int]:
        """反编译指定路径中的所有支持的文件
        
        Args:
            input_path: 输入路径（文件或目录）
            output_dir: 输出目录
            use_multithreading: 是否使用多线程处理
            
        Returns:
            包含统计信息的字典
        """
        # 收集文件
        files_to_process = self._collect_files(input_path)
        self.total_files = len(files_to_process)
        self.processed_files = 0
        
        success_count = 0
        start_time = time.time()
        
        if not files_to_process:
            print(f"未找到需要反编译的class或jar文件：{input_path}")
            return {"total": 0, "success": 0, "failed": 0, "time": 0}
        
        print(f"找到 {self.total_files} 个文件待处理")
        
        # 使用进度条或简单计数器
        if tqdm and self.total_files > 1:
            # 使用tqdm进度条
            if use_multithreading and self.total_files > 1 and self.max_workers > 1:
                # 多线程处理带进度条
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_file = {executor.submit(self._process_file, file_info, output_dir): file_info 
                                    for file_info in files_to_process}
                    
                    with tqdm(total=len(future_to_file), desc="反编译进度") as pbar:
                        for future in concurrent.futures.as_completed(future_to_file):
                            if future.result():
                                success_count += 1
                            pbar.update(1)
            else:
                # 单线程处理带进度条
                for file_info in tqdm(files_to_process, desc="反编译进度"):
                    if self._process_file(file_info, output_dir):
                        success_count += 1
        else:
            # 简单进度显示
            if use_multithreading and self.total_files > 1 and self.max_workers > 1:
                # 多线程处理
                with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    results = list(executor.map(lambda f: self._process_file(f, output_dir), files_to_process))
                    success_count = sum(results)
                    
                    # 显示进度
                    for i, result in enumerate(results, 1):
                        sys.stdout.write(f"\r进度: {i}/{self.total_files}")
                        sys.stdout.flush()
                    sys.stdout.write("\n")
            else:
                # 单线程处理
                for i, file_info in enumerate(files_to_process, 1):
                    file_path, _ = file_info
                    file_name = os.path.basename(file_path)
                    print(f"[{i}/{self.total_files}] 处理 {file_name}")
                    
                    if self._process_file(file_info, output_dir):
                        success_count += 1
        
        elapsed_time = time.time() - start_time
        
        stats = {
            "total": self.total_files,
            "success": success_count,
            "failed": self.total_files - success_count,
            "time": elapsed_time
        }
        
        return stats
        
    # 需要子类实现的方法
    def decompile_single_class(self, class_path: str, output_dir: str, silent: bool = False) -> bool:
        raise NotImplementedError("子类必须实现此方法")
        
    def decompile_single_jar(self, jar_path: str, output_dir: str, silent: bool = False) -> bool:
        raise NotImplementedError("子类必须实现此方法")