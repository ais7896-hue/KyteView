"""
renderers/pdf_renderer.py
PDF 高速預覽器：
- pymupdf (fitz) 渲染頁面為高解析度 QPixmap
- 支援上一頁、下一頁、頁碼跳轉
- 自適應縮放與順暢滾動
"""
from __future__ import annotations

from pathlib import Path

import pymupdf

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from renderers.base import BaseRenderer


class PdfRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._doc: pymupdf.Document | None = None
        self._current_page = 0
        self._total_pages = 0
        self._page_label: QLabel | None = None
        self._img_label: QLabel | None = None

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            self._doc = pymupdf.open(str(path))
            self._total_pages = len(self._doc)
            self._current_page = 0
        except Exception as e:
            err = QLabel(f"⚠️ 無法開啟 PDF 檔案\n{e}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(err)
            return container

        if self._total_pages == 0:
            layout.addWidget(QLabel("PDF 文件為空"))
            return container

        # 頂部控制列（頁碼切換）
        top_bar = QWidget()
        top_bar.setStyleSheet("background: #18181b; border-bottom: 1px solid rgba(255,255,255,0.08);")
        bar_layout = QHBoxLayout(top_bar)
        bar_layout.setContentsMargins(12, 6, 12, 6)
        bar_layout.setSpacing(8)

        btn_prev = QPushButton("◀ 上一頁")
        btn_next = QPushButton("下一頁 ▶")
        for b in (btn_prev, btn_next):
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet("""
                QPushButton {
                    background: #27272a;
                    color: #e0e0e0;
                    border: 1px solid rgba(255,255,255,0.1);
                    border-radius: 4px;
                    padding: 3px 10px;
                    font-size: 12px;
                }
                QPushButton:hover { background: #3b3b40; }
            """)

        self._page_label = QLabel(f"1 / {self._total_pages}")
        self._page_label.setStyleSheet("color: #aaa; font-size: 12px; font-weight: 500;")

        bar_layout.addWidget(btn_prev)
        bar_layout.addWidget(btn_next)
        bar_layout.addWidget(self._page_label)
        bar_layout.addStretch()
        layout.addWidget(top_bar)

        # 內容顯示區（ScrollArea）
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: #121214;")

        content_widget = QWidget()
        c_layout = QVBoxLayout(content_widget)
        c_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.setContentsMargins(16, 16, 16, 16)

        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        c_layout.addWidget(self._img_label)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)

        def show_page(page_idx: int):
            if not self._doc:
                return
            page_idx = max(0, min(page_idx, self._total_pages - 1))
            self._current_page = page_idx
            page = self._doc[page_idx]

            # 2x 縮放確保文字高畫質清晰
            zoom = 2.0
            mat = pymupdf.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)

            img = QImage(
                pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
            )
            pixmap = QPixmap.fromImage(img)
            self._img_label.setPixmap(
                pixmap.scaledToWidth(760, Qt.TransformationMode.SmoothTransformation)
            )
            self._page_label.setText(f"{self._current_page + 1} / {self._total_pages}")

        btn_prev.clicked.connect(lambda: show_page(self._current_page - 1))
        btn_next.clicked.connect(lambda: show_page(self._current_page + 1))

        show_page(0)
        return container

    def cleanup(self) -> None:
        if self._doc:
            self._doc.close()
            self._doc = None
