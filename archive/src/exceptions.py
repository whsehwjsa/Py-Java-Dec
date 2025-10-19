#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自定义异常模块
定义项目中使用的各种自定义异常类
"""

class DecompilerError(Exception):
    """
    反编译工具的基础异常类
    """
    
    def __init__(self, message: str, error_code: int = 1):
        """
        初始化异常
        
        Args:
            message: 异常消息
            error_code: 错误代码
        """
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class JavaEnvironmentError(DecompilerError):
    """
    Java环境相关错误
    """
    
    def __init__(self, message: str = "Java环境未正确配置", error_code: int = 101):
        super().__init__(message, error_code)

class ToolNotFoundError(DecompilerError):
    """
    反编译工具未找到错误
    """
    
    def __init__(self, tool_name: str, message: str = None, error_code: int = 102):
        """
        初始化工具未找到异常
        
        Args:
            tool_name: 工具名称
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            message = f"未找到{tool_name}工具，请下载并配置正确的路径"
        self.tool_name = tool_name
        super().__init__(message, error_code)

class DecompilationError(DecompilerError):
    """
    反编译过程中的错误
    """
    
    def __init__(self, file_path: str, message: str = None, error_code: int = 103):
        """
        初始化反编译错误异常
        
        Args:
            file_path: 反编译失败的文件路径
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            message = f"反编译文件 {file_path} 时发生错误"
        self.file_path = file_path
        super().__init__(message, error_code)

class TimeoutError(DecompilationError):
    """
    反编译超时错误
    """
    
    def __init__(self, file_path: str, timeout: int, error_code: int = 104):
        """
        初始化超时错误异常
        
        Args:
            file_path: 反编译超时的文件路径
            timeout: 超时时间(秒)
            error_code: 错误代码
        """
        message = f"反编译文件 {file_path} 超时 (超过 {timeout} 秒)"
        self.timeout = timeout
        super().__init__(file_path, message, error_code)

class InvalidInputError(DecompilerError):
    """
    无效输入错误
    """
    
    def __init__(self, input_path: str, message: str = None, error_code: int = 105):
        """
        初始化无效输入异常
        
        Args:
            input_path: 无效的输入路径
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            message = f"无效的输入路径: {input_path}"
        self.input_path = input_path
        super().__init__(message, error_code)

class OutputDirectoryError(DecompilerError):
    """
    输出目录相关错误
    """
    
    def __init__(self, output_dir: str, message: str = None, error_code: int = 106):
        """
        初始化输出目录错误异常
        
        Args:
            output_dir: 输出目录路径
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            message = f"无法创建或访问输出目录: {output_dir}"
        self.output_dir = output_dir
        super().__init__(message, error_code)

class ConfigurationError(DecompilerError):
    """
    配置相关错误
    """
    
    def __init__(self, config_key: str = None, message: str = None, error_code: int = 107):
        """
        初始化配置错误异常
        
        Args:
            config_key: 配置键
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            if config_key:
                message = f"配置项 '{config_key}' 无效或缺失"
            else:
                message = "配置无效或缺失"
        self.config_key = config_key
        super().__init__(message, error_code)

class UnsupportedFileError(DecompilerError):
    """
    不支持的文件类型错误
    """
    
    def __init__(self, file_path: str, message: str = None, error_code: int = 108):
        """
        初始化不支持的文件类型异常
        
        Args:
            file_path: 不支持的文件路径
            message: 异常消息
            error_code: 错误代码
        """
        if message is None:
            message = f"不支持的文件类型: {file_path}"
        self.file_path = file_path
        super().__init__(message, error_code)

class MultiThreadingError(DecompilerError):
    """
    多线程处理相关错误
    """
    
    def __init__(self, message: str = "多线程处理过程中发生错误", error_code: int = 109):
        super().__init__(message, error_code)