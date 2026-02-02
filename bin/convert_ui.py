import os
import sys
from pathlib import Path
import subprocess

# Add nextlib parent directory to path
_current_file = Path(__file__).resolve()
_nextlib_root = _current_file.parent.parent.parent  # Go up to /home/test/lib
if str(_nextlib_root) not in sys.path:
    sys.path.insert(0, str(_nextlib_root))

import PySide6
from nextlib.utils.file import get_encoding_type


def modify_ui_py_file(file_path, disable_centralwidget_set):
    encoding_type = get_encoding_type(file_path)  # 다시 확인
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    new_lines = []
    for line in lines:
        if 'MainWindow.setCentralWidget(self.centralwidget)' in line:
            if disable_centralwidget_set:
                if not line.strip().startswith('#'):
                    new_lines.append('# ' + line)
                else:
                    new_lines.append(line)
            else:
                new_lines.append(line)
        else:
            new_lines.append(line)

    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)


if __name__ == '__main__':
    start_path = '.'
    force_update = False
    disable_centralwidget_set = False
    
    # 첫번째 인자는 터미널의 실행 위치(CUR_DIR)
    # 두번째 인자부터 실제 변환 대상
    args = sys.argv[1:]
    
    if '-f' in args:
        force_update = True
        args.remove('-f')
    if '-d' in args:
        disable_centralwidget_set = True
        args.remove('-d')
    
    terminal_dir = Path(args[0])
    target_args = args[1:]
    
    if len(target_args) == 0:
        target_path = terminal_dir / 'view'
        if not target_path.is_dir():
            print(f"Error: {target_path} 폴더가 없습니다.")
            sys.exit(1)

        ui_files = list(Path(target_path).glob('**/*.ui'))

    else:
        target_arg = target_args[0]
        target_path = terminal_dir / target_arg
        
        if target_path.suffix == '.ui' and target_path.is_file():
            ui_files = [target_path]
        
        elif target_path.is_dir():
            ui_files = list(target_path.glob("**/*.ui"))
        
        else:
            print(f"[!] 파일 또는 경로를 찾을 수 없습니다. : {target_arg}")
            sys.exit(1)

    print(f"## Qt Designer UI Converter ##")
    print(f"- Path: {target_path}\n")

    totalNum = len(ui_files)
    for i, source in enumerate(ui_files):
        target = source.parent / (source.stem + '_ui.py')
        if not force_update and target.is_file() and target.stat().st_mtime >= source.stat().st_mtime:
            print(f' [{i + 1}/{totalNum}] Skipping... {source.name:<16} -> Already Up-to-date')
        else:
            print(f' [{i + 1}/{totalNum}] Converting... {source.name:<16} -> {source.stem}_ui.py')

            # Cross-platform uic command
            if os.name == 'nt':  # Windows
                uic = Path(PySide6.__file__).parent / "uic.exe"
                subprocess.run([str(uic), str(source), "-o", str(target)], check=True)
            else:  # Linux/Mac - use pyside6-uic or python module
                try:
                    # Try pyside6-uic command first
                    subprocess.run(["pyside6-uic", str(source), "-o", str(target)], check=True)
                except FileNotFoundError:
                    # Fallback to python module
                    subprocess.run([sys.executable, "-m", "PySide6.uic", str(source), "-o", str(target)], check=True)

            if disable_centralwidget_set:
                modify_ui_py_file(str(target), disable_centralwidget_set)

    if totalNum == 0:
        print(f' [0/0] ui file not found')

    print(' Done')
    