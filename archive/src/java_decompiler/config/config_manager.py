#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理器
负责配置文件的加载、保存和验证
"""

import os
import json
import platform
from typing import Dict, Any, Optional, List
from pathlib import Path

from java_decompiler.exceptions import ConfigurationError
from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)

# 默认配置文件名
DEFAULT_CONFIG_FILE = "config.json"

# 配置文件搜索路径
CONFIG_SEARCH_PATHS = [
    ".",  # 当前目录
    "~/.java-decompiler",  # 用户主目录
]

class ConfigManager:
    """
    配置管理器类
    负责加载、验证和提供配置
    """
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，如果为None则使用默认配置
        """
        self.config_file = config_file
        self._config = get_default_config()
        
        # 如果提供了配置文件，则加载它
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def load_from_file(self, file_path: str) -> None:
        """
        从文件加载配置
        
        Args:
            file_path: 配置文件路径
            
        Raises:
            FileNotFoundError: 文件不存在
            ValueError: 文件格式错误或配置无效
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        # 根据文件扩展名确定格式
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if ext in ['.json']:
                    import json
                    user_config = json.load(f)
                elif ext in ['.yaml', '.yml']:
                    try:
                        import yaml
                        user_config = yaml.safe_load(f)
                    except ImportError:
                        raise ImportError("加载YAML配置需要pyyaml库，请先安装: pip install pyyaml")
                else:
                    raise ValueError(f"不支持的配置文件格式: {ext}")
            
            # 合并配置
            self._config = _merge_configs(self._config, user_config)
            
            # 验证配置
            validate_config(self._config)
            
            # 更新配置文件路径
            self.config_file = file_path
            
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            raise ValueError(f"配置文件格式错误: {str(e)}")
    
    def load_from_dict(self, config_dict: Dict[str, Any]) -> None:
        """
        从字典加载配置
        
        Args:
            config_dict: 配置字典
            
        Raises:
            ValueError: 配置无效
        """
        # 合并配置
        self._config = _merge_configs(self._config, config_dict)
        
        # 验证配置
        validate_config(self._config)
    
    def get_config(self) -> Dict[str, Any]:
        """
        获取当前配置
        
        Returns:
            Dict[str, Any]: 当前配置字典（深拷贝）
        """
        import copy
        return copy.deepcopy(self._config)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项
        支持使用点号分隔的路径，如 "logging.level"
        
        Args:
            key: 配置项键
            default: 默认值
            
        Returns:
            Any: 配置值或默认值
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置项
        支持使用点号分隔的路径，如 "logging.level"
        
        Args:
            key: 配置项键
            value: 配置值
            
        Raises:
            KeyError: 路径不存在且不能自动创建
        """
        keys = key.split('.')
        config = self._config
        
        # 遍历到倒数第二个键
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                raise KeyError(f"配置路径 {'.'.join(keys[:-1])} 不是字典")
            config = config[k]
        
        # 设置最后一个键的值
        config[keys[-1]] = value
        
        # 验证更新后的配置
        validate_config(self._config)
    
    def save_to_file(self, file_path: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            file_path: 文件路径，如果为None则使用当前配置文件路径
            
        Raises:
            ValueError: 文件格式不支持
            IOError: 保存文件失败
        """
        if file_path is None:
            if self.config_file is None:
                raise ValueError("未指定配置文件路径")
            file_path = self.config_file
        
        # 根据文件扩展名确定格式
        ext = os.path.splitext(file_path)[1].lower()
        
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                if ext in ['.json']:
                    import json
                    json.dump(self._config, f, ensure_ascii=False, indent=2)
                elif ext in ['.yaml', '.yml']:
                    try:
                        import yaml
                        yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
                    except ImportError:
                        raise ImportError("保存YAML配置需要pyyaml库，请先安装: pip install pyyaml")
                else:
                    raise ValueError(f"不支持的配置文件格式: {ext}")
                    
        except Exception as e:
            raise IOError(f"保存配置文件失败: {str(e)}")
    
    def reset_to_default(self) -> None:
        """
        重置为默认配置
        """
        self._config = get_default_config()


def get_default_config() -> Dict[str, Any]:
    """
    获取默认配置
    
    Returns:
        Dict[str, Any]: 默认配置字典
    """
    return {
        'version': '1.1.0',
        'engines': {
            'paths': {
                'cfr': None,
                'fernflower': None,
                'jadx': None
            },
            'cfr': {},
            'fernflower': {},
            'jadx': {}
        },
        'engine_management': {
            'timeout': 300,  # 默认超时时间（秒）
            'memory_limit': '4g',  # 默认内存限制
            'prefer_embedded': True  # 优先使用内嵌的引擎JAR文件
        },
        'output': {
            'format': 'java',  # 输出格式：java, json等
            'indent_size': 4,  # 缩进大小
            'line_width': 120  # 行宽度限制
        },
        'logging': {
            'level': 'INFO',  # 日志级别
            'file': None  # 日志文件路径，None表示只输出到控制台
        },
        'performance': {
            'cache_enabled': True,  # 是否启用缓存
            'cache_dir': None  # 缓存目录，None表示使用默认目录
        }
    }


def load_config(config_file: Optional[str] = None) -> Dict[str, Any]:
    """
    加载配置文件
    
    Args:
        config_file: 配置文件路径，如果为None则尝试查找默认配置文件
        
    Returns:
        Dict: 配置字典
        
    Raises:
        ConfigurationError: 配置文件格式错误或无法加载
    """
    # 从默认配置开始
    config = get_default_config()
    
    # 如果没有指定配置文件路径，尝试查找
    if config_file is None:
        config_file = _find_config_file()
    
    # 如果找到配置文件，加载它
    if config_file and os.path.exists(config_file):
        logger.info(f"加载配置文件: {config_file}")
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                user_config = json.load(f)
                
            # 深度合并配置
            config = _merge_configs(config, user_config)
            
            # 验证配置
            validate_config(config)
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigurationError(f"配置文件格式错误: {str(e)}")
        except Exception as e:
            raise ConfigurationError(f"加载配置文件失败: {str(e)}")
    else:
        logger.info("未找到配置文件，使用默认配置")
        return config


def save_config(config: Dict[str, Any], config_file: Optional[str] = None) -> None:
    """
    保存配置到文件
    
    Args:
        config: 要保存的配置字典
        config_file: 保存路径，如果为None则保存到默认位置
        
    Raises:
        ConfigurationError: 保存配置失败
    """
    # 验证配置
    validate_config(config)
    
    # 如果没有指定文件路径，使用默认位置
    if config_file is None:
        config_file = os.path.join(_get_user_config_dir(), DEFAULT_CONFIG_FILE)
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # 保存配置
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        logger.info(f"配置已保存到: {config_file}")
        
    except Exception as e:
        raise ConfigurationError(f"保存配置失败: {str(e)}")


def validate_config(config: Dict[str, Any]) -> None:
    """
    验证配置结构的有效性
    
    Args:
        config: 要验证的配置字典
        
    Raises:
        ValueError: 当配置无效时抛出
        TypeError: 当配置类型错误时抛出
    """
    if not isinstance(config, dict):
        raise TypeError("配置必须是字典类型")
    
    # 检查必要的顶级键
    if 'version' not in config:
        raise ValueError("配置缺少必需的 'version' 键")
    
    # 不再强制要求engines键存在
    if 'engines' in config:
        engines = config['engines']
        if not isinstance(engines, dict):
            raise TypeError("'engines' 配置必须是字典类型")
        
        # 检查paths子字典（如果存在）
        if 'paths' in engines:
            if not isinstance(engines['paths'], dict):
                raise TypeError("'engines.paths' 配置必须是字典类型")
        
        # 验证每个引擎配置都是字典
        for engine_name, engine_config in engines.items():
            if engine_name != 'paths' and not isinstance(engine_config, dict):
                raise TypeError(f"引擎 '{engine_name}' 的配置必须是字典类型")
    
    # 验证其他重要配置部分
    if 'engine_management' in config and not isinstance(config['engine_management'], dict):
        raise TypeError("'engine_management' 配置必须是字典类型")


def _find_config_file() -> Optional[str]:
    """
    在默认位置查找配置文件
    
    Returns:
        Optional[str]: 找到的配置文件路径，如果没有找到则返回None
    """
    for path in CONFIG_SEARCH_PATHS:
        # 扩展~为用户主目录
        expanded_path = os.path.expanduser(path)
        
        # 检查目录或文件
        if os.path.isdir(expanded_path):
            config_path = os.path.join(expanded_path, DEFAULT_CONFIG_FILE)
            if os.path.exists(config_path):
                return config_path
        elif os.path.isfile(expanded_path):
            return expanded_path
    
    return None


def _get_user_config_dir() -> str:
    """
    获取用户配置目录
    
    Returns:
        str: 用户配置目录路径
    """
    if platform.system() == "Windows":
        # Windows使用AppData目录
        return os.path.join(os.path.expanduser("~"), "AppData", "Local", "java-decompiler")
    else:
        # Unix/Linux/Mac使用~/.config目录
        return os.path.join(os.path.expanduser("~"), ".java-decompiler")


def _merge_configs(default_config: Dict[str, Any], user_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    深度合并两个配置字典
    
    Args:
        default_config: 默认配置字典
        user_config: 用户配置字典
        
    Returns:
        Dict[str, Any]: 合并后的配置字典
    """
    merged = default_config.copy()
    
    for key, value in user_config.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # 特殊处理engines配置，确保兼容性
            if key == 'engines':
                # 确保merged['engines']存在paths子字典
                if 'paths' not in merged['engines']:
                    merged['engines']['paths'] = {}
                
                # 遍历用户提供的引擎配置
                for engine_name, engine_config in value.items():
                    if engine_name == 'paths':
                        # 合并paths字典
                        merged['engines']['paths'].update(engine_config)
                    else:
                        # 处理引擎特定配置
                        if engine_name not in merged['engines']:
                            merged['engines'][engine_name] = {}
                        
                        # 检查旧格式配置（引擎路径直接在引擎配置中）
                        if isinstance(engine_config, dict) and 'path' in engine_config:
                            # 将路径移至paths字典
                            merged['engines']['paths'][engine_name] = engine_config['path']
                            # 移除原配置中的path键
                            engine_config_copy = engine_config.copy()
                            engine_config_copy.pop('path')
                            # 合并剩余配置
                            merged['engines'][engine_name].update(engine_config_copy)
                        else:
                            # 直接合并引擎特定配置
                            merged['engines'][engine_name].update(engine_config)
            else:
                # 普通字典深度合并
                merged[key] = _merge_configs(merged[key], value)
        else:
            # 非字典或不在默认配置中，直接覆盖
            merged[key] = value
    
    return merged


def get_config_template() -> Dict[str, Any]:
    """
    获取配置模板（不包含默认值的注释版本）
    
    Returns:
        Dict: 配置模板
    """
    return {
        "version": "1.0.0",
        "threads": 0,  # 0表示自动检测CPU核心数
        "max_retries": 1,  # 失败后的重试次数
        "retry_delay": 1.0,  # 重试间隔（秒）
        
        "logging": {
            "level": "INFO",  # DEBUG, INFO, WARNING, ERROR
            "file": None,  # 日志文件路径，None表示不输出到文件
            "console": True,  # 是否输出到控制台
            "file_format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "console_format": "%(levelname)s: %(message)s"
        },
        
        "engines": {
            "cfr": {
                "path": "path/to/cfr.jar",  # CFR JAR文件路径
                "options": {}  # CFR额外选项
            },
            "fernflower": {
                "path": "path/to/fernflower.jar",  # FernFlower JAR文件路径
                "dgs": True,  # decompile generic signatures
                "hdc": False,  # hide bridge methods
                "hes": False,  # hide synthetic class members
                "ind": 4,      # indent expression with this number of spaces
                "log": False,  # write log file
                "mpm": False,  # maximize performance
                "ren": "0",    # rename ambiguous (not java) identifiers
                "urc": True,   # use raw class files
                "vac": False,  # verify that anonymous classes can be loaded
                "var": 0,      # variable for variable name generation policy
                "nns": True,   # allow to not generate a constructor for non-static inner classes
                "noe": False,  # do not expand the loaded class files
                "tcs": False,  # translate classfiles into synthetic classfiles
                "pll": True,   # decompile methods with implementation
                "lit": False   # literals pool
            },
            "jadx": {
                "path": "path/to/jadx",  # JADX安装目录
                "cli_path": None,  # JADX CLI可执行文件路径，如果为None则自动查找
                "deobfuscation": False,  # 启用反混淆
                "deobfuscation_min": 3,  # 反混淆最小标识符长度
                "deobfuscation_max": 64,  # 反混淆最大标识符长度
                "string_encryption": False,  # 尝试解码加密字符串
                "show_inconsistent_code": False,  # 显示不一致的代码
                "escape_unicode": False,  # 转义Unicode字符
                "no_resources": False,  # 不反编译资源
                "no_debug_info": False,  # 忽略调试信息
                "no_class_debug_info": False,  # 忽略类调试信息
                "no_rt": False,  # 不添加运行时异常检查
                "threads": 0,  # 线程数，0表示自动检测
                "log_level": "WARN"  # 日志级别
            }
        },
        
        "output": {
            "overwrite": False,  # 是否覆盖已存在的文件
            "recursive": True,  # 是否递归处理子目录
            "format": "java"  # 输出格式
        }
    }