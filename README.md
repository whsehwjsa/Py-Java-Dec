# Java反编译工具包

## 项目概述

Java反编译工具包是一个功能强大的多引擎Java反编译解决方案，支持CFR、FernFlower和JADX三种主流反编译引擎。该工具包提供了丰富的命令行接口和Python模块API，能够高效地反编译Java类文件、JAR包，并提供代码格式化、依赖分析、代码搜索等增强功能。

![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)

## 系统要求

- Python 3.7+
- Java 8+（用于运行反编译引擎）
- 各反编译引擎JAR文件（CFR、FernFlower、JADX）
- 可选依赖：
  - tqdm（用于显示进度条）
  - networkx, matplotlib（用于依赖分析和可视化）

## 主要功能

### 反编译核心功能
- 支持多种反编译引擎：CFR（默认）、FernFlower、JADX
- 支持批量反编译多个文件或整个目录
- 多线程处理，显著提高效率
- 详细的进度显示和统计信息
- 支持反混淆功能
- 可自定义各种反编译参数

### 增强功能
- **代码格式化**：对反编译后的Java代码进行格式化和美化
- **依赖分析**：分析Java代码中的类依赖关系，生成依赖图
- **代码搜索**：在Java代码中进行关键词搜索和模式匹配
- **JAR文件Class提取**：从JAR文件中精确或模糊匹配并提取指定的Class文件

### 工具特性
- 自动检测和验证必要的依赖
- 友好的命令行界面
- 模块化设计，易于扩展和维护
- 全面的错误处理和异常管理
- 支持调试模式和性能分析

## 支持的反编译引擎

| 引擎 | 特点 | 适用场景 |
|------|------|----------|
| CFR | 轻量级，速度快，对新版Java特性支持良好 | 快速反编译、日常使用、现代Java代码 |
| FernFlower | 生成代码质量高，结构清晰 | 对代码可读性要求高的场景、代码分析 |
| JADX | 支持APK反编译，反混淆能力强 | 复杂项目、Android应用分析、混淆代码 |

## 安装与设置

### 基础安装

1. **Python环境**：确保已安装Python 3.7或更高版本

2. **Java运行时环境**：
   - 下载地址：https://www.oracle.com/java/technologies/downloads/
   - 确保Java已添加到系统PATH

3. **可选Python依赖**：
   ```bash
   pip install tqdm networkx matplotlib
   ```

4. **反编译引擎**：
   - CFR（推荐）：工具会自动搜索或使用指定路径
     - 下载地址：https://www.benf.org/other/cfr/
   - FernFlower：可选引擎，需单独下载
     - 下载地址：https://github.com/fesh0r/fernflower/releases
   - JADX：可选引擎，需单独下载
     - 下载地址：https://github.com/skylot/jadx/releases

## 快速开始

### 命令行使用

```bash
# 使用默认引擎(CFR)反编译单个文件
python main.py -i input.class -o output_dir

# 使用默认引擎(CFR)反编译JAR文件
python main.py -i input.jar -o output_dir

# 指定引擎反编译JAR文件
python main.py -i input.jar -o output_dir --engine fernflower

# 递归反编译整个目录
python main.py -i input_dir -o output_dir --recursive
```

### 从JAR文件中提取并反编译特定Class

```bash
python extract_and_decompile.py --jar example.jar --class-name Main --show-code
```

### 作为Python模块使用

```python
from archive.src.cfr import CFRDecompiler

# 创建CFR反编译引擎实例
cfr = CFRDecompiler(verbose=True, deobfuscate=True, max_workers=8)

# 反编译单个JAR文件
stats = cfr.decompile_single_jar("example.jar", "output_dir")
```

## 目录结构

```
java_decompiler/
├── README.md                # 项目说明文档
├── main.py                  # 主入口脚本
├── extract_and_decompile.py # JAR文件Class提取与反编译脚本
├── archive/                 # 核心源码目录
│   ├── src/                 # 源代码
│   │   ├── cfr.py           # CFR反编译引擎实现
│   │   ├── fernflower.py    # FernFlower反编译引擎实现
│   │   ├── jadx.py          # JADX反编译引擎实现
│   │   ├── code_formatter.py # 代码格式化模块
│   │   ├── dependency_analyzer.py # 依赖分析模块
│   │   ├── code_searcher.py # 代码搜索模块
│   │   └── tools.py         # 综合工具模块
├── 说明文档/                # 详细文档
└── 测试jar.jar              # 测试用JAR文件
```

## 常见问题与解决方案

### 1. 未找到Java环境
- **错误**：`未找到Java运行时环境，请先安装JRE或JDK`
- **解决**：安装Java运行时环境并确保已添加到系统PATH

### 2. 未找到指定的反编译引擎
- **错误**：`未找到CFR反编译工具`或类似信息
- **解决**：下载相应的反编译引擎JAR文件，并使用`--cfr-path`、`--fernflower-path`或`--jadx-path`参数指定路径

### 3. 反编译超时
- **错误**：`subprocess.TimeoutExpired`
- **解决**：使用`--timeout`参数增加超时时间

### 4. 多线程处理问题
- **解决**：如果在多线程处理时遇到问题，可以尝试使用`--no-multithreading`参数禁用多线程

### 5. 内存不足
- **解决**：对于大型JAR文件，可以尝试增加JVM内存分配或使用`--memory-limit`参数（仅Unix系统有效）

## 反编译引擎比较

### CFR
- **优点**：反编译结果质量高，尤其是对新版Java特性的支持；轻量级，启动速度快
- **缺点**：某些特殊情况下可能速度较慢；配置选项较多

### FernFlower
- **优点**：IntelliJ IDEA使用的反编译引擎，结构清晰，生成代码接近原始代码
- **缺点**：配置选项相对较少；某些复杂代码可能处理不够理想

### JADX
- **优点**：特别适合Android应用分析，对混淆代码有较好支持；提供更多的反混淆选项
- **缺点**：资源占用较大；启动较慢

## 开发与扩展

工具采用面向对象设计，通过基类`JavaDecompiler`定义接口，各具体引擎实现相应方法。如需添加新的反编译引擎，只需继承`JavaDecompiler`并实现相关方法。

项目支持通过扩展模块添加新功能，如代码分析、安全检查等。请参考`code_formatter.py`、`dependency_analyzer.py`和`code_searcher.py`的实现方式。

## 文档

详细使用说明请参考以下文档：

- [JAR_CLASS提取反编译功能说明](说明文档/JAR_CLASS提取反编译功能说明.md)：关于从JAR文件提取并反编译特定Class文件的详细说明
- [命令使用说明](说明文档/命令使用说明.md)：命令行参数和使用示例
- [模块使用说明](说明文档/模块使用说明.md)：Python模块API使用方法
- [测试脚本说明](说明文档/测试脚本说明.md)：测试功能和使用方法