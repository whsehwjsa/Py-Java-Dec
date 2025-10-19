# Java反编译工具包
# 导入核心模块
import sys
from pathlib import Path

# 添加src目录到系统路径
sys.path.append(str(Path(__file__).parent / 'src'))

# 从src目录导入主要功能
from src.base import DecompilerBase
from src.java_decompiler.core.processor import decompile_file, decompile_jar

__version__ = '1.0.0'
__all__ = ['DecompilerBase', 'decompile_file', 'decompile_jar']