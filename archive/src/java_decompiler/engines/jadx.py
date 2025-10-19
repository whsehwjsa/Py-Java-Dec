#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
JADX反编译引擎实现
使用JADX Java反编译器进行反编译操作，适合Android应用分析
"""

import os
import subprocess
import tempfile
import shutil
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

from .engine_base import DecompilerEngine, EngineMetadata, EngineOption
from java_decompiler.exceptions import DecompilationError, ToolNotFoundError, InvalidInputError, ConfigurationError
from java_decompiler.utils.file_utils import ensure_directory, is_class_file, is_jar_file, extract_jar, is_apk_file
from java_decompiler.utils.path_utils import normalize_path
from java_decompiler.utils.filename_utils import get_java_file_name, parse_java_class_filename


class JADXDecompiler(DecompilerEngine):
    """
    JADX反编译器实现
    JADX是一款功能强大的Java反编译器，特别适合Android应用分析
    """
    
    # 引擎元数据
    metadata = EngineMetadata(
        name="JADX",
        version="1.0.0",
        description="强大的Java/Android反编译器",
        supports_files=[".class", ".jar", ".apk", ".dex"],
        requires_java=True
    )
    
    # 支持的配置选项
    supported_options = {
        "path": EngineOption(
            type=str, 
            default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "tools", "jadx"),
            description="JADX工具目录路径"
        ),
        "cli_path": EngineOption(
            type=str, 
            default=None,
            description="JADX CLI可执行文件路径，如果为None将使用默认路径"
        ),
        "deobfuscation": EngineOption(
            type=bool, 
            default=False,
            description="启用反混淆"
        ),
        "deobfuscation_min": EngineOption(
            type=int, 
            default=3,
            description="反混淆最小标识符长度"
        ),
        "deobfuscation_max": EngineOption(
            type=int, 
            default=64,
            description="反混淆最大标识符长度"
        ),
        "string_encryption": EngineOption(
            type=bool, 
            default=False,
            description="尝试解码加密字符串"
        ),
        "show_inconsistent_code": EngineOption(
            type=bool, 
            default=False,
            description="显示不一致的代码"
        ),
        "escape_unicode": EngineOption(
            type=bool, 
            default=False,
            description="转义Unicode字符"
        ),
        "no_resources": EngineOption(
            type=bool, 
            default=False,
            description="不反编译资源"
        ),
        "no_debug_info": EngineOption(
            type=bool, 
            default=False,
            description="忽略调试信息"
        ),
        "no_class_debug_info": EngineOption(
            type=bool, 
            default=False,
            description="忽略类调试信息"
        ),
        "no_rt": EngineOption(
            type=bool, 
            default=False,
            description="不添加运行时异常检查"
        ),
        "threads": EngineOption(
            type=int, 
            default=0,
            description="使用的线程数，0表示自动检测"
        ),
        "log_level": EngineOption(
            type=str, 
            default="WARN",
            description="日志级别"
        )
    }
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化JADX反编译器
        
        Args:
            config: 配置字典，包含JADX特定选项
        """
        super().__init__(config)
        # 验证并合并配置选项
        self._validate_config()
    
    def check_availability(self) -> bool:
        """
        检查JADX引擎是否可用
        
        Returns:
            bool: JADX引擎是否可用
        """
        try:
            # 检查JADX路径
            jadx_path = self._get_jadx_cli_path()
            if not os.path.exists(jadx_path):
                return False
                
            # 检查Java环境
            subprocess.run(["java", "-version"], capture_output=True, check=True)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _get_jadx_cli_path(self) -> str:
        """
        获取JADX CLI可执行文件路径
        
        Returns:
            str: JADX CLI路径
        
        Raises:
            ConfigurationError: 当无法确定JADX路径时
        """
        if self.config.get("cli_path"):
            return self.config.get("cli_path")
        
        # 尝试默认路径
        jadx_base = self.config.get("path")
        if not jadx_base:
            raise ConfigurationError("JADX工具路径未配置")
        
        # 根据操作系统尝试不同的脚本名称
        if os.name == "nt":  # Windows
            script_name = "jadx.bat"
        else:  # Linux/Mac
            script_name = "jadx"
        
        return os.path.join(jadx_base, script_name)
    
    def _merge_options(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        合并全局配置和局部选项
        
        Args:
            options: 局部选项字典
            
        Returns:
            Dict[str, Any]: 合并后的选项字典
        """
        merged = self.config.copy()
        if options:
            for key, value in options.items():
                if key in self.supported_options:
                    merged[key] = value
        return merged
    
    def _build_command(self, input_path: str, output_path: str, options: Dict[str, Any]) -> List[str]:
        """
        构建JADX命令行参数
        
        Args:
            input_path: 输入文件路径
            output_path: 输出目录路径
            options: 配置选项
            
        Returns:
            List[str]: 命令行参数列表
        """
        cmd = [self._get_jadx_cli_path(), input_path, "-d", output_path]
        
        # 添加配置的选项
        if options.get("deobfuscation"):
            cmd.extend(["--deobf"])
            cmd.extend(["--deobf-min", str(options.get("deobfuscation_min"))])
            cmd.extend(["--deobf-max", str(options.get("deobfuscation_max"))])
        
        if options.get("string_encryption"):
            cmd.extend(["--fs-string-refactor"])
        
        if options.get("show_inconsistent_code"):
            cmd.extend(["--show-bad-code"])
        
        if options.get("escape_unicode"):
            cmd.extend(["--escape-unicode"])
        
        if options.get("no_resources"):
            cmd.extend(["--no-res"])
        
        if options.get("no_debug_info"):
            cmd.extend(["--no-debug"])
        
        if options.get("no_class_debug_info"):
            cmd.extend(["--no-class-debug-info"])
        
        if options.get("no_rt"):
            cmd.extend(["--no-inline-anonymous"])
        
        if options.get("threads") > 0:
            cmd.extend(["-j", str(options.get("threads"))])
        
        cmd.extend(["-l", options.get("log_level")])
        
        return cmd
    
    def decompile_file(self, input_path: str, output_path: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Union[str, bool]]:
        """
        使用JADX反编译单个.class文件
        
        Args:
            input_path: 输入.class文件路径
            output_path: 输出.java文件路径
            options: 可选的配置选项字典
            
        Returns:
            Dict[str, Union[str, bool]]: 包含反编译结果信息的字典
            {
                "success": bool,  # 反编译是否成功
                "output_path": str,  # 输出文件路径
                "engine": str,  # 使用的引擎名称
                "errors": list  # 错误信息列表（如果有）
            }
            
        Raises:
            InvalidInputError: 输入文件无效
            ConfigurationError: 配置错误
        """
        # 合并选项
        merged_options = self._merge_options(options)
        
        # 验证输入
        try:
            self._validate_input_file(input_path)
        except Exception as e:
            raise InvalidInputError(f"无效的输入文件: {str(e)}")
            
        if not is_class_file(input_path):
            raise InvalidInputError(f"输入文件不是有效的.class文件: {input_path}")
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_path)
        if output_dir:
            ensure_directory(output_dir)
        
        errors = []
        temp_output_dir = None
        
        try:
            # JADX需要输出到目录，然后移动文件
            temp_output_dir = tempfile.mkdtemp()
            
            # 构建命令行参数
            cmd = self._build_command(input_path, temp_output_dir, merged_options)
            
            # 执行反编译命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # 检查是否成功
            if result.returncode != 0:
                errors.append(f"JADX反编译失败: {result.stderr}")
                return {
                    "success": False,
                    "output_path": output_path,
                    "engine": self.metadata.name,
                    "errors": errors
                }
            
            # 使用filename_utils处理文件名，支持匿名内部类
            input_filename = os.path.basename(input_path)
            
            # 解析类文件名，识别匿名内部类
            base_class_name, inner_class_id, is_anonymous = parse_java_class_filename(input_filename)
            
            # 获取应该生成的Java文件名
            expected_java_filename = get_java_file_name(input_filename)
            
            # 首先尝试查找基础类的Java文件（对于匿名内部类和命名内部类都适用）
            java_files = list(Path(temp_output_dir).glob(f"**/{expected_java_filename}"))
            
            if not java_files:
                # 如果找不到基础类文件，尝试查找任何包含基础类名的Java文件
                java_files = list(Path(temp_output_dir).glob(f"**/*{base_class_name}*.java"))
                
            if not java_files:
                # 如果仍然找不到，尝试查找任何.java文件
                java_files = list(Path(temp_output_dir).glob("**/*.java"))
            
            if java_files:
                # 使用找到的第一个Java文件
                shutil.copy2(java_files[0], output_path)
                return {
                    "success": True,
                    "output_path": output_path,
                    "engine": self.metadata.name,
                    "errors": []
                }
            else:
                errors.append("未生成反编译后的Java文件")
                return {
                    "success": False,
                    "output_path": output_path,
                    "engine": self.metadata.name,
                    "errors": errors
                }
                
        except Exception as e:
            errors.append(f"反编译文件时出错: {str(e)}")
            return {
                "success": False,
                "output_path": output_path,
                "engine": self.metadata.name,
                "errors": errors
            }
        finally:
            # 确保临时目录被清理
            if temp_output_dir and os.path.exists(temp_output_dir):
                shutil.rmtree(temp_output_dir)
    
    def decompile_jar(self, jar_path: str, output_dir: str, options: Optional[Dict[str, Any]] = None) -> Dict[str, Union[str, bool, List[str]]]:
        """
        使用JADX反编译JAR文件
        
        Args:
            jar_path: JAR文件路径
            output_dir: 输出目录
            options: 可选的配置选项字典，可包含exclude_patterns
            
        Returns:
            Dict[str, Union[str, bool, List[str]]]: 包含反编译结果信息的字典
            {
                "success": bool,  # 反编译是否成功
                "output_dir": str,  # 输出目录路径
                "engine": str,  # 使用的引擎名称
                "decompiled_files": List[str],  # 反编译的文件列表
                "errors": List[str]  # 错误信息列表（如果有）
            }
            
        Raises:
            InvalidInputError: 输入文件无效
            ConfigurationError: 配置错误
        """
        # 合并选项
        merged_options = self._merge_options(options)
        
        # 获取exclude_patterns（如果有）
        exclude_patterns = merged_options.pop("exclude_patterns", None)
        
        # 验证输入
        try:
            self._validate_input_file(jar_path)
        except Exception as e:
            raise InvalidInputError(f"无效的JAR文件: {str(e)}")
            
        if not (is_jar_file(jar_path) or is_apk_file(jar_path)):
            raise InvalidInputError(f"输入文件不是有效的JAR或APK文件: {jar_path}")
        
        # 确保输出目录存在
        ensure_directory(output_dir)
        
        errors = []
        
        try:
            # 构建命令行参数
            cmd = self._build_command(jar_path, output_dir, merged_options)
            
            # 执行反编译命令
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # 检查是否成功
            if result.returncode != 0:
                errors.append(f"JADX反编译JAR失败: {result.stderr}")
                return {
                    "success": False,
                    "output_dir": output_dir,
                    "engine": self.metadata.name,
                    "decompiled_files": [],
                    "errors": errors
                }
            
            # JADX会直接在输出目录生成反编译后的Java文件
            # 检查是否有Java文件生成
            java_files = list(Path(output_dir).glob("**/*.java"))
            java_files_str = [str(f) for f in java_files]
            
            if not java_files:
                errors.append("未生成反编译后的Java文件")
                return {
                    "success": False,
                    "output_dir": output_dir,
                    "engine": self.metadata.name,
                    "decompiled_files": [],
                    "errors": errors
                }
            
            # 如果有排除模式，删除匹配的文件
            if exclude_patterns:
                excluded_count = 0
                for pattern in exclude_patterns:
                    for file_path in list(Path(output_dir).glob(f"**/{pattern}")):
                        if file_path.exists():
                            file_path.unlink()
                            excluded_count += 1
                            if str(file_path) in java_files_str:
                                java_files_str.remove(str(file_path))
                if excluded_count > 0:
                    self._logger.info(f"排除了 {excluded_count} 个文件")
            
            return {
                "success": True,
                "output_dir": output_dir,
                "engine": self.metadata.name,
                "decompiled_files": java_files_str,
                "errors": []
            }
            
        except Exception as e:
            errors.append(f"反编译JAR文件时出错: {str(e)}")
            return {
                "success": False,
                "output_dir": output_dir,
                "engine": self.metadata.name,
                "decompiled_files": [],
                "errors": errors
            }
    
    def get_supported_options(self) -> Dict[str, EngineOption]:
        """
        获取JADX支持的配置选项
        
        Returns:
            Dict[str, EngineOption]: 支持的选项字典
        """
        return self.supported_options.copy()