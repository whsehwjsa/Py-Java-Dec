#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
基于FernFlower的Java反编译工具实现"""

import os
import sys
import subprocess
import glob
import tempfile
import shutil
from typing import Optional, Dict
from pathlib import Path

# 获取当前文件所在目录
current_dir = Path(__file__).parent
# 添加当前目录到Python路径以便导入
sys.path.append(str(current_dir))

# 导入基类
from base import JavaDecompiler



class FernFlowerDecompiler(JavaDecompiler):
    """基于FernFlower的Java反编译工具实现"""
    
    def __init__(self, 
                 verbose: bool = False, 
                 deobfuscate: bool = False, 
                 fernflower_path: Optional[str] = None,
                 max_workers: int = 4,
                 timeout: Optional[int] = 300,
                 additional_options: Optional[Dict[str, str]] = None):
        """
        初始化FernFlower反编译工具
        
        Args:
            verbose: 是否显示详细日志
            deobfuscate: 是否启用反混淆
            fernflower_path: FernFlower JAR文件路径
            max_workers: 最大工作线程数
            timeout: 单个文件的反编译超时时间(秒)
            additional_options: 额外的FernFlower配置选项
        """
        super().__init__(
            verbose=verbose,
            deobfuscate=deobfuscate,
            max_workers=max_workers,
            timeout=timeout,
            additional_options=additional_options
        )
        self.fernflower_jar_path = self._find_or_validate_fernflower(fernflower_path)
        self.log("使用FernFlower反编译引擎")
    
    def _find_or_validate_fernflower(self, fernflower_path: Optional[str]) -> str:
        if fernflower_path:
            if os.path.isfile(fernflower_path) and fernflower_path.endswith(".jar"):
                return os.path.abspath(fernflower_path)
            else:
                raise FileNotFoundError(f"FernFlower JAR文件无效：{fernflower_path}")
        
        common_paths = [
            "fernflower.jar",
            "fernflower-*.jar",
            os.path.expanduser("~/.local/bin/fernflower.jar"),
            "/usr/local/bin/fernflower.jar",
            "/opt/fernflower/fernflower.jar",
            "C:\\tools\\fernflower.jar"
        ]
        
        # 尝试精确匹配
        for path in common_paths:
            if os.path.isfile(path):
                return os.path.abspath(path)
        
        # 尝试通配符匹配
        for pattern in common_paths:
            if '*' in pattern:
                matches = glob.glob(pattern)
                if matches:
                    return os.path.abspath(matches[0])
        
        raise FileNotFoundError(
            "未找到FernFlower反编译工具，请下载FernFlower JAR文件：\n"
            "下载地址：https://github.com/fesh0r/fernflower/releases 或 https://github.com/fornwall/jadx/releases\n"
            "使用--fernflower-path参数指定下载后的JAR文件路径"
        )
    
    def _get_fernflower_command(self, input_path: str, output_dir: str) -> list:
        # FernFlower的命令行参数格式是：java -jar fernflower.jar [options] <source> <destination>
        cmd = [
            "java", "-jar", self.fernflower_jar_path
        ]
        
        # 添加FernFlower选项
        if self.deobfuscate:
            cmd.extend(["-ren", "1", "-din", "1", "-rbr", "1", "-dgs", "1", "-asc", "1"])
        
        # 添加用户自定义的额外选项
        for key, value in self.additional_options.items():
            cmd.extend([f"-{key}", value])
        
        # 添加源文件和目标目录
        cmd.extend([input_path, output_dir])
        
        return cmd
    
    def decompile_single_class(self, class_path: str, output_dir: str, silent: bool = False) -> bool:
        """使用FernFlower反编译单个class文件"""
        if not os.path.isfile(class_path) or not class_path.endswith(".class"):
            self.log(f"跳过无效class文件：{class_path}")
            return False
        
        class_name = os.path.splitext(os.path.basename(class_path))[0]
        output_subdir = os.path.join(output_dir, f"class_{class_name}")
        os.makedirs(output_subdir, exist_ok=True)
        
        if not silent:
            print(f"{class_name}.class 反编译中 (FernFlower)")
        
        cmd = self._get_fernflower_command(class_path, output_subdir)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"FernFlower输出：{result.stdout[:500]}...")
            
            # FernFlower会生成.jar文件，需要解压
            output_jar = os.path.join(output_subdir, f"{class_name}.jar")
            if os.path.exists(output_jar):
                # 创建临时目录来解压
                temp_dir = os.path.join(output_subdir, "temp")
                os.makedirs(temp_dir, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(output_jar, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # 查找生成的.java文件
                    for root, _, files in os.walk(temp_dir):
                        for file in files:
                            if file.endswith(".java"):
                                java_file = os.path.join(root, file)
                                dest_file = os.path.join(output_subdir, f"{class_name}.java")
                                shutil.copy2(java_file, dest_file)
                                
                                if not silent:
                                    print(f"{class_name}.class 反编译完成 (FernFlower)")
                                return True
                    
                    return False
                finally:
                    # 清理临时文件
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                    if os.path.exists(output_jar):
                        os.remove(output_jar)
            else:
                self.log(f"FernFlower未生成输出文件：{output_jar}")
                return False
        except Exception as e:
            self.log(f"反编译失败：{str(e)}")
            if not silent:
                print(f"{class_name}.class 反编译失败 (FernFlower)")
            return False
    
    def decompile_single_jar(self, jar_path: str, output_dir: str, silent: bool = False) -> bool:
        """使用FernFlower反编译单个jar文件"""
        if not os.path.isfile(jar_path) or not jar_path.endswith(".jar"):
            self.log(f"跳过无效jar文件：{jar_path}")
            return False
        
        jar_name = os.path.splitext(os.path.basename(jar_path))[0]
        jar_output_dir = os.path.join(output_dir, f"jar_{jar_name}")
        os.makedirs(jar_output_dir, exist_ok=True)
        
        if not silent:
            print(f"{jar_name}.jar 反编译中 (FernFlower)")
        
        cmd = self._get_fernflower_command(jar_path, jar_output_dir)
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"FernFlower输出：{result.stdout[:500]}...")
            
            # FernFlower会生成.jar文件，需要解压
            output_jar = os.path.join(jar_output_dir, f"{jar_name}.jar")
            if os.path.exists(output_jar):
                # 解压结果jar
                extract_dir = os.path.join(jar_output_dir, "sources")
                os.makedirs(extract_dir, exist_ok=True)
                
                try:
                    with zipfile.ZipFile(output_jar, 'r') as zip_ref:
                        zip_ref.extractall(extract_dir)
                    
                    # 统计生成的.java文件数量
                    java_files = []
                    for root, _, files in os.walk(extract_dir):
                        for file in files:
                            if file.endswith(".java"):
                                java_files.append(os.path.join(root, file))
                    
                    if java_files:
                        if not silent:
                            print(f"{jar_name}.jar 反编译完成，共生成 {len(java_files)} 个Java文件 (FernFlower)")
                        return True
                    else:
                        return False
                finally:
                    # 保留解压后的源文件，清理中间jar文件
                    if os.path.exists(output_jar):
                        os.remove(output_jar)
            else:
                self.log(f"FernFlower未生成输出文件：{output_jar}")
                return False
        except Exception as e:
            self.log(f"反编译失败：{str(e)}")
            if not silent:
                print(f"{jar_name}.jar 反编译失败 (FernFlower)")
            return False