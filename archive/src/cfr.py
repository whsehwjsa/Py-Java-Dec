"""基于CFR的Java反编译工具实现"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
from typing import Optional, Dict
from pathlib import Path

# 获取当前文件所在目录
current_dir = Path(__file__).parent
# 添加当前目录到Python路径以便导入
sys.path.append(str(current_dir))

from base import JavaDecompiler


class CFRDecompiler(JavaDecompiler):
    """基于CFR的Java反编译工具实现"""
    
    def __init__(self, 
                 verbose: bool = False, 
                 deobfuscate: bool = False, 
                 cfr_path: Optional[str] = None,
                 max_workers: int = 4,
                 timeout: Optional[int] = 300,
                 additional_options: Optional[Dict[str, str]] = None):
        """
        初始化CFR反编译工具
        
        Args:
            verbose: 是否显示详细日志
            deobfuscate: 是否启用反混淆
            cfr_path: CFR JAR文件路径
            max_workers: 最大工作线程数
            timeout: 单个文件的反编译超时时间(秒)
            additional_options: 额外的CFR配置选项
        """
        super().__init__(
            verbose=verbose,
            deobfuscate=deobfuscate,
            max_workers=max_workers,
            timeout=timeout,
            additional_options=additional_options
        )
        self.cfr_jar_path = self._find_or_validate_cfr(cfr_path)
        self.log("使用CFR反编译引擎")

    def _find_or_validate_cfr(self, cfr_path: Optional[str]) -> str:
        if cfr_path:
            if os.path.isfile(cfr_path) and cfr_path.endswith(".jar"):
                return os.path.abspath(cfr_path)
            else:
                raise FileNotFoundError(f"CFR JAR文件无效：{cfr_path}")
        
        # 获取项目根目录下的resources文件夹路径
        resources_dir = os.path.join(str(current_dir.parent), "resources")
        common_paths = [
            "cfr.jar",
            os.path.join(resources_dir, "cfr.jar"),
            os.path.expanduser("~/.local/bin/cfr.jar"),
            "/usr/local/bin/cfr.jar",
            "/opt/cfr/cfr.jar",
            "C:\\tools\\cfr.jar"
        ]
        for path in common_paths:
            if os.path.isfile(path):
                return os.path.abspath(path)
        
        raise FileNotFoundError(
            "未找到CFR反编译工具，请下载CFR JAR文件：\n"
            "下载地址：https://github.com/leibnitz27/cfr/releases\n"
            "使用--cfr-path参数指定下载后的JAR文件路径"
        )

    def _get_cfr_command(self, input_path: str, output_file: str) -> list:
        cmd = [
            "java", "-jar", self.cfr_jar_path,
            input_path,
            "--outputdir", os.path.dirname(output_file),
            "--comments", "false",
            "--showversion", "false"
        ]
        
        if self.deobfuscate:
            cmd.extend([
                "--renamedupmembers", "true",
                "--rename", "true"
            ])
        
        # 添加用户自定义的额外选项
        for key, value in self.additional_options.items():
            cmd.extend([f"--{key}", value])
        
        return cmd

    def decompile_single_class(self, class_path: str, output_dir: str, silent: bool = False) -> bool:
        """反编译单个class文件
        
        Args:
            class_path: class文件路径
            output_dir: 输出目录
            silent: 是否静默模式（不打印单个文件进度）
            
        Returns:
            反编译是否成功
        """
        if not os.path.isfile(class_path) or not class_path.endswith(".class"):
            self.log(f"跳过无效class文件：{class_path}")
            return False
        
        class_name = os.path.splitext(os.path.basename(class_path))[0]
        output_subdir = os.path.join(output_dir, f"{class_name}")
        output_file = os.path.join(output_subdir, f"{class_name}.java")
        os.makedirs(output_subdir, exist_ok=True)
        
        if not silent:
            print(f"{class_name}.class 反编译中")
        
        cmd = self._get_cfr_command(class_path, output_file)
        try:
            # 添加超时处理
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"CFR输出：{result.stdout[:500]}...")
            
            # 检查并删除summary.txt文件
            summary_file = os.path.join(os.path.dirname(output_file), "summary.txt")
            if os.path.exists(summary_file):
                try:
                    os.remove(summary_file)
                    self.log(f"已删除summary.txt文件")
                except Exception as e:
                    self.log(f"删除summary.txt文件失败: {str(e)}")
            
            if os.path.exists(output_file):
                # 检查文件大小，过小可能表示反编译不完整
                if os.path.getsize(output_file) < 10:
                    self.log(f"警告：生成的Java文件过小，可能反编译不完整：{output_file}")
                    if not silent:
                        print(f"{class_name}.class 反编译完成（可能不完整）")
                else:
                    if not silent:
                        print(f"{class_name}.class 反编译完成")
                return True
            else:
                self.log(f"CFR未生成输出文件：{output_file}")
                return False
        except subprocess.TimeoutExpired:
            self.log(f"反编译超时：{class_path}")
            if not silent:
                print(f"{class_name}.class 反编译超时")
            return False
        except subprocess.CalledProcessError as e:
            self.log(f"反编译失败：{e.stderr}")
            if not silent:
                print(f"{class_name}.class 反编译失败")
            return False
        except Exception as e:
            self.log(f"发生未预期错误：{str(e)}")
            if not silent:
                print(f"{class_name}.class 处理时发生错误")
            return False

    def decompile_single_jar(self, jar_path: str, output_dir: str, silent: bool = False) -> bool:
        """反编译单个jar文件
        
        Args:
            jar_path: jar文件路径
            output_dir: 输出目录
            silent: 是否静默模式（不打印单个文件进度）
            
        Returns:
            反编译是否成功
        """
        if not os.path.isfile(jar_path) or not jar_path.endswith(".jar"):
            self.log(f"跳过无效jar文件：{jar_path}")
            return False
        
        jar_name = os.path.splitext(os.path.basename(jar_path))[0]
        jar_output_dir = os.path.join(output_dir, f"{jar_name}")
        os.makedirs(jar_output_dir, exist_ok=True)
        
        if not silent:
            print(f"{jar_name}.jar 反编译中")
        
        cmd = self._get_cfr_command(jar_path, os.path.join(jar_output_dir, "dummy.java"))
        try:
            # 添加超时处理
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=self.timeout
            )
            self.log(f"CFR输出：{result.stdout[:500]}...")
            
            # 检查并删除summary.txt文件
            summary_file = os.path.join(jar_output_dir, "summary.txt")
            if os.path.exists(summary_file):
                try:
                    os.remove(summary_file)
                    self.log(f"已删除summary.txt文件")
                except Exception as e:
                    self.log(f"删除summary.txt文件失败: {str(e)}")
            
            java_files = [f for f in os.listdir(jar_output_dir) if f.endswith(".java")]
            if java_files:
                if not silent:
                    print(f"{jar_name}.jar 反编译完成，共生成 {len(java_files)} 个Java文件")
                return True
            else:
                self.log(f"CFR未生成任何Java文件：{jar_output_dir}")
                return False
        except subprocess.TimeoutExpired:
            self.log(f"反编译超时：{jar_path}")
            if not silent:
                print(f"{jar_name}.jar 反编译超时")
            return False
        except subprocess.CalledProcessError as e:
            self.log(f"反编译失败：{e.stderr}")
            if not silent:
                print(f"{jar_name}.jar 反编译失败")
            return False
        except Exception as e:
            self.log(f"发生未预期错误：{str(e)}")
            if not silent:
                print(f"{jar_name}.jar 处理时发生错误")
            return False