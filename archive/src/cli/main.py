#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
命令行入口模块
提供命令行访问的主函数
"""

import sys
from ..__main__ import main

if __name__ == "__main__":
    sys.exit(main())