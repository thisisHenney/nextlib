"""
Backward-compatible wrapper.
Use dialogbox_improved_v2 directly for new code.
"""
from nextlib.dialogbox.dialogbox_improved_v2 import (
    DialogBoxConfig,
    DirDialogBox,
    FileDialogBox,
    CommonFilters,
    select_folder,
    select_file,
    select_files,
    save_as,
)

__all__ = [
    "DialogBoxConfig",
    "DirDialogBox",
    "FileDialogBox",
    "CommonFilters",
    "select_folder",
    "select_file",
    "select_files",
    "save_as",
]
