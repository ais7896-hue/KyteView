"""
main.py
KyteView 入口：系統托盤常駐 + 全域 Space 監聽。
"""
from __future__ import annotations

import sys
import os
from pathlib import Path
from typing import Optional

# 確保專案根目錄在 PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtCore import QTimer, Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu

from core.file_watcher import get_selected_files, is_explorer_window, get_file_nav_context
from core.hotkey_listener import HotkeyListener
from ui.preview_window import PreviewWindow


def _make_tray_icon() -> QIcon:
    base_dir = Path(__file__).resolve().parent
    ico_path = base_dir / "assets" / "icon.ico"
    png_path = base_dir / "assets" / "icon.png"
    if ico_path.exists():
        return QIcon(str(ico_path))
    if png_path.exists():
        return QIcon(str(png_path))

    px = QPixmap(32, 32)
    px.fill(QColor(0, 0, 0, 0))
    p = QPainter(px)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor("#6366f1"))
    p.setPen(QColor(0, 0, 0, 0))
    p.drawRoundedRect(2, 2, 28, 28, 6, 6)
    p.setPen(QColor("white"))
    p.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    p.drawText(px.rect(), Qt.AlignmentFlag.AlignCenter, "K")
    p.end()
    return QIcon(px)

class KyteViewApp(QObject):
    # Signal 是執行緒安全的，hook 執行緒 emit → 主執行緒 slot 執行
    _sig_open       = Signal(object)  # hwnd (64-bit safe)
    _sig_close      = Signal()
    _sig_navigate   = Signal(str)     # direction
    _sig_peek       = Signal(bool)    # peek through (Alt/Ctrl)
    _sig_toggle_pin = Signal()        # toggle side-pin mode (Tab)

    def __init__(self, app: QApplication) -> None:
        super().__init__()
        self._app = app
        self._window = PreviewWindow()
        self._current_paths: list[Path] = []
        self._current_index: int = 0
        self._last_explorer_hwnd: Optional[int] = None

        # 連接 Signal → Slot（均在主執行緒執行）
        self._sig_open.connect(self._on_open_main)
        self._sig_close.connect(self._on_close_main)
        self._sig_navigate.connect(self._on_navigate_main)
        self._sig_peek.connect(self._window.set_peek_through)
        self._sig_toggle_pin.connect(self._window.toggle_pin_mode)

        self._setup_tray()
        self._setup_hotkey()

    # ── 托盤 ──────────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        from config.settings import settings

        self._tray = QSystemTrayIcon(_make_tray_icon(), self._app)
        self._tray.setToolTip("KyteView")

        menu = QMenu()
        menu.addAction("KyteView").setEnabled(False)
        menu.addSeparator()

        act_theme = menu.addAction(f"切換主題 (目前: {'深色' if settings.is_dark() else '淺色'})")
        def _toggle_and_update():
            settings.toggle_theme()
            act_theme.setText(f"切換主題 (目前: {'深色' if settings.is_dark() else '淺色'})")
        act_theme.triggered.connect(_toggle_and_update)

        act_pin = menu.addAction("切換側邊釘選模式 (Tab)")
        act_pin.triggered.connect(self._window.toggle_pin_mode)

        act_settings = menu.addAction("⚙️ 偏好設定...")
        act_settings.triggered.connect(self._window.open_settings)

        menu.addSeparator()
        menu.addAction("結束").triggered.connect(self._quit)

        self._tray.setContextMenu(menu)
        self._tray.show()

    # ── 熱鍵 ──────────────────────────────────────────────────────────────────

    def _setup_hotkey(self) -> None:
        self._listener = HotkeyListener(
            on_open=lambda hwnd: self._sig_open.emit(hwnd),
            on_close=lambda: self._sig_close.emit(),
            on_navigate=lambda d: self._sig_navigate.emit(d),
            on_peek=lambda enabled: self._sig_peek.emit(enabled),
            on_toggle_pin=lambda: self._sig_toggle_pin.emit(),
            is_preview_visible=self._window.is_visible,
            is_explorer=is_explorer_window,
        )
        self._listener.start()

    # ── Slot（主執行緒）──────────────────────────────────────────────────────

    def _on_open_main(self, hwnd: int) -> None:
        """COM 呼叫在主執行緒執行，安全。"""
        self._last_explorer_hwnd = hwnd
        paths = get_selected_files(hwnd)
        if not paths:
            return
        self._current_paths = paths
        self._current_index = 0
        self._show_current()

    def _on_close_main(self) -> None:
        self._window.hide_window()

    def _on_navigate_main(self, direction: str) -> None:
        """方向鍵：放行後 60ms 重新讀取 Explorer 選取並刷新。"""
        def _refresh():
            target_hwnd = getattr(self, "_last_explorer_hwnd", None)
            paths = get_selected_files(target_hwnd)
            if paths and paths != self._current_paths:
                self._current_paths = paths
                self._current_index = 0
                self._show_current()
        QTimer.singleShot(60, _refresh)

    def _show_current(self) -> None:
        if not self._current_paths:
            return
        idx = max(0, min(self._current_index, len(self._current_paths) - 1))
        cur_path = self._current_paths[idx]
        index_info, breadcrumb = get_file_nav_context(
            cur_path, idx, len(self._current_paths)
        )
        exp_hwnd = getattr(self, "_last_explorer_hwnd", None)
        self._window.show_file(cur_path, index_info, breadcrumb, exp_hwnd)

    # ── 結束 ──────────────────────────────────────────────────────────────────

    def _quit(self) -> None:
        self._listener.stop()
        self._tray.hide()
        self._app.quit()


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(_make_tray_icon())

    kyte = KyteViewApp(app)

    print("[OK] KyteView started. Press Space in Explorer to preview.")
    sys.exit(app.exec())



if __name__ == "__main__":
    main()
