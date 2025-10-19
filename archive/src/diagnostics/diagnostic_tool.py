#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
诊断工具模块
提供系统检查、配置验证和故障排除功能
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

from java_decompiler.config import ConfigManager, DEFAULT_CONFIG
from java_decompiler.logger import get_logger, setup_logger
from java_decompiler.file_utils import is_jar_file, ensure_directory
from java_decompiler.exceptions import JavaEnvironmentError, ToolNotFoundError

logger = get_logger("diagnostics")

class DiagnosticTool:
    """诊断工具类，提供系统检查和故障排除功能"""
    
    def __init__(self, config: Optional[ConfigManager] = None):
        """初始化诊断工具
        
        Args:
            config: 配置管理器实例，如果为None则创建默认配置
        """
        self.config = config or ConfigManager()
        self.results: Dict[str, Dict[str, Any]] = {}
    
    def run_full_diagnostic(self) -> Dict[str, Dict[str, Any]]:
        """运行完整诊断
        
        Returns:
            诊断结果字典
        """
        logger.info("开始运行完整诊断...")
        
        self.results = {
            "environment": self._check_environment(),
            "java": self._check_java_environment(),
            "tools": self._check_decompiler_tools(),
            "config": self._check_config(),
            "permissions": self._check_permissions(),
            "dependencies": self._check_dependencies()
        }
        
        logger.info("诊断完成")
        return self.results
    
    def _check_environment(self) -> Dict[str, Any]:
        """检查系统环境"""
        logger.info("检查系统环境...")
        
        result = {
            "success": True,
            "os": sys.platform,
            "python_version": sys.version,
            "architecture": "64-bit" if sys.maxsize > 2**32 else "32-bit",
            "issues": []
        }
        
        # 检查Python版本
        if sys.version_info < (3, 7):
            result["success"] = False
            result["issues"].append("Python版本过低，建议使用Python 3.7或更高版本")
        
        return result
    
    def _check_java_environment(self) -> Dict[str, Any]:
        """检查Java环境"""
        logger.info("检查Java环境...")
        
        result = {
            "available": False,
            "version": "未检测到",
            "issues": []
        }
        
        try:
            # 尝试运行java -version
            proc = subprocess.run(
                ["java", "-version"],
                capture_output=True,
                text=True
            )
            
            # Java版本信息输出到stderr
            if proc.stderr:
                version_output = proc.stderr
                # 解析版本信息
                import re
                match = re.search(r"version\s+\"([\d._]+)", version_output)
                if match:
                    result["version"] = match.group(1)
                    result["available"] = True
                else:
                    result["issues"].append("无法解析Java版本信息")
            else:
                result["issues"].append("Java命令执行成功但没有输出版本信息")
                
        except FileNotFoundError:
            result["issues"].append("未找到Java可执行文件，请确保Java已安装且在PATH环境变量中")
        except Exception as e:
            result["issues"].append(f"检查Java环境时出错: {str(e)}")
        
        return result
    
    def _check_decompiler_tools(self) -> Dict[str, Any]:
        """检查反编译工具"""
        logger.info("检查反编译工具...")
        
        result = {
            "tools": {},
            "issues": []
        }
        
        # 获取项目根目录
        package_dir = Path(os.path.dirname(os.path.dirname(__file__)))
        
        # 检查配置中的所有引擎
        for engine_name, engine_config in self.config.get("engines", {}).items():
            if not engine_config.get("enabled", True):
                continue
                
            tool_result = {
                "available": False,
                "path": engine_config.get("path", ""),
                "issues": []
            }
            
            # 获取实际路径
            tool_path = engine_config.get("path", "")
            if not os.path.isabs(tool_path):
                tool_path = os.path.join(package_dir, tool_path)
            
            # 检查文件是否存在
            if not os.path.exists(tool_path):
                tool_result["issues"].append(f"文件不存在: {tool_path}")
            # 检查文件类型
            elif not is_jar_file(tool_path):
                tool_result["issues"].append(f"不是有效的JAR文件: {tool_path}")
            else:
                tool_result["available"] = True
            
            result["tools"][engine_name] = tool_result
        
        return result
    
    def _check_config(self) -> Dict[str, Any]:
        """检查配置"""
        logger.info("检查配置...")
        
        result = {
            "success": True,
            "issues": []
        }
        
        # 检查必要配置项
        required_sections = ["engines", "output", "performance"]
        for section in required_sections:
            if section not in self.config.config:
                result["success"] = False
                result["issues"].append(f"配置缺少必要部分: {section}")
        
        # 检查是否有可用的引擎
        available_engines = False
        for engine_name, engine_config in self.config.get("engines", {}).items():
            if engine_config.get("enabled", True):
                available_engines = True
                break
        
        if not available_engines:
            result["success"] = False
            result["issues"].append("没有启用的反编译引擎")
        
        return result
    
    def _check_permissions(self) -> Dict[str, Any]:
        """检查权限"""
        logger.info("检查权限...")
        
        result = {
            "success": True,
            "issues": []
        }
        
        # 检查临时目录
        temp_dir = self.config.get("output.temp_dir", "./temp")
        try:
            ensure_directory(temp_dir)
            # 测试写入权限
            test_file = os.path.join(temp_dir, "test_write_permission.txt")
            with open(test_file, "w") as f:
                f.write("测试权限")
            os.remove(test_file)
        except Exception as e:
            result["success"] = False
            result["issues"].append(f"无法写入临时目录: {str(e)}")
        
        # 检查默认输出目录
        output_dir = self.config.get("output.default_dir", "./output")
        try:
            ensure_directory(output_dir)
        except Exception as e:
            result["success"] = False
            result["issues"].append(f"无法创建输出目录: {str(e)}")
        
        return result
    
    def _check_dependencies(self) -> Dict[str, Any]:
        """检查依赖项"""
        logger.info("检查依赖项...")
        
        result = {
            "success": True,
            "missing": [],
            "issues": []
        }
        
        # 检查可选依赖
        optional_deps = ["psutil"]
        for dep in optional_deps:
            try:
                __import__(dep)
            except ImportError:
                result["missing"].append(dep)
                result["issues"].append(f"可选依赖缺失: {dep}（会影响性能监控功能）")
        
        return result
    
    def print_report(self) -> None:
        """打印诊断报告"""
        print("\n" + "="*60)
        print("Java 反编译工具包 - 诊断报告")
        print("="*60)
        
        # 环境信息
        env = self.results.get("environment", {})
        print(f"\n1. 系统环境:")
        print(f"   - 操作系统: {env.get('os', '未知')}")
        print(f"   - Python版本: {env.get('python_version', '未知').split()[0]}")
        print(f"   - 架构: {env.get('architecture', '未知')}")
        for issue in env.get('issues', []):
            print(f"   ! {issue}")
        
        # Java环境
        java = self.results.get("java", {})
        print(f"\n2. Java环境:")
        status = "✓" if java.get('available', False) else "✗"
        print(f"   {status} Java: {java.get('version', '未检测到')}")
        for issue in java.get('issues', []):
            print(f"   ! {issue}")
        
        # 反编译工具
        tools = self.results.get("tools", {})
        print(f"\n3. 反编译工具:")
        for engine_name, engine_info in tools.get('tools', {}).items():
            status = "✓" if engine_info.get('available', False) else "✗"
            print(f"   {status} {engine_name}: {engine_info.get('path', '未知')}")
            for issue in engine_info.get('issues', []):
                print(f"     ! {issue}")
        for issue in tools.get('issues', []):
            print(f"   ! {issue}")
        
        # 配置
        config = self.results.get("config", {})
        print(f"\n4. 配置:")
        status = "✓" if config.get('success', False) else "✗"
        print(f"   {status} 配置检查")
        for issue in config.get('issues', []):
            print(f"   ! {issue}")
        
        # 权限
        permissions = self.results.get("permissions", {})
        print(f"\n5. 权限:")
        status = "✓" if permissions.get('success', False) else "✗"
        print(f"   {status} 权限检查")
        for issue in permissions.get('issues', []):
            print(f"   ! {issue}")
        
        # 依赖项
        deps = self.results.get("dependencies", {})
        print(f"\n6. 依赖项:")
        status = "✓" if deps.get('success', False) else "✗"
        print(f"   {status} 依赖检查")
        if deps.get('missing'):
            print(f"   - 缺失可选依赖: {', '.join(deps['missing'])}")
        for issue in deps.get('issues', []):
            print(f"   ! {issue}")
        
        # 总结
        print("\n" + "="*60)
        all_success = all([
            env.get('success', True),
            java.get('available', False),
            len(tools.get('tools', {})) > 0,
            config.get('success', True),
            permissions.get('success', True)
        ])
        
        if all_success:
            print("🎉 诊断通过！系统环境和配置正常。")
        else:
            print("❌ 诊断未通过，请根据上述问题进行修复。")
        print("="*60)

def check_environment() -> Tuple[bool, Dict[str, Any]]:
    """检查系统环境
    
    Returns:
        (是否正常, 环境信息字典)
    """
    diagnostic = DiagnosticTool()
    env_info = diagnostic._check_environment()
    java_info = diagnostic._check_java_environment()
    
    all_good = env_info.get('success', True) and java_info.get('available', False)
    
    return all_good, {
        "system": env_info,
        "java": java_info
    }

def validate_config(config: Optional[ConfigManager] = None) -> Tuple[bool, List[str]]:
    """验证配置文件
    
    Args:
        config: 配置管理器实例
    
    Returns:
        (是否有效, 错误信息列表)
    """
    diagnostic = DiagnosticTool(config)
    config_info = diagnostic._check_config()
    return config_info.get('success', False), config_info.get('issues', [])

def troubleshoot_issues(issue_type: str) -> List[str]:
    """故障排除助手
    
    Args:
        issue_type: 问题类型
    
    Returns:
        解决方案列表
    """
    solutions = {
        "java_not_found": [
            "1. 确保Java已安装（推荐Java 8或更高版本）",
            "2. 将Java安装目录添加到系统PATH环境变量中",
            "3. 重启命令行或IDE使环境变量生效",
            "4. 尝试指定Java可执行文件的完整路径"
        ],
        "tool_not_found": [
            "1. 确保反编译工具JAR文件存在于指定位置",
            "2. 检查文件权限是否正确",
            "3. 下载最新版本的反编译工具",
            "4. 在配置中指定正确的工具路径"
        ],
        "permission_denied": [
            "1. 确保有足够的权限读写输出目录",
            "2. 尝试以管理员/root权限运行程序",
            "3. 修改输出目录到用户有写权限的位置"
        ],
        "decompile_failed": [
            "1. 检查class文件是否损坏或格式不支持",
            "2. 尝试使用不同的反编译引擎",
            "3. 更新反编译工具到最新版本",
            "4. 查看详细日志了解具体错误"
        ]
    }
    
    return solutions.get(issue_type.lower(), ["未找到相关解决方案"])

# 命令行入口函数
def main():
    """诊断工具命令行入口"""
    setup_logger(level="INFO")
    diagnostic = DiagnosticTool()
    diagnostic.run_full_diagnostic()
    diagnostic.print_report()

if __name__ == "__main__":
    main()