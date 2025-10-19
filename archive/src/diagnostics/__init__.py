"""诊断工具模块

提供系统检查、配置验证和故障排除功能，帮助用户解决可能遇到的问题。

导出：
    - DiagnosticTool: 诊断工具类
    - check_environment: 检查系统环境
    - validate_config: 验证配置文件
    - troubleshoot_issues: 故障排除助手
"""

from java_decompiler.diagnostics.diagnostic_tool import DiagnosticTool
from java_decompiler.diagnostics.diagnostic_tool import check_environment
from java_decompiler.diagnostics.diagnostic_tool import validate_config
from java_decompiler.diagnostics.diagnostic_tool import troubleshoot_issues

__all__ = [
    "DiagnosticTool",
    "check_environment",
    "validate_config",
    "troubleshoot_issues"
]