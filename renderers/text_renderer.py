"""
renderers/text_renderer.py
純文字 fallback renderer。
支援大型檔案：只讀前 500 行，超過時顯示提示。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QPalette
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPlainTextEdit, QLabel

from renderers.base import BaseRenderer

MAX_LINES = 500
MAX_BYTES = 512 * 1024  # 512KB 硬上限，防止超大檔案


class TextRenderer(BaseRenderer):
    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        text, truncated, error = _read_text(path)

        if error:
            label = QLabel(f"⚠️ 無法讀取檔案\n{error}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(label)
            return container

        from config.theme import get_theme_colors
        c = get_theme_colors()

        editor = QPlainTextEdit()
        editor.setReadOnly(True)
        editor.setPlainText(text)
        editor.setFont(QFont("Consolas", 11))
        editor.setFrameShape(QPlainTextEdit.Shape.NoFrame)
        from PySide6.QtGui import QTextOption
        editor.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        editor.setStyleSheet(f"""
            QPlainTextEdit {{
                background: transparent;
                color: {c['text_color']};
                selection-background-color: {c['table_select_bg']};
                padding: 4px 8px;
            }}
        """)
        layout.addWidget(editor)

        if truncated:
            bar = QLabel(
                f"⚠️ 僅顯示前 {MAX_LINES} 行  ·  完整檔案：{path.stat().st_size:,} bytes"
            )
            bar.setStyleSheet("""
                background: #2a2a2a;
                color: #858585;
                font-size: 11px;
                padding: 3px 10px;
            """)
            layout.addWidget(bar)

        return container


def _read_text(path: Path) -> tuple[str, bool, str]:
    """
    回傳 (text, is_truncated, error_msg)。
    若為二進位檔案則回傳錯誤提示，避免亂碼。
    """
    try:
        # 二進位檢查：讀取前 1024 bytes，檢查是否有 null byte
        with path.open("rb") as f:
            chunk = f.read(1024)
            if b"\x00" in chunk:
                return "", False, f"此檔案為二進位檔案（{path.suffix or '無副檔名'}），目前尚未提供內容解析"

        for encoding in ("utf-8-sig", "utf-8", "gbk", "cp950", "big5"):
            try:
                with path.open("r", encoding=encoding) as f:
                    lines = []
                    total_bytes = 0
                    truncated = False
                    for i, line in enumerate(f):
                        if i >= MAX_LINES:
                            truncated = True
                            break
                        total_bytes += len(line.encode("utf-8", errors="replace"))
                        if total_bytes > MAX_BYTES:
                            truncated = True
                            break
                        lines.append(line)
                    return "".join(lines), truncated, ""
            except UnicodeDecodeError:
                continue

        return "", False, "無法以文字編碼解讀此檔案（非純文字格式）"
    except OSError as e:
        return "", False, str(e)
