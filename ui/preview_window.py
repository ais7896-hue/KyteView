"""
ui/preview_window.py
KyteView 主預覽視窗。
- 無邊框、毛玻璃/Acrylic（Windows 11 DWM）
- ESC / 二次 Space 關閉
- 淡入動畫
- 拖曳移動
- 多螢幕感知（在游標所在螢幕彈出）
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
from pathlib import Path
from typing import Optional, Any

from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    QPoint, QRect, QSize, Property,
)
from PySide6.QtGui import (
    QColor, QPainter, QPaintEvent, QFont, QFontDatabase,
    QMouseEvent, QKeyEvent, QCursor,
)
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QSizeGrip, QFrame, QSizePolicy,
)

from core.preview_router import get_renderer
from config.settings import settings
from config.theme import get_theme_colors
import win32gui


# ── Windows 11 毛玻璃 ─────────────────────────────────────────────────────────
def _apply_acrylic(hwnd: int) -> None:
    """嘗試啟用 Windows 11 Mica/Acrylic 材質，失敗靜默忽略。"""
    try:
        DWMWA_SYSTEMBACKDROP_TYPE = 38
        DWMSBT_MAINWINDOW = 2  # Mica
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(ctypes.c_int(DWMSBT_MAINWINDOW)),
            ctypes.sizeof(ctypes.c_int),
        )
    except Exception:
        pass


# ── 工具列 ────────────────────────────────────────────────────────────────────
class _Toolbar(QWidget):
    def __init__(self, parent: "PreviewWindow"):
        super().__init__(parent)
        self._window = parent
        self._drag_start: Optional[QPoint] = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 6, 10, 6)
        layout.setSpacing(8)

        # 左側標題容器（垂直雙行排版：主檔名+膠囊 Badge，下方為路徑與大小）
        left_box = QVBoxLayout()
        left_box.setContentsMargins(0, 0, 0, 0)
        left_box.setSpacing(2)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        # 巢狀導航返回按鈕
        self.btn_back = QPushButton("⬅ 返回壓縮包")
        self.btn_back.setObjectName("btn_back")
        self.btn_back.setFixedHeight(22)
        self.btn_back.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_back.setVisible(False)
        self.btn_back.clicked.connect(parent.navigate_back)
        title_row.addWidget(self.btn_back)

        # 檔案名稱
        self.title = QLabel("—")
        self.title.setMinimumWidth(0)
        self.title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        title_row.addWidget(self.title)

        # 序號膠囊 Badge (如 9 / 16)
        self.badge = QLabel("")
        self.badge.setVisible(False)
        title_row.addWidget(self.badge)
        title_row.addStretch()

        left_box.addLayout(title_row)

        # 副標（大小、類型、路徑層級）
        self.subtitle = QLabel("")
        self.subtitle.setMinimumWidth(0)
        self.subtitle.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        left_box.addWidget(self.subtitle)

        layout.addLayout(left_box, 1)

        # 右側操作按鈕群（統一俐落單色字元）
        self.btn_pin = self._make_btn("◨", "快速側邊釘選模式 (Tab)")
        self.btn_pin.clicked.connect(parent.toggle_pin_mode)
        layout.addWidget(self.btn_pin)

        self.btn_theme = self._make_btn("☼", "切換深色/淺色主題")
        self.btn_theme.clicked.connect(parent.toggle_theme)
        layout.addWidget(self.btn_theme)

        self.btn_settings = self._make_btn("⚙", "偏好設定 (Ctrl + ,)")
        self.btn_settings.clicked.connect(parent.open_settings)
        layout.addWidget(self.btn_settings)

        btn_copy = self._make_btn("⎘", "複製路徑")
        btn_copy.clicked.connect(parent.copy_path)
        layout.addWidget(btn_copy)

        btn_open = self._make_btn("↗", "用預設程式開啟")
        btn_open.clicked.connect(parent.open_externally)
        layout.addWidget(btn_open)

        btn_close = self._make_btn("✕", "關閉 (ESC)")
        btn_close.setObjectName("btn_close")
        btn_close.clicked.connect(parent.hide_window)
        layout.addWidget(btn_close)

        self.setFixedHeight(46)
        self.apply_theme()

    def apply_theme(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()
        self.btn_theme.setText("☼" if is_dark else "☽")
        self.title.setStyleSheet(f"color: {c['title_color']}; font-weight: 600; font-size: 13px;")
        self.subtitle.setStyleSheet(f"color: {c['subtitle_color']}; font-size: 11px;")

        badge_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        badge_c = "#a1a1aa" if is_dark else "#71717a"
        self.badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_bg};
                color: {badge_c};
                border-radius: 4px;
                padding: 1px 6px;
                font-size: 10px;
                font-weight: 500;
            }}
        """)

        self.setStyleSheet(f"""
            QWidget {{ background: transparent; }}
            QPushButton {{
                background: transparent;
                color: {c['btn_color']};
                border: none;
                border-radius: 6px;
                font-family: 'Segoe UI Symbol', 'Segoe UI', -apple-system, sans-serif;
                font-size: 13px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
                padding: 0;
            }}
            QPushButton:hover {{
                background: {c['btn_hover']};
                color: {c['title_color']};
            }}
            QPushButton#btn_close:hover {{
                background: {'rgba(239, 68, 68, 0.2)' if is_dark else 'rgba(239, 68, 68, 0.12)'};
                color: #ef4444;
            }}
            QPushButton#btn_back {{
                background: {'rgba(99, 102, 241, 0.18)' if is_dark else 'rgba(79, 70, 229, 0.12)'};
                color: {'#818cf8' if is_dark else '#4f46e5'};
                font-size: 11px;
                font-weight: 600;
                min-width: 90px;
                max-width: 90px;
                height: 22px;
                padding: 0 6px;
                border-radius: 4px;
                border: 1px solid {'rgba(99, 102, 241, 0.35)' if is_dark else 'rgba(79, 70, 229, 0.25)'};
            }}
            QPushButton#btn_back:hover {{
                background: {'#6366f1' if is_dark else '#4f46e5'};
                color: #ffffff;
            }}
        """)

    def _make_btn(self, text: str, tip: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setToolTip(tip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def set_file_info(self, path: Path, index_info: str = "", breadcrumb: str = "") -> None:
        self.title.setText(path.name)
        if index_info:
            self.badge.setText(index_info)
            self.badge.setVisible(True)
        else:
            self.badge.setVisible(False)

        try:
            size = path.stat().st_size
            size_str = _fmt_size(size)
        except OSError:
            size_str = "?"

        ext = path.suffix.upper().lstrip('.') or 'FILE'
        bc_prefix = f"{breadcrumb}  ·  " if breadcrumb else ""
        self.subtitle.setText(f"{bc_prefix}{ext}  ·  {size_str}")

    # 拖曳移動視窗
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start = event.globalPosition().toPoint() - self._window.pos()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start and event.buttons() & Qt.MouseButton.LeftButton:
            self._window.move(event.globalPosition().toPoint() - self._drag_start)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_start = None


# ── 主視窗 ────────────────────────────────────────────────────────────────────
class PreviewWindow(QWidget):
    def __init__(self) -> None:
        super().__init__(
            None,
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)  # 不奪走 Explorer 焦點

        self._current_path: Optional[Path] = None
        self._content_widget: Optional[QWidget] = None
        self._current_renderer: Optional[Any] = None

        self._is_pinned: bool = False
        self._last_explorer_hwnd: Optional[int] = None
        self._last_index_info: str = ""
        self._last_breadcrumb: str = ""
        self._settings_dialog = None
        self._history_stack: list[tuple[Optional[Path], str, str]] = []

        self._build_ui()
        self.apply_theme()
        settings.theme_changed.connect(self._on_theme_changed)
        settings.settings_changed.connect(self._on_settings_changed)

        # 視窗最小與預設大小（允許自由縮小至 200x150）
        self.setMinimumSize(200, 150)
        self.resize(820, 600)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(1, 1, 1, 1)
        root_layout.setSpacing(0)

        # 外框容器（用於統一背景 + 邊框）
        self._frame = QFrame()
        self._frame.setObjectName("frame")
        frame_layout = QVBoxLayout(self._frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # 工具列
        self._toolbar = _Toolbar(self)
        frame_layout.addWidget(self._toolbar)

        # 分隔線
        self._sep = QFrame()
        self._sep.setFrameShape(QFrame.Shape.HLine)
        frame_layout.addWidget(self._sep)

        # 內容區（動態替換）
        self._content_area = QVBoxLayout()
        self._content_area.setContentsMargins(0, 0, 0, 0)
        frame_layout.addLayout(self._content_area)

        # 右下角 resize grip
        grip_row = QHBoxLayout()
        grip_row.addStretch()
        grip = QSizeGrip(self._frame)
        grip.setStyleSheet("background: transparent;")
        grip_row.addWidget(grip)
        grip_row.setContentsMargins(0, 0, 4, 4)
        frame_layout.addLayout(grip_row)

        root_layout.addWidget(self._frame)

    def apply_theme(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()
        bg_style = c['window_bg'] if settings.enable_acrylic else ("#18181b" if is_dark else "#ffffff")
        scroll_handle_bg = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.18)"
        scroll_handle_hover = "rgba(255, 255, 255, 0.38)" if is_dark else "rgba(0, 0, 0, 0.35)"

        self._frame.setStyleSheet(f"""
            QFrame#frame {{
                background: {bg_style};
                border: 1px solid {c['window_border']};
                border-radius: 12px;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_handle_bg};
                border-radius: 4px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
                height: 0px;
                border: none;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 8px;
                margin: 0 4px 2px 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {scroll_handle_bg};
                border-radius: 4px;
                min-width: 28px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {scroll_handle_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: transparent;
                width: 0px;
                border: none;
            }}
            QScrollBar::corner {{
                background: transparent;
            }}
        """)
        self._sep.setStyleSheet(f"background: {c['sep_color']}; max-height: 1px;")
        if hasattr(self, "_toolbar"):
            self._toolbar.apply_theme()

    def toggle_theme(self) -> None:
        settings.toggle_theme()

    def _on_theme_changed(self, new_theme: str) -> None:
        self.apply_theme()
        if self.isVisible() and self._current_path:
            self.refresh()

    def _on_settings_changed(self, key: str) -> None:
        if key in ("theme_mode", "enable_acrylic"):
            self.apply_theme()
            if self.isVisible() and settings.enable_acrylic:
                _apply_acrylic(int(self.winId()))
        if self.isVisible() and self._current_path:
            self.refresh()

    def open_settings(self) -> None:
        """開啟現代偏好設定視窗。"""
        from ui.settings_dialog import SettingsDialog
        if self._settings_dialog is None:
            self._settings_dialog = SettingsDialog(None)
        else:
            self._settings_dialog.reload_values()
        self._settings_dialog.show()
        self._settings_dialog.raise_()
        self._settings_dialog.activateWindow()

    # ── 新增進階互動模式 ──────────────────────────────────────────────────────

    def set_peek_through(self, enabled: bool) -> None:
        """長按 Alt/Ctrl 微透機制：半透明 0.15 看穿背景。"""
        if not settings.enable_peek:
            return
        self.setWindowOpacity(0.15 if enabled else 1.0)
        if enabled:
            self._frame.setStyleSheet("""
                QFrame#frame {
                    background: rgba(10, 10, 12, 0.12);
                    border: 1px dashed rgba(255, 255, 255, 0.4);
                    border-radius: 12px;
                }
            """)
        else:
            self.apply_theme()

    def toggle_pin_mode(self) -> None:
        """快速側邊釘選模式切換 (Tab)。"""
        if not settings.enable_pin_dock:
            return
        self._is_pinned = not self._is_pinned
        if hasattr(self, "_toolbar"):
            self._toolbar.btn_pin.setText("▣" if self._is_pinned else "◨")
        if self._current_path:
            self._adjust_window_geometry(self._current_path)

    # ── 公開方法 ──────────────────────────────────────────────────────────────

    def show_file(
        self,
        path: Path,
        index_info: str = "",
        breadcrumb: str = "",
        explorer_hwnd: Optional[int] = None,
    ) -> None:
        """顯示指定檔案的預覽。"""
        self._history_stack.clear()
        if hasattr(self, "_toolbar"):
            self._toolbar.btn_back.setVisible(False)

        self._current_path = path
        self._last_index_info = index_info
        self._last_breadcrumb = breadcrumb
        if explorer_hwnd:
            self._last_explorer_hwnd = explorer_hwnd

        self._toolbar.set_file_info(path, index_info, breadcrumb)
        self._load_content(path)
        self._adjust_window_geometry(path)
        self._show_window()

    def open_nested_preview(self, nested_path: Path) -> None:
        """從壓縮包內部雙擊單檔觸發的巢狀就地預覽。"""
        if self._current_path:
            self._history_stack.append((self._current_path, self._last_index_info, self._last_breadcrumb))
            self._toolbar.btn_back.setVisible(True)

        self._current_path = nested_path
        self._toolbar.set_file_info(nested_path, "", f"壓縮包 ➔ {nested_path.name}")
        self._load_content(nested_path)

    def navigate_back(self) -> None:
        """返回前一層（例如從解壓的預覽檔案返回壓縮包清單）。"""
        if not self._history_stack:
            return
        prev_path, prev_index, prev_breadcrumb = self._history_stack.pop()
        if not self._history_stack:
            self._toolbar.btn_back.setVisible(False)

        if prev_path:
            self._current_path = prev_path
            self._last_index_info = prev_index
            self._last_breadcrumb = prev_breadcrumb
            self._toolbar.set_file_info(prev_path, prev_index, prev_breadcrumb)
            self._load_content(prev_path)

    def refresh(self) -> None:
        """方向鍵或主題切換後刷新。"""
        if self._current_path:
            self.show_file(
                self._current_path,
                self._last_index_info,
                self._last_breadcrumb,
                self._last_explorer_hwnd,
            )

    def hide_window(self) -> None:
        self._history_stack.clear()
        if hasattr(self, "_toolbar"):
            self._toolbar.btn_back.setVisible(False)
        if hasattr(self, "_current_renderer") and self._current_renderer:
            self._current_renderer.cleanup()
        self.hide()

    def copy_path(self) -> None:
        if self._current_path:
            QApplication.clipboard().setText(str(self._current_path))

    def open_externally(self) -> None:
        if self._current_path:
            import subprocess
            subprocess.Popen(["explorer", str(self._current_path)], shell=True)

    def is_visible(self) -> bool:
        return self.isVisible()

    # ── 私有方法 ──────────────────────────────────────────────────────────────

    def _load_content(self, path: Path) -> None:
        """安全清空舊 widget，釋放舊 renderer，建立新的 renderer widget。"""
        if hasattr(self, "_current_renderer") and self._current_renderer:
            try:
                self._current_renderer.cleanup()
            except Exception:
                pass
            self._current_renderer = None

        # Qt 官方最安全的 layout 清理方式
        while self._content_area.count():
            item = self._content_area.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self._content_widget = None

        renderer = get_renderer(path)
        self._current_renderer = renderer
        widget = renderer.render(path)
        self._content_widget = widget
        self._content_area.addWidget(widget)

        # 影片解析度自適應回呼
        if hasattr(widget, "resolution_detected"):
            widget.resolution_detected.connect(self._on_video_resolution_ready)

        # 壓縮檔內部巢狀單檔預覽回呼
        if hasattr(widget, "open_nested_file"):
            widget.open_nested_file.connect(self.open_nested_preview)

    def _on_video_resolution_ready(self, orig_w: int, orig_h: int) -> None:
        """影片讀出真實解析度後，動態等比例自適應縮放，避免黑邊。"""
        if self._is_pinned or not self.isVisible() or orig_w <= 0 or orig_h <= 0:
            return

        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        geo: QRect = screen.availableGeometry()

        max_w = int(geo.width() * 0.70)
        max_h = int(geo.height() * 0.70)
        toolbar_h = 46

        avail_w = max_w - 4
        avail_h = max_h - toolbar_h - 4

        scale = min(avail_w / orig_w, avail_h / orig_h)
        target_w = max(360, int(orig_w * scale))
        target_h = max(240, int(orig_h * scale))

        win_w = target_w + 4
        win_h = target_h + toolbar_h + 4

        cur_rect = self.geometry()
        cx = cur_rect.center().x()
        cy = cur_rect.center().y()
        x = max(geo.left() + 20, min(geo.right() - win_w - 20, cx - win_w // 2))
        y = max(geo.top() + 20, min(geo.bottom() - win_h - 20, cy - win_h // 2))

        self.setGeometry(x, y, win_w, win_h)

    def _adjust_window_geometry(self, path: Path) -> None:
        """依檔案類型、側邊釘選模式與 Explorer 智慧避讓偏移計算幾何。"""
        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        geo: QRect = screen.availableGeometry()

        # ── 1. 側邊釘選模式 (Pin to Side / Split View) ──────────────────────
        if self._is_pinned:
            pin_w = max(420, geo.width() // 3)
            pin_h = geo.height()
            pin_x = geo.right() - pin_w
            pin_y = geo.top()
            self.setGeometry(pin_x, pin_y, pin_w, pin_h)
            return

        # ── 2. 正常自適應尺寸計算 ───────────────────────────────────────────
        img_exts = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg"}
        is_image = path.suffix.lower() in img_exts

        # 取得頂層 Explorer 視窗 handle
        import win32con
        exp_hwnd = self._last_explorer_hwnd
        if exp_hwnd and win32gui.IsWindow(exp_hwnd):
            try:
                root_hwnd = win32gui.GetAncestor(exp_hwnd, win32con.GA_ROOT)
                if root_hwnd and win32gui.IsWindow(root_hwnd):
                    exp_hwnd = root_hwnd
            except Exception:
                pass

        # 若目前仍未取得有效 Explorer 視窗，主動向系統探測
        if not (exp_hwnd and win32gui.IsWindow(exp_hwnd)):
            fg = win32gui.GetForegroundWindow()
            if fg and win32gui.IsWindow(fg):
                try:
                    root_fg = win32gui.GetAncestor(fg, win32con.GA_ROOT)
                    fg_target = root_fg if (root_fg and win32gui.IsWindow(root_fg)) else fg
                    if win32gui.GetClassName(fg_target) in ("CabinetWClass", "ExploreWClass"):
                        exp_hwnd = fg_target
                except Exception:
                    pass

        # 若前景非 Explorer，枚舉畫面上可見的 CabinetWClass 視窗
        if not (exp_hwnd and win32gui.IsWindow(exp_hwnd)):
            cabs = []
            def _find_cabs(h, _):
                if win32gui.IsWindowVisible(h):
                    if win32gui.GetClassName(h) in ("CabinetWClass", "ExploreWClass"):
                        cabs.append(h)
            try:
                win32gui.EnumWindows(_find_cabs, None)
                if cabs:
                    exp_hwnd = cabs[0]
            except Exception:
                pass

        is_zoomed = False
        exp_rect = None
        cls_name = ""
        if exp_hwnd and win32gui.IsWindow(exp_hwnd):
            try:
                cls_name = win32gui.GetClassName(exp_hwnd)
                if cls_name not in ("WorkerW", "Progman"):
                    exp_rect = win32gui.GetWindowRect(exp_hwnd)
                    import ctypes
                    is_zoomed = bool(ctypes.windll.user32.IsZoomed(exp_hwnd))
            except Exception as e:
                print(f"[DEBUG Geo Exception] {e}", flush=True)

        # 圖片或標準視窗縮放限制（依設定）
        user_max_ratio = settings.img_max_screen_ratio / 100.0
        scale_limit = 0.55 if is_zoomed else user_max_ratio

        vid_exts = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts"}
        is_video = path.suffix.lower() in vid_exts

        if is_image:
            from PySide6.QtGui import QImageReader
            reader = QImageReader(str(path))
            reader.setAutoTransform(True)
            orig_size = reader.size()

            if orig_size.isValid() and orig_size.width() > 0 and orig_size.height() > 0:
                orig_w = orig_size.width()
                orig_h = orig_size.height()

                max_w = int(geo.width() * scale_limit)
                max_h = int(geo.height() * (0.65 if is_zoomed else user_max_ratio))
                min_w = 200
                min_h = 150
                toolbar_h = 46

                avail_w = max_w - 4
                avail_h = max_h - toolbar_h - 4

                # 小圖保持 1:1 原生尺寸顯示（不強制放大）
                if settings.img_keep_original and orig_w <= avail_w and orig_h <= avail_h:
                    target_w = orig_w
                    target_h = orig_h
                else:
                    scale = min(avail_w / orig_w, avail_h / orig_h)
                    target_w = int(orig_w * scale)
                    target_h = int(orig_h * scale)

                win_w = max(min_w, target_w + 4)
                win_h = max(min_h, target_h + toolbar_h + 4)
            else:
                win_w, win_h = self._get_default_window_size(geo, is_zoomed)
        elif is_video:
            # 影片初始 16:9 黃金比例，若解析度回傳將自動等比例精確調整
            max_w = int(geo.width() * 0.68)
            target_w = min(max_w, 860)
            target_h = int(target_w * 9 / 16)
            win_w = target_w + 4
            win_h = target_h + 46 + 4
        elif path.suffix.lower() == ".pptx":
            # PPTX 專屬 16:9 橫向畫布比例，預設優雅呈現兩側無黑邊
            max_w = int(geo.width() * 0.65)
            target_w = min(max_w, 880)
            target_h = int(target_w * 9 / 16)
            win_w = target_w + 4
            win_h = target_h + 46 + 4
        else:
            win_w, win_h = self._get_default_window_size(geo, is_zoomed)

        # ── 3. 智慧避讓偏移策略 (Smart Offsetting) ──────────────────────────
        if not settings.smart_offset:
            # 關閉避讓：強制置中
            x = geo.left() + (geo.width() - win_w) // 2
            y = geo.top() + (geo.height() - win_h) // 2
            strategy = "Disabled (Centered)"
        elif is_zoomed:
            # 全螢幕最大化：視窗果斷靠向右側（留出左側檔案清單與樹狀導航）
            x = geo.right() - win_w - 40
            y = geo.top() + (geo.height() - win_h) // 2
            strategy = "Zoomed -> Right"
        elif exp_rect:
            l, t, r, b = exp_rect
            exp_center_x = (l + r) / 2.0
            scr_center_x = geo.left() + geo.width() / 2.0

            if exp_center_x < scr_center_x:
                # Explorer 偏左側 → 預覽視窗自動向右側偏移靠放
                x = geo.right() - win_w - 40
                strategy = f"Exp Left ({exp_center_x:.0f} < {scr_center_x:.0f}) -> Right"
            else:
                # Explorer 偏右側 → 預覽視窗自動向左側偏移靠放
                x = geo.left() + 40
                strategy = f"Exp Right ({exp_center_x:.0f} >= {scr_center_x:.0f}) -> Left"
            y = geo.top() + (geo.height() - win_h) // 2
        else:
            # 無位置資訊或桌面：標準中央置中
            x = geo.left() + (geo.width() - win_w) // 2
            y = geo.top() + (geo.height() - win_h) // 2
            strategy = "Center"

        print(f"[SmartOffset] hwnd={exp_hwnd} cls='{cls_name}' rect={exp_rect} -> strategy='{strategy}', pos=({x}, {y}), size=({win_w}, {win_h})", flush=True)

        self.setGeometry(x, y, win_w, win_h)

    def _get_default_window_size(self, geo: QRect, is_zoomed: bool) -> tuple[int, int]:
        """依據使用者設定模式計算預設視窗大小。"""
        mode = settings.window_size_mode
        if mode == "fixed":
            win_w = settings.fixed_width
            win_h = settings.fixed_height
        elif mode == "adaptive":
            win_w = int(geo.width() * settings.adaptive_ratio_w / 100.0)
            win_h = int(geo.height() * settings.adaptive_ratio_h / 100.0)
        else:
            # remember 智慧記憶模式
            win_w, win_h = settings.window_size

        if is_zoomed:
            win_w = min(win_w, int(geo.width() * 0.55))
            win_h = min(win_h, int(geo.height() * 0.65))
        else:
            win_w = min(win_w, int(geo.width() * 0.85))
            win_h = min(win_h, int(geo.height() * 0.85))

        return max(200, win_w), max(150, win_h)

    def _show_window(self) -> None:
        self.setWindowOpacity(1.0)
        self.show()
        self.raise_()
        if settings.enable_acrylic:
            _apply_acrylic(int(self.winId()))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # 非圖片與影片檔案且處於 remember 模式時，自動記憶使用者手動縮放的大小
        if self._current_path:
            media_exts = {
                ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg",
                ".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts",
            }
            if self._current_path.suffix.lower() not in media_exts:
                if settings.window_size_mode == "remember":
                    settings.window_size = (self.width(), self.height())

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide_window()
        elif event.key() == Qt.Key.Key_Backspace and self._history_stack:
            self.navigate_back()
        elif event.key() == Qt.Key.Key_Space:
            # 影片預覽時按 Space 切換播放/暫停，其它檔案則關閉
            if hasattr(self, "_content_widget") and hasattr(self._content_widget, "toggle_play"):
                self._content_widget.toggle_play()
            else:
                self.hide_window()
        elif (event.modifiers() & Qt.KeyboardModifier.ControlModifier) and event.key() == Qt.Key.Key_Comma:
            self.open_settings()
        else:
            super().keyPressEvent(event)


def _fmt_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"
