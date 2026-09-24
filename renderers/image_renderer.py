"""
renderers/image_renderer.py
macOS QuickLook 頂級圖片預覽體驗：
- 等比例自適應無黑邊
- PNG / WebP 透明微型棋盤格（Checkerboard）
- SmoothTransformation 平滑縮放（抗鋸齒/無摩爾紋）
- 滑鼠滾輪縮放（Zoom）+ 拖曳平移（Pan）+ 雙擊復原
- 浮動半透明 HUD 膠囊標籤（解析度 / 大小 / 縮放百分比）
- GIF 動態圖播放
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QImageReader,
    QMouseEvent,
    QMovie,
    QPainter,
    QPaintEvent,
    QPixmap,
    QWheelEvent,
)
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from renderers.base import BaseRenderer


def _make_checkerboard_pattern(size: int = 12) -> QPixmap:
    """產生精緻透明棋盤格圖樣。"""
    pm = QPixmap(size * 2, size * 2)
    p = QPainter(pm)
    c1 = QColor(26, 26, 30)
    c2 = QColor(36, 36, 42)
    p.fillRect(0, 0, size, size, c1)
    p.fillRect(size, size, size, size, c1)
    p.fillRect(size, 0, size, size, c2)
    p.fillRect(0, size, size, size, c2)
    p.end()
    return pm


class _InteractiveImageViewer(QWidget):
    def __init__(self, pixmap: QPixmap, file_size_str: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._pixmap = pixmap
        self._orig_w = pixmap.width()
        self._orig_h = pixmap.height()
        self._file_size_str = file_size_str

        # 縮放與平移狀態
        self._zoom_factor = 1.0  # 相對於適應尺寸的倍率
        self._fit_scale = 1.0
        self._pan_offset = QPointF(0, 0)
        self._drag_start = QPointF(0, 0)
        self._is_dragging = False

        self._checkerboard = _make_checkerboard_pattern()
        self.setMouseTracking(True)

        # 懸浮 HUD 標籤
        self._hud = QLabel(self)
        self._hud.setStyleSheet("""
            QLabel {
                background: rgba(15, 15, 18, 0.78);
                color: #e2e8f0;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                padding: 4px 12px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                font-weight: 500;
            }
        """)
        self._update_hud_text()

    def _update_hud_text(self) -> None:
        pct = int(self._zoom_factor * 100)
        self._hud.setText(f"{self._orig_w} × {self._orig_h}  ·  {self._file_size_str}  ·  {pct}%")
        self._hud.adjustSize()
        self._position_hud()

    def _position_hud(self) -> None:
        margin_bottom = 12
        x = (self.width() - self._hud.width()) // 2
        y = self.height() - self._hud.height() - margin_bottom
        self._hud.move(max(10, x), max(10, y))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._recalc_fit_scale()
        self._position_hud()

    def _recalc_fit_scale(self) -> None:
        if self._orig_w == 0 or self._orig_h == 0:
            return
        w = max(10, self.width())
        h = max(10, self.height())
        scale_w = w / self._orig_w
        scale_h = h / self._orig_h
        self._fit_scale = min(scale_w, scale_h, 1.0)

    def paintEvent(self, event: QPaintEvent) -> None:
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        # 1. 繪製微型棋盤格底色（便於檢視透明 PNG/SVG）
        p.fillRect(self.rect(), QBrush(self._checkerboard))

        # 2. 計算目標尺寸與中心位置
        current_scale = self._fit_scale * self._zoom_factor
        draw_w = self._orig_w * current_scale
        draw_h = self._orig_h * current_scale

        center_x = (self.width() - draw_w) / 2.0 + self._pan_offset.x()
        center_y = (self.height() - draw_h) / 2.0 + self._pan_offset.y()

        target_rect = QRectF(center_x, center_y, draw_w, draw_h)
        p.drawPixmap(target_rect.toRect(), self._pixmap)
        p.end()

    # ── 互動：滾輪縮放 ────────────────────────────────────────────────────────
    def wheelEvent(self, event: QWheelEvent) -> None:
        angle = event.angleDelta().y()
        zoom_delta = 1.15 if angle > 0 else (1.0 / 1.15)
        new_zoom = max(0.2, min(self._zoom_factor * zoom_delta, 10.0))

        # 以游標位置為縮放中心
        cursor_pos = event.position()
        self._zoom_factor = new_zoom
        self._update_hud_text()
        self.update()

    # ── 互動：拖曳平移 ────────────────────────────────────────────────────────
    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_start = event.position() - self._pan_offset

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging:
            self._pan_offset = event.position() - self._drag_start
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """雙擊復原為最適大小。"""
        self._zoom_factor = 1.0
        self._pan_offset = QPointF(0, 0)
        self._update_hud_text()
        self.update()


class ImageRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._movie: QMovie | None = None

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        suffix = path.suffix.lower()

        # 動態 GIF 支援
        if suffix == ".gif":
            self._movie = QMovie(str(path))
            if self._movie.isValid():
                label = QLabel()
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setMovie(self._movie)
                self._movie.start()
                layout.addWidget(label)
                return container

        # 靜態圖片（QImageReader）
        reader = QImageReader(str(path))
        reader.setAutoTransform(True)
        pixmap = QPixmap.fromImageReader(reader)

        if pixmap.isNull():
            label = QLabel(f"⚠️ 無法讀取圖片格式\n{path.name}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(label)
            return container

        try:
            size_bytes = path.stat().st_size
            if size_bytes < 1024 * 1024:
                file_size_str = f"{size_bytes / 1024:.1f} KB"
            else:
                file_size_str = f"{size_bytes / (1024 * 1024):.2f} MB"
        except OSError:
            file_size_str = "?"

        viewer = _InteractiveImageViewer(pixmap, file_size_str)
        layout.addWidget(viewer)
        return container

    def cleanup(self) -> None:
        if self._movie:
            self._movie.stop()
            self._movie = None
