"""
renderers/font_renderer.py
字型檔極速預覽器：
- 支援 TTF / OTF / WOFF
- 使用 Qt QFontDatabase.addApplicationFont 原生動態載入
- 多字號瀑布流排版展示（Alphabet, Numbers, 經典中英文字句）
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from renderers.base import BaseRenderer


class FontRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._font_id: int = -1

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 動態載入字型
        font_id = QFontDatabase.addApplicationFont(str(path))
        self._font_id = font_id

        if font_id == -1:
            err = QLabel(f"⚠️ 無法解析此字型檔案\n{path.name}")
            err.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(err)
            return container

        families = QFontDatabase.applicationFontFamilies(font_id)
        family_name = families[0] if families else path.stem

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("background: #121214;")

        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setContentsMargins(28, 20, 28, 20)
        c_layout.setSpacing(20)

        # 字型標題
        title_box = QVBoxLayout()
        name_lbl = QLabel(family_name)
        name_lbl.setStyleSheet("color: #6366f1; font-size: 22px; font-weight: bold;")
        sub_lbl = QLabel(f"格式: {path.suffix.upper().lstrip('.')}  ·  檔案大小: {path.stat().st_size / 1024:.1f} KB")
        sub_lbl.setStyleSheet("color: #888888; font-size: 12px;")
        title_box.addWidget(name_lbl)
        title_box.addWidget(sub_lbl)
        c_layout.addLayout(title_box)

        # 字型樣本展示（英文字母、數字、符號）
        sample_chars = QLabel("ABCDEFGHIJKLMNOPQRSTUVWXYZ\nabcdefghijklmnopqrstuvwxyz\n0123456789 !@#$%^&*()")
        font_chars = QFont(family_name, 16)
        sample_chars.setFont(font_chars)
        sample_chars.setStyleSheet("""
            background: #1a1a1e;
            color: #d1d5db;
            padding: 16px;
            border-radius: 8px;
            line-height: 1.6;
        """)
        c_layout.addWidget(sample_chars)

        # 瀑布流（不同字號展示）
        for size, sample_text in [
            (32, "The quick brown fox jumps over the lazy dog."),
            (24, "永和九年，歲在癸丑，暮春之初，會於會稽山陰之蘭亭。"),
            (18, "Pack my box with five dozen liquor jugs. 1234567890"),
            (14, "天地玄黃，宇宙洪荒。日月盈昃，辰宿列張。寒來暑往，秋收冬藏。"),
        ]:
            row = QVBoxLayout()
            label_text = QLabel(sample_text)
            label_text.setFont(QFont(family_name, size))
            label_text.setStyleSheet("color: #f3f4f6; margin-bottom: 2px;")
            label_text.setWordWrap(True)

            size_tag = QLabel(f"{size} pt")
            size_tag.setStyleSheet("color: #6b7280; font-size: 11px;")

            row.addWidget(size_tag)
            row.addWidget(label_text)
            c_layout.addLayout(row)

        c_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)

        return container

    def cleanup(self) -> None:
        if self._font_id != -1:
            QFontDatabase.removeApplicationFont(self._font_id)
            self._font_id = -1
