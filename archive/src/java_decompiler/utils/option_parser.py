#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
选项解析工具函数
处理命令行选项、配置选项等
"""

import re
from typing import Any, Dict, List, Union, Tuple

from java_decompiler.logger.logger import get_logger

logger = get_logger(__name__)


def parse_key_value_string(value: str, delimiter: str = '=', 
                          pair_delimiter: str = ',') -> Dict[str, str]:
    """
    解析键值对字符串为字典
    格式: key1=value1,key2=value2
    
    Args:
        value: 键值对字符串
        delimiter: 键值之间的分隔符
        pair_delimiter: 键值对之间的分隔符
        
    Returns:
        Dict[str, str]: 解析后的字典
    """
    result = {}
    
    if not value:
        return result
    
    # 分割键值对
    pairs = value.split(pair_delimiter)
    
    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue
            
        # 分割键和值
        if delimiter in pair:
            key, val = pair.split(delimiter, 1)
            key = key.strip()
            val = val.strip()
            
            # 处理引号包围的值
            if (val.startswith('"') and val.endswith('"')) or \
               (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
                
            result[key] = val
        else:
            # 如果没有分隔符，将整个字符串作为键，值为空字符串
            result[pair.strip()] = ''
    
    return result

def format_option_string(options: Dict[str, Any], delimiter: str = '=',
                        pair_delimiter: str = ',') -> str:
    """
    将字典格式化为键值对字符串
    
    Args:
        options: 选项字典
        delimiter: 键值之间的分隔符
        pair_delimiter: 键值对之间的分隔符
        
    Returns:
        str: 格式化后的字符串
    """
    pairs = []
    
    for key, value in options.items():
        # 将值转换为字符串
        str_value = str(value)
        
        # 如果值包含分隔符，使用引号包围
        if delimiter in str_value or pair_delimiter in str_value or ' ' in str_value:
            # 转义内部引号
            str_value = str_value.replace('"', '\\"')
            str_value = f'"{str_value}"'
            
        pairs.append(f"{key}{delimiter}{str_value}")
    
    return pair_delimiter.join(pairs)

def parse_memory_size(size_str: str) -> int:
    """
    解析内存大小字符串为字节数
    支持的格式: 1024, 1024b, 1k, 1m, 1g, 1t
    
    Args:
        size_str: 内存大小字符串
        
    Returns:
        int: 字节数
        
    Raises:
        ValueError: 格式不正确
    """
    # 定义单位转换系数
    units = {
        'b': 1,
        'k': 1024,
        'm': 1024 * 1024,
        'g': 1024 * 1024 * 1024,
        't': 1024 * 1024 * 1024 * 1024
    }
    
    # 正则表达式匹配格式
    match = re.match(r'^\s*(\d+(?:\.\d+)?)\s*([bBkKmMgGtT])?\s*$', size_str)
    
    if not match:
        raise ValueError(f"无效的内存大小格式: {size_str}")
    
    # 提取数值和单位
    value = float(match.group(1))
    unit = match.group(2).lower() if match.group(2) else 'b'
    
    # 转换为字节数
    bytes_value = int(value * units[unit])
    
    return bytes_value

def validate_option_name(name: str) -> bool:
    """
    验证选项名称是否合法
    合法格式: 字母、数字、下划线，且以字母开头
    
    Args:
        name: 选项名称
        
    Returns:
        bool: 是否合法
    """
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    return bool(re.match(pattern, name))

def normalize_option_name(name: str, separator: str = '-') -> str:
    """
    标准化选项名称
    将分隔符替换为下划线，并转换为小写
    
    Args:
        name: 原始选项名称
        separator: 要替换的分隔符
        
    Returns:
        str: 标准化后的选项名称
    """
    # 替换分隔符为下划线
    normalized = name.replace(separator, '_')
    # 转换为小写
    normalized = normalized.lower()
    # 移除多余的下划线
    normalized = re.sub(r'_+', '_', normalized)
    
    return normalized

def parse_boolean_value(value: Union[str, bool, None]) -> bool:
    """
    解析布尔值
    
    Args:
        value: 输入值
        
    Returns:
        bool: 解析后的布尔值
    """
    # 如果已经是布尔值，直接返回
    if isinstance(value, bool):
        return value
    
    # 如果是None，返回False
    if value is None:
        return False
    
    # 如果是字符串，转换为小写并判断
    if isinstance(value, str):
        value_lower = value.lower().strip()
        true_values = ['true', 'yes', 'y', '1', 'on']
        false_values = ['false', 'no', 'n', '0', 'off']
        
        if value_lower in true_values:
            return True
        elif value_lower in false_values:
            return False
        else:
            logger.warning(f"无法解析布尔值: '{value}'，默认返回False")
            return False
    
    # 其他类型，转换为布尔值
    return bool(value)

def parse_int_value(value: Union[str, int, None], default: int = 0, 
                   min_value: int = None, max_value: int = None) -> int:
    """
    解析整数值
    
    Args:
        value: 输入值
        default: 默认值
        min_value: 最小值
        max_value: 最大值
        
    Returns:
        int: 解析后的整数值
    """
    # 如果是None，返回默认值
    if value is None:
        return default
    
    # 如果已经是整数，直接返回
    if isinstance(value, int):
        result = value
    else:
        # 尝试转换为整数
        try:
            result = int(value)
        except (ValueError, TypeError):
            logger.warning(f"无法解析整数值: '{value}'，使用默认值 {default}")
            return default
    
    # 检查范围
    if min_value is not None and result < min_value:
        logger.warning(f"整数值 {result} 小于最小值 {min_value}，使用 {min_value}")
        return min_value
    
    if max_value is not None and result > max_value:
        logger.warning(f"整数值 {result} 大于最大值 {max_value}，使用 {max_value}")
        return max_value
    
    return result

def merge_options(default_options: Dict[str, Any], 
                 user_options: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并默认选项和用户选项
    用户选项优先级高于默认选项
    
    Args:
        default_options: 默认选项
        user_options: 用户选项
        
    Returns:
        Dict[str, Any]: 合并后的选项
    """
    # 创建默认选项的副本
    merged = default_options.copy()
    
    # 更新用户选项
    for key, value in user_options.items():
        # 如果值是字典，递归合并
        if (key in merged and isinstance(merged[key], dict) and 
            isinstance(value, dict)):
            merged[key] = merge_options(merged[key], value)
        else:
            merged[key] = value
    
    return merged

def filter_options(options: Dict[str, Any], 
                  allowed_keys: List[str]) -> Dict[str, Any]:
    """
    过滤选项，只保留允许的键
    
    Args:
        options: 原始选项
        allowed_keys: 允许的键列表
        
    Returns:
        Dict[str, Any]: 过滤后的选项
    """
    return {k: v for k, v in options.items() if k in allowed_keys}

def parse_enum_value(value: Union[str, Any], enum_type: Any, 
                    case_sensitive: bool = False) -> Any:
    """
    解析枚举值
    
    Args:
        value: 输入值
        enum_type: 枚举类型
        case_sensitive: 是否大小写敏感
        
    Returns:
        Any: 解析后的枚举值，如果无法解析则返回None
    """
    # 如果已经是枚举类型的实例，直接返回
    if isinstance(value, enum_type):
        return value
    
    # 如果是字符串，尝试匹配枚举值
    if isinstance(value, str):
        try:
            if case_sensitive:
                return enum_type[value]
            else:
                # 转换为大写并尝试匹配
                value_upper = value.upper()
                return enum_type[value_upper]
        except (KeyError, ValueError):
            # 尝试直接使用字符串值创建枚举
            try:
                return enum_type(value)
            except (ValueError, TypeError):
                logger.warning(f"无法解析枚举值: '{value}' 为 {enum_type.__name__}")
                return None
    
    return None

def extract_option_groups(options: Dict[str, str], 
                         prefix: str = '') -> Tuple[Dict[str, str], Dict[str, str]]:
    """
    从选项字典中提取特定前缀的选项组
    
    Args:
        options: 原始选项字典
        prefix: 前缀，默认为空字符串
        
    Returns:
        Tuple[Dict[str, str], Dict[str, str]]: 
            - 第一个字典包含带前缀的选项（移除前缀）
            - 第二个字典包含剩余的选项
    """
    group_options = {}
    remaining_options = {}
    
    for key, value in options.items():
        if key.startswith(prefix):
            # 移除前缀
            new_key = key[len(prefix):] if len(prefix) < len(key) else key
            group_options[new_key] = value
        else:
            remaining_options[key] = value
    
    return group_options, remaining_options