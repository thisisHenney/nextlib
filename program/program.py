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
        subprocess.Popen(['explorer', str(Path(path).resolve())])
    elif system == 'Linux':
        try:
            subprocess.Popen(['xdg-open', path])
        except FileNotFoundError:
            subprocess.Popen(['nautilus', path])
    else:
        messagebox_error(parent, text='Cannot open this system')

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


