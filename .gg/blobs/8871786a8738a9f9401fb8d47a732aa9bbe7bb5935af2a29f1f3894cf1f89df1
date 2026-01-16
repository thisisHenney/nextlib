import os
import platform
import subprocess
from pathlib import Path
from nextlib.utils.file import check_path, is_file, is_dir
from nextlib.widgets.messagebox import messagebox_error


def open_file_explorer(parent: None = None, path: str | None = None):
    system = platform.system()
    path = check_path(path)

    if system == 'Windows':
        subprocess.Popen(['explorer', (Path(path).resolve())])
    elif system == 'Linux':
        try:
            subprocess.Popen(['xdg-open', path])
        except FileNotFoundError:
            subprocess.Popen(['nautilus', path])
    else:
        messagebox_error(parent, text='Cannot open this system')

# def open_terminal(parent: None = None, path: str | None = None):
#     system = platform.system()
#     path = check_path(path)
#
#     if system == 'Windows':
#         # subprocess.Popen(f'start cmd /K cd /d "{path}"', shell=True)
#         subprocess.Popen(f'cmd /K start cmd /d {path}')
#     elif platform.system() == 'Linux':
#         subprocess.Popen(['gnome-terminal', f'--working-directory={path}'])
#         # os.system(f'gnome-terminal --working-directory={path} &')
#     else:
#         messagebox_error(None, title='Cannot open this system')
#
#     # elif system == 'Linux':
#     #     try:
#     #         subprocess.Popen(['gnome-terminal', f'--working-directory={path}'])
#     #     except FileNotFoundError:
#     #         subprocess.Popen(['x-terminal-emulator', f'--working-directory={path}'])
#     # else:
#     #     messagebox_error(parent, title='Cannot open this system')
#
def open_text_editor(parent=None, path: str | None = None):
    system = platform.system()
    path = check_path(path)
    if not path:
        messagebox_error(parent, 'Cannot open file')
        return

    if system == 'Windows':
        subprocess.Popen(['notepad.exe', str(Path(path).resolve())])
    elif system == 'Linux':
        try:
            subprocess.Popen(['gedit', path])
        except FileNotFoundError:
            subprocess.Popen(['xdg-open', path])
    else:
        messagebox_error(parent, 'Cannot open this system')
    return True
#
# def run_pdf_viewer(parent: None = None, path: str | None = None):
#     system = platform.system()
#     path = check_path(path)
#
#     if system == 'Windows':
#         os.startfile(os.path.normpath(path))
#     elif system == 'Linux':
#         subprocess.Popen(['xdg-open', path])
#     else:
#         messagebox_error(parent, title='Cannot open this system')
#
#

def open_web_browser(parent: None = None, url: str | None = None):
    system = platform.system()
    url = url or "https://www.google.com"

    if system == 'Windows':
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception:
            subprocess.Popen([r'C:\Program Files\Google\Chrome\Application\chrome.exe', url])
    elif system == 'Linux':
        try:
            subprocess.Popen(['xdg-open', url])
        except FileNotFoundError:
            subprocess.Popen(['google-chrome-stable', url])
    else:
        messagebox_error(parent, title='Cannot open this system')


# Need to check
# def empty_trash(parent: None = None):
#     system = platform.system()
#
#     if system == 'Windows':
#         try:
#             import winshell  # pip install winshell pywin32
#             winshell.recycle_bin().empty(confirm=False, show_progress=False, sound=False)
#         except Exception as e:
#             print(f"Error emptying recycle bin: {e}")
#     elif system == 'Linux':
#         trash_files_path = os.path.expanduser('~/.local/share/Trash/files')
#         trash_info_path = os.path.expanduser('~/.local/share/Trash/info')
#         subprocess.Popen(['rm', '-rf', trash_files_path, trash_info_path])
#     else:
#         messagebox_error(parent, title='Cannot open this system')