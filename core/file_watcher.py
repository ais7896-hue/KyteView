"""
core/file_watcher.py
取得 Windows Explorer 當前選取的檔案路徑。
支援一般資料夾視窗 + 桌面 (Progman/WorkerW) 兩種場景。
回傳 List[Path]，支援多選。
"""
from __future__ import annotations

import pythoncom
import win32com.client
import win32gui
import win32con
from pathlib import Path
from typing import Optional


def _get_desktop_selected() -> list[Path]:
    """
    桌面死角處理：桌面不是一般 Explorer 視窗，
    而是 Progman -> WorkerW -> SHELLDLL_DefView。
    透過 IShellWindows + CSIDL_DESKTOP 取得選取檔案。
    """
    try:
        shell = win32com.client.Dispatch("Shell.Application")
        # 嘗試從所有視窗中找 Desktop
        for window in shell.Windows():
            try:
                # LocationURL 為空通常是桌面
                if not window.LocationURL:
                    selected = window.Document.SelectedItems()
                    return [Path(item.Path) for item in selected]
            except Exception:
                continue
    except Exception:
        pass
    return []


def get_selected_files(hwnd: Optional[int] = None) -> list[Path]:
    """
    取得 Explorer 當前選取的檔案清單。
    """
    pythoncom.CoInitialize()
    try:
        if hwnd is None:
            hwnd = win32gui.GetForegroundWindow()

        shell = win32com.client.Dispatch("Shell.Application")
        windows = shell.Windows()
        
        # 1. 精準比對：window.HWND == hwnd
        for window in windows:
            try:
                if window.HWND == hwnd:
                    selected = window.Document.SelectedItems()
                    return [Path(item.Path) for item in selected]
            except Exception:
                continue

        # 2. 根視窗比對（處理 Explorer 內部控制項焦點時 hwnd 不同的問題）
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT) if hwnd else 0
        if root_hwnd and root_hwnd != hwnd:
            for window in windows:
                try:
                    if window.HWND == root_hwnd:
                        selected = window.Document.SelectedItems()
                        return [Path(item.Path) for item in selected]
                except Exception:
                    continue

        # 3. 若只有一個 Explorer 視窗，直接取用
        exp_windows = []
        for window in windows:
            try:
                if getattr(window, "Document", None) is not None:
                    exp_windows.append(window)
            except Exception:
                pass
        if len(exp_windows) == 1:
            try:
                selected = exp_windows[0].Document.SelectedItems()
                return [Path(item.Path) for item in selected]
            except Exception:
                pass

        # 4. Fallback：桌面場景
        return _get_desktop_selected()

    except Exception:
        return []
    finally:
        pythoncom.CoUninitialize()


def is_explorer_window(hwnd: int) -> bool:
    """判斷指定 hwnd 是否為 Explorer 或桌面視窗。"""
    class_name = win32gui.GetClassName(hwnd)
    # CabinetWClass = 資料夾視窗, WorkerW/Progman = 桌面
    return class_name in ("CabinetWClass", "ExploreWClass", "WorkerW", "Progman")


def get_file_nav_context(
    path: Path, current_index: int = 0, total_selected: int = 1
) -> tuple[str, str]:
    """
    回傳 (index_info, breadcrumb)。
    例如: ("第 5 / 24 個檔案", "Downloads > Projects")
    """
    parts = path.parts
    if len(parts) >= 3:
        breadcrumb = f"{parts[-3]} > {parts[-2]}"
    elif len(parts) >= 2:
        breadcrumb = f"{parts[-2]}"
    else:
        breadcrumb = "本機"

    if total_selected > 1:
        return f"選取 {current_index + 1} / {total_selected}", breadcrumb

    try:
        parent = path.parent
        if parent.exists() and parent.is_dir():
            files = [
                p
                for p in parent.iterdir()
                if p.is_file() and not p.name.startswith(".")
            ]
            files.sort(key=lambda p: p.name.lower())
            if path in files:
                idx = files.index(path) + 1
                return f"第 {idx} / {len(files)} 個檔案", breadcrumb
    except Exception:
        pass

    return "", breadcrumb
