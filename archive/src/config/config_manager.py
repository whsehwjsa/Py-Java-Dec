#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
配置管理器
负责加载、保存和管理用户配置
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

# 默认配置
DEFAULT_CONFIG = {
    # 反编译引擎配置
    'engine': {
        'default': 'cfr',  # 默认引擎: cfr, fernflower, jadx
        'cfr_path': '',    # CFR JAR文件路径
        'fernflower_path': '',  # FernFlower JAR文件路径
        'jadx_path': '',  # JADX可执行文件或JAR文件路径
    },
    
    # 反编译选项
    'options': {
        'deobfuscate': False,      # 是否启用反混淆
        'threads': 4,              # 默认线程数
        'timeout': 300,            # 默认超时时间(秒)
        'verbose': False,          # 是否显示详细信息
    },
    
    # 各引擎特定选项
    'engines': {
        'cfr': {
            'options': ''  # CFR特定选项
        },
        'fernflower': {
            'options': ''  # FernFlower特定选项
        },
        'jadx': {
            'options': ''  # JADX特定选项
        }
    },
    
    # 界面相关配置
    'ui': {
        'progress_bar': True,      # 是否显示进度条
        'color_output': True       # 是否使用彩色输出
    }
}

class ConfigManager:
    """
    配置管理器类
    处理配置文件的加载、保存和访问
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径，如果为None则使用默认路径
        """
        # 如果未指定配置文件路径，则使用默认路径
        if config_path is None:
            # 在用户目录下创建配置目录
            config_dir = Path.home() / '.java_decompiler'
            config_dir.mkdir(parents=True, exist_ok=True)
            self.config_path = str(config_dir / 'config.json')
        else:
            self.config_path = config_path
        
        # 初始化配置
        self.config = DEFAULT_CONFIG.copy()
        
        # 尝试加载现有配置
        self.load()
    
    def load(self) -> bool:
        """
        加载配置文件
        
        Returns:
            bool: 是否成功加载配置文件
        """
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    # 合并加载的配置和默认配置
                    self._merge_config(self.config, loaded_config)
                return True
        except Exception as e:
            print(f"警告: 无法加载配置文件 {self.config_path}: {e}")
        
        return False
    
    def save(self) -> bool:
        """
        保存配置到文件
        
        Returns:
            bool: 是否成功保存配置文件
        """
        try:
            # 确保配置目录存在
            config_dir = os.path.dirname(self.config_path)
            if config_dir:
                os.makedirs(config_dir, exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"警告: 无法保存配置文件 {self.config_path}: {e}")
            return False
    
    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置项的值
        
        Args:
            key_path: 配置键路径，使用点表示法，如 'engine.default'
            default: 如果配置项不存在则返回的默认值
            
        Returns:
            Any: 配置项的值或默认值
        """
        keys = key_path.split('.')
        value = self.config
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path: str, value: Any) -> bool:
        """
        设置配置项的值
        
        Args:
            key_path: 配置键路径，使用点表示法，如 'engine.default'
            value: 要设置的值
            
        Returns:
            bool: 是否成功设置配置项
        """
        keys = key_path.split('.')
        config = self.config
        
        try:
            # 遍历到倒数第二个键
            for key in keys[:-1]:
                if key not in config:
                    config[key] = {}
                config = config[key]
            
            # 设置最后一个键的值
            config[keys[-1]] = value
            return True
        except (KeyError, TypeError):
            return False
    
    def reset(self) -> None:
        """
        重置为默认配置
        """
        self.config = DEFAULT_CONFIG.copy()
    
    def _merge_config(self, base: Dict[str, Any], update: Dict[str, Any]) -> None:
        """
        递归合并配置字典
        
        Args:
            base: 基础配置字典
            update: 要合并的配置字典
        """
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                # 如果两边都是字典，则递归合并
                self._merge_config(base[key], value)
            else:
                # 否则直接替换
                base[key] = value