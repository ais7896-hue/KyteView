"""
main.py
KyteView 入口：單一實例防多開 + 系統托盤常駐 + 全域 Space 監聽 + 檔案總管焦點提示。
"""
from __future__ import annotations

import sys
import os
import time
from pathlib import Path
from typing import Optional

# 確保專案根目錄在 PYTHONPATH
sys.path.insert(0, os.path.dirname(__file__))

import win32gui
from PySide6.QtCore import QTimer, Qt, QObject, Signal
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtWidgets import QApplication, QSystemTrayIcon, QMenu
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from config.settings import settings
from core.file_watcher import get_selected_files, is_explorer_window, get_file_nav_context
from core.hotkey_listener import HotkeyListener
from ui.preview_window import PreviewWindow
from ui.status_pill import StatusPill

IPC_SERVER_NAME = "KyteView_SingleInstance_IPC"


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

    def __init__(self, app: QApplication, local_server: Optional[QLocalServer] = None) -> None:
        super().__init__()
        self._app = app
        self._local_server = local_server
        self._window = PreviewWindow()
        self._pill = StatusPill()
        self._current_paths: list[Path] = []
        self._current_index: int = 0
        self._last_explorer_hwnd: Optional[int] = None

        # 狀態監視
        self._last_checked_hwnd: Optional[int] = None
        self._last_was_explorer: bool = False
        self._last_hud_time: float = 0.0

        # 連接 Signal → Slot（均在主執行緒執行）
        self._sig_open.connect(self._on_open_main)
        self._sig_close.connect(self._on_close_main)
        self._sig_navigate.connect(self._on_navigate_main)
        self._sig_peek.connect(self._window.set_peek_through)
        self._sig_toggle_pin.connect(self._window.toggle_pin_mode)

        self._setup_ipc()
        self._setup_tray()
        self._setup_hotkey()
        self._setup_focus_monitor()

    # ── 單一實例 IPC ──────────────────────────────────────────────────────────

    def _setup_ipc(self) -> None:
        if self._local_server:
            self._local_server.newConnection.connect(self._on_ipc_connection)

    def _on_ipc_connection(self) -> None:
        """當另一個 KyteView 或外部程式 (KyteRename/KyteShelf) 傳送訊號時接收處理。"""
        if not self._local_server:
            return
        sock = self._local_server.nextPendingConnection()
        if not sock:
            return
        sock.waitForReadyRead(300)
        data = sock.readAll().data().decode("utf-8", errors="ignore").strip()
        sock.disconnectFromServer()

        if data.startswith("PREVIEW_UPDATE:"):
            target_str = data[len("PREVIEW_UPDATE:"):].strip()
            if target_str:
                self.preview_external_path(Path(target_str), is_update_only=True)
        elif data.startswith("PREVIEW:"):
            target_str = data[len("PREVIEW:"):].strip()
            if target_str:
                self.preview_external_path(Path(target_str), is_update_only=False)
        elif "SHOW_ALIVE" in data:
            self.notify_already_running()

    def preview_external_path(self, path: Path, is_update_only: bool = False) -> None:
        """接收外部程式 (如 KyteRename / KyteShelf) 傳來的特定檔案預覽請求。"""
        if not path.exists():
            return

        # 若僅為游標移動同步 (is_update_only)，且目前預覽視窗根本未開啟，則靜默忽略
        if is_update_only and not self._window.is_visible():
            return

        # 若使用者按下 Space 觸發，且目前已在預覽同一個檔案且視窗開啟中，則 Space 鍵行為是隱藏切換 (Toggle)
        if not is_update_only and self._window.is_visible() and getattr(self, "_current_paths", None):
            if self._current_paths and self._current_paths[self._current_index].resolve() == path.resolve():
                self._window.hide_window()
                return

        self._current_paths = [path]
        self._current_index = 0
        index_info, breadcrumb = get_file_nav_context(path, 0, 1)
        self._window.show_file(path, index_info, breadcrumb, None)

        # 僅當不是單純上下鍵同步時才拉到前景，避免搶走 KyteRename 等呼叫端的鍵盤焦點
        if not is_update_only:
            self._window.activateWindow()
            self._window.raise_()

    def notify_already_running(self) -> None:
        """通知使用者程式早已在運行中，避免重複開啟。"""
        self._tray.showMessage(
            "KyteView 正在背景運行中",
            "程式已在此常駐！在檔案總管中選取檔案，按下 [空白鍵 Space] 即可預覽。\n請勿重複啟動。",
            QSystemTrayIcon.MessageIcon.Information,
            4000,
        )
        self._pill.flash("⚡ KyteView 正在運行中 · [Space] 預覽", 3000)

    # ── 托盤 ──────────────────────────────────────────────────────────────────

    def _setup_tray(self) -> None:
        self._tray = QSystemTrayIcon(_make_tray_icon(), self._app)
        self._tray.setToolTip("KyteView (運行中)\n在檔案總管選取檔案後按 [Space] 快速預覽")
        self._tray.activated.connect(self._on_tray_activated)

        menu = QMenu()
        menu.addAction("KyteView (運行中)").setEnabled(False)
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

        # 啟動時發送歡迎提示（如果設定開啟）
        if settings.get("show_startup_notification", True):
            QTimer.singleShot(600, self._show_startup_balloon)

    def _show_startup_balloon(self) -> None:
        self._tray.showMessage(
            "KyteView 已在背景就緒",
            "在檔案總管中選取任意檔案，按下 [空白鍵] 即可快速預覽！",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        """點擊托盤圖示回饋。"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 左鍵單擊
            if self._window.is_visible():
                self._window.activateWindow()
                self._window.raise_()
            else:
                self._pill.flash("⚡ KyteView 待命中 · [Space] 預覽", 2000)

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

    # ── 檔案總管焦點監控 (HUD 微光提示) ────────────────────────────────────────

    def _setup_focus_monitor(self) -> None:
        self._focus_timer = QTimer(self)
        self._focus_timer.setInterval(400)
        self._focus_timer.timeout.connect(self._check_explorer_focus)
        self._focus_timer.start()

    def _check_explorer_focus(self) -> None:
        if not settings.get("show_explorer_hud", True):
            return
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd or hwnd == self._last_checked_hwnd:
                return

            self._last_checked_hwnd = hwnd
            is_exp = is_explorer_window(hwnd)

            # 剛由其他程式切換進入檔案總管
            if is_exp and not self._last_was_explorer:
                now = time.time()
                # 8 秒冷卻機制，避免使用者頻繁切換視窗時被干擾
                if now - self._last_hud_time > 8.0:
                    self._last_hud_time = now
                    self._pill.flash("⚡ KyteView 待命中 · [Space] 預覽", 1500)

            self._last_was_explorer = is_exp
        except Exception:
            pass

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
        if hasattr(self, "_focus_timer"):
            self._focus_timer.stop()
        if self._local_server:
            self._local_server.close()
            QLocalServer.removeServer(IPC_SERVER_NAME)
        self._listener.stop()
        self._tray.hide()
        self._pill.hide()
        self._app.quit()


def main() -> None:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(_make_tray_icon())

    # ── 單一實例檢測 (Single Instance Check) ─────────────────────────────────
    target_arg_path = None
    if len(sys.argv) > 1:
        cand_p = Path(sys.argv[1])
        if cand_p.exists():
            target_arg_path = cand_p.resolve()

    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(300):
        # 已有執行中實例，通知預覽或喚醒並退出
        if target_arg_path:
            socket.write(f"PREVIEW:{str(target_arg_path)}\n".encode("utf-8"))
        else:
            socket.write(b"SHOW_ALIVE")
        socket.waitForBytesWritten(300)
        socket.disconnectFromServer()
        print("[INFO] KyteView 已在執行中，已向主行程發送提示並安全退出。")
        sys.exit(0)

    # 首次啟動：建立 IPC 伺服器
    QLocalServer.removeServer(IPC_SERVER_NAME)
    local_server = QLocalServer()
    if not local_server.listen(IPC_SERVER_NAME):
        print(f"[WARN] QLocalServer 監聽失敗: {local_server.errorString()}")

    kyte = KyteViewApp(app, local_server)
    if target_arg_path:
        QTimer.singleShot(150, lambda: kyte.preview_external_path(target_arg_path))

    print("[OK] KyteView started. Press Space in Explorer to preview.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
