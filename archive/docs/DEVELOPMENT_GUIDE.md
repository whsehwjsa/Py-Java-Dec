# Java 反编译工具包 - 开发指南

本文档旨在帮助开发者理解项目结构、开发规范和扩展方法，以便更好地维护和扩展 Java 反编译工具包。

## 目录结构

项目采用模块化架构，各模块职责明确，便于维护和扩展：

```
.
├── java_decompiler/          # 主包目录
│   ├── __init__.py           # 包初始化
│   ├── __main__.py           # 主程序入口
│   ├── base.py               # 基础反编译器接口
│   ├── cfr.py                # CFR 反编译器实现
│   ├── exceptions.py         # 自定义异常类
│   ├── cli/                  # 命令行接口模块
│   ├── config/               # 配置管理模块
│   ├── file_utils/           # 文件处理工具模块
│   ├── logger/               # 日志系统模块
│   ├── performance/          # 性能监控模块
│   └── task_manager/         # 任务管理模块
├── cfr.jar                   # CFR 反编译工具
├── setup.py                  # 安装配置
├── README.md                 # 用户文档
└── DEVELOPMENT_GUIDE.md      # 开发指南（当前文档）
```

## 开发规范

### 代码风格

- 遵循 PEP 8 编码规范
- 使用类型提示增强代码可读性和IDE支持
- 为所有公共函数、类和模块添加文档字符串
- 使用 `snake_case` 命名函数和变量，`CamelCase` 命名类

### 错误处理

- 使用项目中定义的自定义异常类，避免使用通用异常
- 提供有意义的错误消息，包含上下文信息
- 在适当的地方捕获异常并进行处理，避免程序崩溃

### 日志记录

- 使用项目提供的日志系统，而不是 `print` 语句
- 根据信息重要性选择适当的日志级别
- 在日志中包含足够的上下文信息

## 扩展指南

### 添加新的反编译器引擎

要添加新的反编译器引擎（如 Fernflower、JD-GUI 等），请遵循以下步骤：

1. **创建新的引擎实现类**：

```python
from java_decompiler.base import JavaDecompiler

class NewDecompilerEngine(JavaDecompiler):
    """新反编译器引擎的实现"""
    
    def __init__(self, config=None):
        super().__init__(config)
        self.engine_name = "new_engine"
    
    def check_availability(self):
        # 检查引擎是否可用
        pass
    
    def decompile_file(self, input_path, output_path):
        # 实现反编译逻辑
        pass
```

2. **更新配置**：
在 `config/config_manager.py` 中的 `DEFAULT_CONFIG` 字典中添加新引擎的配置项：

```python
"engines": {
    "cfr": {
        "path": os.path.join(PACKAGE_DIR, "cfr.jar"),
        "enabled": True,
        "priority": 1
    },
    "new_engine": {
        "path": "/path/to/new_engine.jar",
        "enabled": True,
        "priority": 2,
        "options": {
            # 特定选项
        }
    }
}
```

3. **更新 `get_decompiler` 函数**：
在 `__init__.py` 中更新函数，使其能够返回新的引擎实例。

### 添加新的命令行参数

要添加新的命令行参数，请修改 `cli/argument_parser.py` 文件：

```python
def parse_arguments():
    parser = ArgumentParser()
    
    # 现有参数...
    
    # 添加新参数
    parser.add_argument(
        "--new-option",
        help="新选项的描述",
        default=None
    )
    
    return parser.parse_args()
```

### 添加新的工具函数

如果有通用工具函数需要添加，可以在相应的工具模块中添加，如 `file_utils`、`performance` 等。

## 测试指南

### 单元测试

为新功能编写单元测试，确保代码质量和功能正确性。单元测试应放在 `tests/` 目录下（如果不存在，可创建）。

### 集成测试

使用项目根目录下的 `test_integration.py` 脚本进行集成测试，确保各模块协同工作正常。

```bash
python test_integration.py
```

## 发布流程

1. **更新版本号**：在 `setup.py` 中更新版本号
2. **更新变更日志**：在 `README.md` 中更新变更信息
3. **构建发布包**：

```bash
python setup.py sdist bdist_wheel
```

4. **安装并测试**：

```bash
pip install -e .
```

## 常见问题

### 依赖管理

项目使用 `setup.py` 管理依赖。添加新依赖时，请更新 `install_requires` 和 `extras_require` 部分。

### 性能优化

- 使用 `performance` 模块监控代码性能
- 对于大型文件处理，考虑使用 `task_manager` 中的并行处理功能
- 避免不必要的文件 IO 操作