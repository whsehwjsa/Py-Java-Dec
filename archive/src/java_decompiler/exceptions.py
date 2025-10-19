#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
自定义异常类定义
"""


class JavaDecompilerError(Exception):
    """
    Java反编译工具的基础异常类
    """
    pass


class EngineNotFoundError(JavaDecompilerError):
    """
    指定的反编译引擎未找到
    """
    def __init__(self, engine_name: str):
        self.engine_name = engine_name
        super().__init__(f"反编译引擎 '{engine_name}' 未找到或未安装")


class EngineNotAvailableError(JavaDecompilerError):
    """
    反编译引擎不可用
    """
    def __init__(self, engine_name: str, reason: str = ""):
        self.engine_name = engine_name
        self.reason = reason
        message = f"反编译引擎 '{engine_name}' 不可用"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class DecompilationError(JavaDecompilerError):
    """
    反编译过程失败
    """
    def __init__(self, input_file: str, engine: str = None, error_message: str = ""):
        self.input_file = input_file
        self.engine = engine
        self.error_message = error_message
        message = f"反编译文件 '{input_file}' 失败"
        if engine:
            message += f" 使用引擎 '{engine}'"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class InvalidInputError(JavaDecompilerError):
    """
    无效的输入文件或目录
    """
    def __init__(self, input_path: str, reason: str = ""):
        self.input_path = input_path
        self.reason = reason
        message = f"无效的输入 '{input_path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class FileTypeError(JavaDecompilerError):
    """
    文件类型不支持
    """
    def __init__(self, file_path: str, expected_type: str = None):
        self.file_path = file_path
        self.expected_type = expected_type
        message = f"文件 '{file_path}' 类型不支持"
        if expected_type:
            message += f"，期望类型: {expected_type}"
        super().__init__(message)


class ConfigError(JavaDecompilerError):
    """
    配置相关错误
    """
    def __init__(self, config_path: str = None, error_message: str = ""):
        self.config_path = config_path
        self.error_message = error_message
        message = "配置错误"
        if config_path:
            message += f" 在文件 '{config_path}'"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class ConfigurationError(JavaDecompilerError):
    """
    配置参数错误
    当反编译引擎的配置参数无效或不完整时抛出
    """
    def __init__(self, option_name: str = None, error_message: str = ""):
        self.option_name = option_name
        self.error_message = error_message
        message = "配置参数错误"
        if option_name:
            message += f" 在选项 '{option_name}'"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class PathError(JavaDecompilerError):
    """
    路径相关错误
    """
    pass


class FileOperationError(JavaDecompilerError):
    """
    文件操作错误
    """
    def __init__(self, operation: str, file_path: str, error_message: str = ""):
        self.operation = operation
        self.file_path = file_path
        self.error_message = error_message
        message = f"{operation} 文件 '{file_path}' 失败"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class JavaRuntimeError(JavaDecompilerError):
    """
    Java运行时相关错误
    """
    def __init__(self, error_message: str = "Java运行时环境不可用或配置错误"):
        self.error_message = error_message
        super().__init__(error_message)


class OutputDirectoryError(JavaDecompilerError):
    """
    输出目录相关错误
    """
    def __init__(self, output_dir: str, error_message: str = ""):
        self.output_dir = output_dir
        self.error_message = error_message
        message = f"输出目录 '{output_dir}' 错误"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class OptionError(JavaDecompilerError):
    """
    选项相关错误
    """
    def __init__(self, option_name: str, error_message: str = ""):
        self.option_name = option_name
        self.error_message = error_message
        message = f"选项 '{option_name}' 错误"
        if error_message:
            message += f": {error_message}"
        super().__init__(message)


class TimeoutError(JavaDecompilerError):
    """
    反编译超时错误
    """
    def __init__(self, input_file: str, timeout: int):
        self.input_file = input_file
        self.timeout = timeout
        super().__init__(f"反编译文件 '{input_file}' 超时，超过 {timeout} 秒")


class MemoryLimitExceededError(JavaDecompilerError):
    """
    内存限制超出错误
    """
    def __init__(self, input_file: str, memory_limit: str):
        self.input_file = input_file
        self.memory_limit = memory_limit
        super().__init__(f"反编译文件 '{input_file}' 超出内存限制 {memory_limit}")


class BatchDecompilationError(JavaDecompilerError):
    """
    批量反编译过程中的错误
    """
    def __init__(self, total_files: int, success_count: int, failed_files: list):
        self.total_files = total_files
        self.success_count = success_count
        self.failed_files = failed_files
        self.failed_count = len(failed_files)
        super().__init__(
            f"批量反编译完成，总计 {total_files} 个文件，"  
            f"成功 {success_count} 个，失败 {self.failed_count} 个"
        )