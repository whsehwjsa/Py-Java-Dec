"""反编译工具 - 主入口"""

import sys
import os
import argparse
import time
import signal
from pathlib import Path

# 添加archive/src目录到系统路径
sys.path.append(str(Path(__file__).parent / 'archive' / 'src'))

# 导入调试工具模块
from debug_tools import DebugTools

# 导入反编译引擎相关模块
try:
    from cfr import CFRDecompiler
    from fernflower import FernFlowerDecompiler
    from jadx import JADXDecompiler
except ImportError as e:
    print(f"导入反编译引擎失败: {e}")
    sys.exit(1)


def create_decompiler(args):
    """根据参数创建适当的反编译引擎实例"""
    engine_map = {
        'cfr': CFRDecompiler,
        'fernflower': FernFlowerDecompiler,
        'jadx': JADXDecompiler
    }
    
    decompiler_class = engine_map.get(args.engine)
    if not decompiler_class:
        print(f"不支持的引擎: {args.engine}")
        sys.exit(1)
    
    try:
        return decompiler_class(
            verbose=args.verbose,
            deobfuscate=args.deobfuscate,
            max_workers=args.threads
        )
    except Exception as e:
        print(f"创建反编译引擎失败: {e}")
        sys.exit(1)


def generate_custom_output_dir(base_output_dir, target_name):
    """
    生成自定义输出目录路径，处理同名文件夹情况
    
    Args:
        base_output_dir: 基础输出目录
        target_name: 目标文件夹名称
        
    Returns:
        str: 最终的输出目录路径
    """
    output_path = os.path.join(base_output_dir, target_name)
    
    # 检查是否已存在同名文件夹
    if not os.path.exists(output_path):
        return output_path
    
    # 提示用户是否替换
    response = input(f"已有同名文件夹，名称为'{target_name}'，是否替换？(y/n): ")
    
    if response.lower() == 'y':
        # 删除已存在的文件夹
        import shutil
        shutil.rmtree(output_path)
        return output_path
    else:
        # 尝试重命名为带序号的版本
        counter = 2
        while True:
            new_name = f"{target_name}({counter})"
            new_path = os.path.join(base_output_dir, new_name)
            
            if not os.path.exists(new_path):
                # 提示用户确认重命名
                rename_response = input(f"是否将新文件夹重命名为'{new_name}'？(y/n): ")
                if rename_response.lower() == 'y':
                    return new_path
                else:
                    # 如果用户拒绝，尝试下一个序号
                    counter += 1
                    continue
            else:
                # 如果带序号的版本也存在，继续尝试更高的序号
                counter += 1


def ensure_output_directory(output_dir, force=False):
    """确保输出目录存在，如果已存在则根据force参数决定是否继续"""
    if os.path.exists(output_dir):
        if not force:
            # 获取基础目录和目标名称
            base_dir = os.path.dirname(output_dir)
            target_name = os.path.basename(output_dir)
            
            # 使用自定义函数处理目录冲突
            resolved_path = generate_custom_output_dir(base_dir, target_name)
            
            # 如果路径不同，表示用户选择了重命名而不是替换
            if resolved_path != output_dir:
                print(f"将使用新路径: {resolved_path}")
                return resolved_path
        else:
            # 强制模式下直接删除已存在的目录
            import shutil
            shutil.rmtree(output_dir)
    
    # 创建目录
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def process_input_path(input_path, output_dir, decompiler, recursive=False):
    """处理输入路径，根据文件类型调用相应的反编译方法"""
    if os.path.isfile(input_path):
        # 处理单个文件
        if input_path.lower().endswith('.jar'):
            decompiler.decompile_single_jar(input_path, output_dir)
        elif input_path.lower().endswith('.class'):
            decompiler.decompile_single_class(input_path, output_dir)
        else:
            print(f"不支持的文件类型: {input_path}")
            return False
    elif os.path.isdir(input_path):
        # 处理目录
        if recursive:
            # 递归处理所有子目录
            for root, _, files in os.walk(input_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if file_path.lower().endswith('.jar'):
                        decompiler.decompile_single_jar(file_path, output_dir)
                    elif file_path.lower().endswith('.class'):
                        decompiler.decompile_single_class(file_path, output_dir)
        else:
            # 只处理当前目录
            for file in os.listdir(input_path):
                file_path = os.path.join(input_path, file)
                if os.path.isfile(file_path):
                    if file_path.lower().endswith('.jar'):
                        decompiler.decompile_single_jar(file_path, output_dir)
                    elif file_path.lower().endswith('.class'):
                        decompiler.decompile_single_class(file_path, output_dir)
    else:
        print(f"输入路径不存在: {input_path}")
        return False
    
    return True


def main():
    """主程序入口点"""
    # 创建参数解析器，支持更灵活的参数格式
    parser = argparse.ArgumentParser(
        prog='python main.py',
        description='Java反编译工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python main.py -i input.jar -o output_dir
  python main.py -i input.class -o output_dir --engine cfr
  python main.py -o output_dir -i input_dir --recursive --threads 10
  python main.py -v -i input.jar -o output_dir --deobfuscate

调试参数（开发者使用）:
  python main.py --version-info
  python main.py --dump-config -i input.jar -o output_dir
  python main.py --debug --dry-run -i input.jar -o output_dir
  python main.py --profile --timeout 300 -i large.jar -o output_dir
  python main.py --log-level DEBUG --log-file decompile.log -i input.jar -o output_dir
        """)
    
    # 主要参数
    parser.add_argument('-i', '--input', help='输入路径（类文件、JAR文件或目录）')
    parser.add_argument('-o', '--output', help='输出目录路径')
    parser.add_argument('--engine', default='cfr', choices=['cfr', 'fernflower', 'jadx'], 
                       help='选择反编译引擎（默认: cfr）')
    
    # 高级选项
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细输出')
    parser.add_argument('-r', '--recursive', action='store_true', help='递归处理子目录')
    parser.add_argument('-f', '--force', action='store_true', help='强制覆盖已存在的输出目录')
    parser.add_argument('-d', '--deobfuscate', action='store_true', help='启用反混淆功能')
    parser.add_argument('-t', '--threads', type=int, default=4, help='使用的线程数量')
    
    # 添加调试参数
    DebugTools.add_debug_arguments(parser)
    
    # 修复常见的参数格式问题
    args = parser.parse_args()
    
    # 确保路径格式正确（处理可能的空格问题）
    if hasattr(args, 'input') and args.input:
        # 如果输入路径包含空格且被引号包围，确保正确处理
        input_path = args.input
        # 去除可能的引号包围
        if (input_path.startswith('"') and input_path.endswith('"')) or \
           (input_path.startswith("'") and input_path.endswith("'")):
            args.input = input_path[1:-1]
    
    # 调试参数处理
    if args.version_info:
        DebugTools.show_version_info()
        return 0
    
    if args.dump_config:
        DebugTools.dump_config(args)
        return 0
    
    # 检查必需参数（除了调试参数）
    if not args.version_info and not args.dump_config:
        if not args.input:
            parser.error("必需参数: -i/--input")
        if not args.output:
            parser.error("必需参数: -o/--output")
    
    # 设置调试模式
    if args.debug:
        args.verbose = True
        DebugTools.setup_debug_logging(debug=True, log_level=args.log_level, log_file=args.log_file)
    
    # 参数解析已移到前面
    
    # 显示信息
    print(f"Java 反编译工具 v1.0.0")
    print(f"输入: {args.input}")
    print(f"输出: {args.output}")
    print(f"引擎: {args.engine}")
    print(f"线程数: {args.threads}")
    print(f"反混淆: {'是' if args.deobfuscate else '否'}")
    print(f"递归处理: {'是' if args.recursive else '否'}")
    if args.debug:
        print(f"调试模式: 已启用")
    if args.dry_run:
        print(f"模拟运行: 已启用")
    if args.timeout > 0:
        print(f"超时时间: {args.timeout}秒")
    if args.memory_limit > 0:
        print(f"内存限制: {args.memory_limit}MB")
    print("=" * 60)
    
    # 确保输入路径存在
    if not os.path.exists(args.input):
        print(f"错误: 输入路径不存在 - {args.input}")
        return 1
    
    # 确保输出目录，并更新args.output为可能修改后的路径
    args.output = ensure_output_directory(args.output, args.force)
    
    # 创建反编译引擎
    decompiler = create_decompiler(args)
    
    # 模拟运行检查
    if args.dry_run:
        DebugTools.simulate_decompilation(args.input, args.output)
        return 0
    
    try:
        # 性能分析
        if args.profile:
            profiler_data = DebugTools.profile_decompilation(
                process_input_path, 
                args.input, 
                args.output, 
                decompiler, 
                args.recursive
            )
            success = profiler_data['result']
            elapsed = profiler_data['time_elapsed']
            DebugTools.save_profile_stats(profiler_data['profiler'], args.profile_output)
        else:
            # 超时控制
            if args.timeout > 0:
                def timeout_handler(signum, frame):
                    raise TimeoutError(f"操作超时（{args.timeout}秒）")
                
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(args.timeout)
            
            start_time = time.time()
            
            # 执行反编译
            success = process_input_path(args.input, args.output, decompiler, args.recursive)
            
            end_time = time.time()
            elapsed = end_time - start_time
        
        # 内存限制（仅限Unix系统）
        if args.memory_limit > 0 and hasattr(os, 'setrlimit'):
            import resource
            memory_limit = args.memory_limit * 1024 * 1024  # 转换为字节
            resource.setrlimit(resource.RLIMIT_AS, (memory_limit, memory_limit))
        
            # 取消超时
            if args.timeout > 0:
                signal.alarm(0)
        
        if success:
            print("=" * 60)
            print(f"反编译操作完成!")
            print(f"总耗时: {elapsed:.2f} 秒")
            print(f"输出目录: {args.output}")
            return 0
        else:
            print("反编译操作失败")
            return 1
            
    except KeyboardInterrupt:
        print("\n用户中断操作")
        return 130
    except TimeoutError as e:
        print(f"\n错误: {e}")
        return 124
    except MemoryError:
        print("\n错误: 内存不足，请增加内存限制或减少处理规模")
        return 137
    except Exception as e:
        print(f"反编译过程中发生错误: {e}")
        if args.verbose or args.debug:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())