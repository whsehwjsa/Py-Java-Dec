#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
诊断工具实现
"""

import os
import sys
import subprocess
import platform
import json
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime

from java_decompiler.logger.logger import get_logger
from java_decompiler.core.decompiler_manager import get_available_engines
from java_decompiler.utils.path_utils import is_safe_path

logger = get_logger(__name__)

def check_system_environment() -> Dict[str, Any]:
    """
    检查系统环境
    
    Returns:
        Dict[str, Any]: 系统环境信息
    """
    env_info = {
        'system': platform.system(),
        'system_version': platform.version(),
        'architecture': platform.architecture(),
        'python_version': platform.python_version(),
        'python_executable': sys.executable,
        'os_name': os.name,
        'current_directory': os.getcwd(),
        'user_home': os.path.expanduser('~'),
        'path_env': os.environ.get('PATH', '').split(os.pathsep)
    }
    
    # 检查临时目录
    try:
        temp_dir = os.environ.get('TEMP', os.environ.get('TMP', '/tmp'))
        env_info['temp_directory'] = temp_dir
        env_info['temp_directory_writable'] = os.access(temp_dir, os.W_OK)
    except Exception as e:
        env_info['temp_directory_error'] = str(e)
    
    # 检查权限
    env_info['current_directory_writable'] = os.access(os.getcwd(), os.W_OK)
    
    logger.debug(f"系统环境检查完成: {env_info['system']} {env_info['system_version']}, "
                f"Python {env_info['python_version']}")
    
    return env_info

def detect_java_runtime() -> Dict[str, Any]:
    """
    检测Java运行时环境
    
    Returns:
        Dict[str, Any]: Java运行时信息
    """
    java_info = {
        'available': False,
        'version': None,
        'path': None,
        'bitness': None,
        'vendor': None
    }
    
    # 尝试查找java可执行文件
    java_candidates = ['java']
    if platform.system() == 'Windows':
        java_candidates.append('java.exe')
    
    java_path = None
    for candidate in java_candidates:
        try:
            # 使用subprocess查找java路径
            if platform.system() == 'Windows':
                cmd = ['where', candidate]
            else:
                cmd = ['which', candidate]
                
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                java_path = result.stdout.strip().split('\n')[0]
                break
        except Exception as e:
            logger.debug(f"查找Java路径失败: {str(e)}")
            continue
    
    if java_path:
        java_info['path'] = java_path
        
        # 尝试获取Java版本信息
        try:
            result = subprocess.run(
                [java_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            # Java版本信息通常输出到stderr
            version_output = result.stderr or result.stdout
            
            # 解析Java版本
            import re
            version_match = re.search(r'version\s+["\'](\d+(?:\.\d+)*)(?:_\d+)?["\']', version_output)
            if version_match:
                java_info['version'] = version_match.group(1)
            
            # 解析Java供应商
            vendor_match = re.search(r'(?:OpenJDK|Java)\s+Runtime\s+Environment\s+["\']([^"\']+)["\']', version_output)
            if vendor_match:
                java_info['vendor'] = vendor_match.group(1)
            
            # 检查64位还是32位
            if '64-Bit' in version_output or 'amd64' in version_output:
                java_info['bitness'] = '64-bit'
            elif '32-Bit' in version_output or 'i386' in version_output:
                java_info['bitness'] = '32-bit'
            
            java_info['available'] = True
            logger.debug(f"检测到Java运行时: {java_info['version']} ({java_info['bitness']}), "
                        f"供应商: {java_info['vendor']}")
            
        except Exception as e:
            logger.warning(f"获取Java版本信息失败: {str(e)}")
    else:
        logger.warning("未检测到Java运行时环境")
    
    return java_info

def verify_engine_availability(engine_names: Optional[List[str]] = None) -> Dict[str, Dict[str, Any]]:
    """
    验证反编译引擎的可用性
    
    Args:
        engine_names: 要验证的引擎名称列表，如果为None则验证所有引擎
        
    Returns:
        Dict[str, Dict[str, Any]]: 引擎可用性信息
    """
    result = {}
    
    # 获取所有可用引擎
    all_engines = get_available_engines()
    
    # 确定要验证的引擎
    engines_to_verify = engine_names if engine_names else list(all_engines.keys())
    
    for engine_name in engines_to_verify:
        engine_info = {
            'available': False,
            'reason': '未知引擎',
            'engine_class': None,
            'jar_path': None
        }
        
        if engine_name not in all_engines:
            result[engine_name] = engine_info
            continue
        
        try:
            # 获取引擎类
            engine_class = all_engines[engine_name]
            engine_info['engine_class'] = engine_class.__name__
            
            # 创建引擎实例并检查可用性
            engine_instance = engine_class()
            is_available = engine_instance.check_availability()
            
            if is_available:
                engine_info['available'] = True
                engine_info['reason'] = '可用'
                
                # 尝试获取JAR路径
                if hasattr(engine_instance, '_jar_path'):
                    engine_info['jar_path'] = engine_instance._jar_path
                
                logger.debug(f"引擎 {engine_name} 可用")
            else:
                engine_info['available'] = False
                engine_info['reason'] = 'JAR文件不存在或不可访问'
                logger.debug(f"引擎 {engine_name} 不可用: {engine_info['reason']}")
                
        except Exception as e:
            engine_info['available'] = False
            engine_info['reason'] = f"初始化失败: {str(e)}"
            logger.warning(f"验证引擎 {engine_name} 时出错: {str(e)}")
        
        result[engine_name] = engine_info
    
    return result

def check_file_accessibility(file_path: str) -> Dict[str, Any]:
    """
    检查文件的可访问性
    
    Args:
        file_path: 文件路径
        
    Returns:
        Dict[str, Any]: 文件访问信息
    """
    file_info = {
        'path': file_path,
        'exists': False,
        'is_file': False,
        'is_directory': False,
        'readable': False,
        'writable': False,
        'executable': False,
        'size': None,
        'safe_path': False,
        'error': None
    }
    
    try:
        # 检查路径安全性
        file_info['safe_path'] = is_safe_path(file_path)
        
        # 检查文件是否存在
        file_info['exists'] = os.path.exists(file_path)
        
        if file_info['exists']:
            file_info['is_file'] = os.path.isfile(file_path)
            file_info['is_directory'] = os.path.isdir(file_path)
            file_info['readable'] = os.access(file_path, os.R_OK)
            file_info['writable'] = os.access(file_path, os.W_OK)
            file_info['executable'] = os.access(file_path, os.X_OK)
            
            if file_info['is_file']:
                file_info['size'] = os.path.getsize(file_path)
                
    except Exception as e:
        file_info['error'] = str(e)
        logger.warning(f"检查文件访问性时出错 '{file_path}': {str(e)}")
    
    return file_info

def run_diagnostics() -> Dict[str, Any]:
    """
    运行完整的诊断测试
    
    Returns:
        Dict[str, Any]: 诊断结果
    """
    logger.info("开始运行诊断测试...")
    
    diagnostics = {
        'timestamp': datetime.now().isoformat(),
        'system_environment': check_system_environment(),
        'java_runtime': detect_java_runtime(),
        'engine_availability': verify_engine_availability(),
        'dependencies': check_python_dependencies(),
        'summary': {
            'passed_checks': 0,
            'failed_checks': 0,
            'warnings': []
        }
    }
    
    # 计算检查结果
    checks = 0
    passed = 0
    warnings = []
    
    # 检查Java运行时
    checks += 1
    if diagnostics['java_runtime']['available']:
        passed += 1
    else:
        warnings.append("未检测到Java运行时环境，反编译功能将不可用")
    
    # 检查引擎可用性
    engine_available_count = sum(1 for e in diagnostics['engine_availability'].values() if e['available'])
    if engine_available_count > 0:
        passed += 1
        checks += 1
    else:
        warnings.append("没有可用的反编译引擎")
        checks += 1
    
    # 更新摘要
    diagnostics['summary']['passed_checks'] = passed
    diagnostics['summary']['failed_checks'] = checks - passed
    diagnostics['summary']['warnings'] = warnings
    
    logger.info(f"诊断测试完成: 通过 {passed}/{checks} 项检查")
    
    return diagnostics

def check_python_dependencies() -> Dict[str, Any]:
    """
    检查Python依赖
    
    Returns:
        Dict[str, Any]: 依赖信息
    """
    dependencies = {
        'installed': [],
        'missing': []
    }
    
    # 检查可选依赖
    optional_deps = [
        ('psutil', '系统监控'),
        ('python-magic', '文件类型检测')
    ]
    
    for module_name, description in optional_deps:
        try:
            __import__(module_name)
            dependencies['installed'].append({
                'name': module_name,
                'description': description,
                'version': '已安装'
            })
        except ImportError:
            dependencies['missing'].append({
                'name': module_name,
                'description': description
            })
    
    return dependencies

def generate_diagnostic_report(output_file: str) -> bool:
    """
    生成诊断报告
    
    Args:
        output_file: 输出文件路径
        
    Returns:
        bool: 是否成功生成报告
    """
    try:
        # 运行诊断
        diagnostics = run_diagnostics()
        
        # 确保输出目录存在
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
        
        # 保存报告
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(diagnostics, f, indent=2, ensure_ascii=False)
        
        logger.info(f"诊断报告已生成: {output_file}")
        
        # 同时输出摘要到控制台
        _print_diagnostic_summary(diagnostics)
        
        return True
        
    except Exception as e:
        logger.error(f"生成诊断报告失败: {str(e)}")
        return False

def _print_diagnostic_summary(diagnostics: Dict[str, Any]) -> None:
    """
    打印诊断摘要到控制台
    
    Args:
        diagnostics: 诊断结果
    """
    print("\n=== Java反编译工具诊断报告 ===")
    print(f"生成时间: {diagnostics['timestamp']}")
    print(f"系统: {diagnostics['system_environment']['system']} {diagnostics['system_environment']['system_version']}")
    print(f"Python版本: {diagnostics['system_environment']['python_version']}")
    
    # Java运行时信息
    java_info = diagnostics['java_runtime']
    if java_info['available']:
        print(f"Java运行时: {java_info['version']} ({java_info['bitness']}) - {java_info['vendor']}")
    else:
        print("Java运行时: 未检测到 [警告]")
    
    # 引擎可用性
    print("\n反编译引擎状态:")
    for engine_name, engine_info in diagnostics['engine_availability'].items():
        status = "✓ 可用" if engine_info['available'] else "✗ 不可用"
        print(f"  {engine_name}: {status}")
    
    # 依赖信息
    deps = diagnostics['dependencies']
    if deps['missing']:
        print("\n缺少可选依赖:")
        for dep in deps['missing']:
            print(f"  - {dep['name']}: {dep['description']}")
    
    # 警告
    if diagnostics['summary']['warnings']:
        print("\n警告:")
        for warning in diagnostics['summary']['warnings']:
            print(f"  - {warning}")
    
    print(f"\n检查结果: 通过 {diagnostics['summary']['passed_checks']}/"
          f"{diagnostics['summary']['passed_checks'] + diagnostics['summary']['failed_checks']} 项检查")
    print("============================\n")