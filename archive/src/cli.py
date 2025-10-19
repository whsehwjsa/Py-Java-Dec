"""命令行接口模块"""

import argparse
import os
import sys
import shutil
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from utils import validate_paths, parse_tool_options, get_decompiler


def main():
    """程序主入口"""
    parser = argparse.ArgumentParser(description='反编译工具')
    parser.add_argument('-i', '--input', required=True, 
                      help='输入路径（单个class、单个jar或包含它们的目录）')
    parser.add_argument('-o', '--output', required=True, 
                      help='输出目录（反编译结果导出路径）')
    parser.add_argument('-v', '--verbose', action='store_true', 
                      help='显示详细反编译过程')
    parser.add_argument('--deobfuscate', action='store_true', 
                      help='启用反混淆')
    parser.add_argument('--overwrite', action='store_true', 
                      help='覆盖已存在的输出目录')
    parser.add_argument('--threads', type=int, default=4,
                      help='工作线程数（默认为4）')
    parser.add_argument('--timeout', type=int, default=300,
                      help='单个文件反编译超时时间（秒，默认为300）')
    parser.add_argument('--no-multithreading', action='store_true',
                      help='禁用多线程处理')
    
    # 反编译工具选择
    parser.add_argument('--fernflower', action='store_true',
                      help='使用FernFlower反编译引擎')
    parser.add_argument('--jadx', '-j', action='store_true',
                      help='使用JADX反编译引擎（默认使用CFR）')
    
    # CFR相关参数
    parser.add_argument('--cfr-path', 
                      help='CFR JAR文件的路径')
    parser.add_argument('--cfr-options',
                      help='额外的CFR选项（格式：key1=value1,key2=value2）')
    
    # FernFlower相关参数
    parser.add_argument('--fernflower-path',
                      help='FernFlower JAR文件的路径')
    parser.add_argument('--fernflower-options',
                      help='额外的FernFlower选项（格式：key1=value1,key2=value2）')
    
    # JADX相关参数
    parser.add_argument('--jadx-path',
                      help='JADX可执行文件或JAR文件的路径')
    parser.add_argument('--jadx-options',
                      help='额外的JADX选项（格式：key1=value1,key2=value2）')
    
    # 通用选项参数
    parser.add_argument('--tool-options',
                      help='所选反编译工具的额外选项（格式：key1=value1,key2=value2）')
    
    args = parser.parse_args()

    try:
        # 处理输出目录
        if os.path.exists(args.output) and args.overwrite:
            print(f"正在删除现有输出目录：{args.output}...")
            shutil.rmtree(args.output)
            print(f"已删除现有输出目录：{args.output}")
        
        input_path = os.path.abspath(args.input)
        output_dir = os.path.abspath(args.output)
        validate_paths(input_path, output_dir)
        
        # 获取反编译工具实例
        decompiler = get_decompiler(args)
        
        # 确定使用的反编译引擎名称
        engine_name = "CFR"
        if args.fernflower:
            engine_name = "FernFlower"
        elif args.jadx:
            engine_name = "JADX"
        
        print(f"\n开始反编译...")
        print(f"输入路径: {input_path}")
        print(f"输出目录: {output_dir}")
        print(f"反编译引擎: {engine_name}")
        print(f"线程数: {'1 (禁用)' if args.no_multithreading else args.threads}")
        print(f"反混淆: {'启用' if args.deobfuscate else '禁用'}")
        
        # 显示额外选项
        options = None
        if engine_name == "CFR":
            options = parse_tool_options(args.tool_options or args.cfr_options, "CFR")
        elif engine_name == "FernFlower":
            options = parse_tool_options(args.tool_options or args.fernflower_options, "FernFlower")
        elif engine_name == "JADX":
            options = parse_tool_options(args.tool_options or args.jadx_options, "JADX")
            
        if options:
            print(f"额外{engine_name}选项: {options}")
            
        print("=" * 60)
        
        # 执行反编译
        stats = decompiler.decompile_path(
            input_path, 
            output_dir, 
            use_multithreading=not args.no_multithreading
        )
        
        # 输出统计信息
        print("\n" + "=" * 60)
        print(f"反编译完成！")
        print(f"总计: {stats['total']} 个文件")
        print(f"成功: {stats['success']} 个文件")
        print(f"失败: {stats['failed']} 个文件")
        print(f"耗时: {stats['time']:.2f} 秒")
        print(f"结果已导出到: {output_dir}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n[中断] 用户中断了反编译操作")
        sys.exit(130)  # SIGINT 退出码
    except Exception as e:
        print(f"[错误] {str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()