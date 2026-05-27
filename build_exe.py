import os
import subprocess
import sys

def build():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    main_py = os.path.join(script_dir, "main.py")
    dist_dir = os.path.join(script_dir, "dist")

    # 确保安装了 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",
        "--name", "FocusPlanner",
        "--add-data", f"data{os.pathsep}data",
        "--clean",
        main_py
    ]

    print("正在打包 Focus Planner...")
    subprocess.check_call(cmd, cwd=script_dir)
    print(f"\n打包完成！exe 文件在 {dist_dir} 目录下")

if __name__ == "__main__":
    build()