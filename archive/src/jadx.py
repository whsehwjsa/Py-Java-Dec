#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""基于JADX的Java反编译工具实现"""

import os
import sys
import subprocess
import shutil
from typing import Optional, Dict
from pathlib import Path

# 获取当前文件所在目录
current_dir = Path(__file__).parent
# 添加当前目录到Python路径以便导入
sys.path.append(str(current_dir))

# 导入基类
from base import JavaDecompiler


class JADXDecompiler(JavaDecompiler):
    """基于JADX的Java反编译工具实现"""
    
    def __init__(self, 
                 verbose: bool = False, 
                 deobfuscate: bool = False, 
                 jadx_path: Optional[str] = None,
                 max_workers: int = 4,
                 timeout: Optional[int] = 300,
                 additional_options: Optional[Dict[str, str]] = None):
        """
        初始化JADX反编译工具
        
        Args:
            verbose: 是否显示详细日志
            deobfuscate: 是否启用反混淆
            jadx_path: JADX可执行文件路径或JAR文件路径
            max_workers: 最大工作线程数
            timeout: 单个文件的反编译超时时间(秒)
            additional_options: 额外的JADX配置选项
        """
        super().__init__(
            verbose=verbose,
            deobfuscate=deobfuscate,
            max_workers=max_workers,
            timeout=timeout,
            additional_options=additional_options
        )
        self.jadx_path = self._find_or_validate_jadx(jadx_path)
        self.is_jadx_jar = self.jadx_path.endswith(".jar")
        self.log("使用JADX反编译引擎")
    
    def _find_or_validate_jadx(self, jadx_path: Optional[str]) -> str:
        # 首先检查直接指定的路径
        if jadx_path:
            if os.path.isfile(jadx_path):
                return os.path.abspath(jadx_path)
            else:
                raise FileNotFoundError(f"JADX文件无效：{jadx_path}")
        
        # 检查环境变量中的jadx命令
        jadx_cmd = shutil.which("jadx")
        if jadx_cmd:
            return jadx_cmd
        
        # 检查常见路径
        common_paths = [
            "jadx.jar",
            "jadx/bin/jadx",
            "jadx/bin/jadx.bat",
            os.path.expanduser("~/.local/bin/jadx"),
            os.path.expanduser("~/.local/bin/jadx.jar"),
            "/usr/local/bin/jadx",
            "/opt/jadx/bin/jadx",
            "C:\\tools\\jadx\\bin\\jadx",
            "C:\\tools\\jadx\\bin\\jadx.bat",
            "C:\\tools\\jadx.jar"
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        raise FileNotFoundError(
            "未找到JADX反编译工具，请下载并安装JADX：\n"
            "下载地址：https://github.com/skylot/jadx/releases\n"
            "使用--jadx-path参数指定JADX可执行文件或JAR文件路径"
        )
    
    def _get_jadx_command(self, input_path: str, output_dir: str) -> list:
        # JADX有两种使用方式：直接命令行或通过java -jar
        if self.is_jadx_jar:
            cmd = ["java", "-jar", self.jadx_path]
        else:
            cmd = [self.jadx_path]
        
        # 基本选项
        cmd.extend([
            "-d", output_dir,
            "--no-res",  # 不反编译资源文件
            "--no-imports",  # 不生成导入语句
            "--no-src-vars",  # 不生成源变量
        ])
        
        # 反混淆选项
        if self.deobfuscate:
            cmd.extend([
                "--deobf",  # 启用反混淆
                "--deobf-min", "3",  # 最短标识符长度
                "--deobf-max", "32"  # 最长标识符长度
            ])
        
        # 添加用户自定义的额外选项
        for key, value in self.additional_options.items():
            cmd.extend([f"--{key}", value])
        
        # 添加输入文件
        cmd.append(input_path)
        
        return cmd
    
    def decompile_single_class(self, class_path: str, output_dir: str, silent: bool = False) -> bool:
        """使用JADX反编译单个class文件"""
        if not os.path.isfile(class_path) or not class_path.endswith(".class"):
            self.log(f"跳过无效class文件：{class_path}")
            return False
        
        class_name = os.path.splitext(os.path.basename(class_path))[0]
        output_subdir = os.path.join(output_dir, f"class_{class_name}")
        os.makedirs(output_subdir, exist_ok=True)
        
        if not silent:
            print(f"{class_name}.class 反编译中 (JADX)")
        
        cmd = self._get_jadx_command(class_path, output_subdir)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"JADX输出：{result.stdout[:500]}...")
            
            # 查找生成的.java文件
            java_files = []
            for root, _, files in os.walk(output_subdir):
                for file in files:
                    if file.endswith(".java"):
                        java_files.append(os.path.join(root, file))
            
            if java_files:
                if not silent:
                    print(f"{class_name}.class 反编译完成，共生成 {len(java_files)} 个Java文件 (JADX)")
                return True
            else:
                self.log(f"JADX未生成任何Java文件：{output_subdir}")
                return False
        except Exception as e:
            self.log(f"反编译失败：{str(e)}")
            if not silent:
                print(f"{class_name}.class 反编译失败 (JADX)")
            return False
    
    def decompile_single_jar(self, jar_path: str, output_dir: str, silent: bool = False) -> bool:
        """使用JADX反编译单个jar文件"""
        if not os.path.isfile(jar_path) or not jar_path.endswith(".jar"):
            self.log(f"跳过无效jar文件：{jar_path}")
            return False
        
        jar_name = os.path.splitext(os.path.basename(jar_path))[0]
        jar_output_dir = os.path.join(output_dir, f"jar_{jar_name}")
        os.makedirs(jar_output_dir, exist_ok=True)
        
        if not silent:
            print(f"{jar_name}.jar 反编译中 (JADX)")
        
        cmd = self._get_jadx_command(jar_path, jar_output_dir)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"JADX输出：{result.stdout[:500]}...")
            
            # 查找生成的.java文件
            java_files = []
            for root, _, files in os.walk(jar_output_dir):
                for file in files:
                    if file.endswith(".java"):
                        java_files.append(os.path.join(root, file))
            
            if java_files:
                if not silent:
                    print(f"{jar_name}.jar 反编译完成，共生成 {len(java_files)} 个Java文件 (JADX)")
                return True
            else:
                self.log(f"JADX未生成任何Java文件：{jar_output_dir}")
                return False
        except Exception as e:
            self.log(f"反编译失败：{str(e)}")
            if not silent:
                print(f"{jar_name}.jar 反编译失败 (JADX)")
            return False