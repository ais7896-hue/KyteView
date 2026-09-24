"""
renderers/docx_renderer.py
Word 文檔極速預覽器：
1. .docx：使用超輕量 mammoth 純 Python 庫 (55KB，零外部依賴) 在 20ms 內解析為標準語義化 HTML，
   並以現代專業文稿排版 CSS（深淺色自適應）在 QTextBrowser 中流暢渲染。
2. .doc (Word 97-2003 舊格式)：
   - 若系統安裝有 Word，嘗試以輕量 COM 讀取前幾段純文字預覽。
   - 若無安裝或解析受限，平滑降級為精美文檔資訊卡片 +「↗ 使用預設程式開啟」按鈕，保持介面優雅不崩潰。
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QFrame,
)

from renderers.base import BaseRenderer
from core.render_cache import cache
from config.settings import settings
from config.theme import get_theme_colors


_DOCX_CSS_DARK = """
<style>
body {
    background-color: #121214;
    color: #e4e4e7;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", sans-serif;
    font-size: 14px;
    line-height: 1.7;
    margin: 0;
    padding: 24px 32px;
}
h1, h2, h3, h4, h5, h6 {
    color: #ffffff;
    font-weight: 700;
    margin-top: 24px;
    margin-bottom: 12px;
    line-height: 1.35;
}
h1 {
    font-size: 24px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.12);
    padding-bottom: 8px;
    color: #818cf8;
}
h2 {
    font-size: 19px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    padding-bottom: 6px;
}
h3 { font-size: 16px; }
p {
    margin-top: 0;
    margin-bottom: 12px;
    text-align: justify;
}
strong, b {
    color: #ffffff;
    font-weight: 600;
}
em, i {
    color: #d4d4d8;
}
ul, ol {
    margin-top: 0;
    margin-bottom: 14px;
    padding-left: 24px;
}
li {
    margin-bottom: 6px;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 13px;
    background-color: #18181b;
    border-radius: 6px;
    overflow: hidden;
}
th, td {
    border: 1px solid rgba(255, 255, 255, 0.1);
    padding: 8px 12px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #27272a;
    color: #ffffff;
    font-weight: 600;
}
tr:nth-child(even) {
    background-color: #1f1f23;
}
img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    margin: 10px 0;
    border: 1px solid rgba(255, 255, 255, 0.1);
}
blockquote {
    border-left: 4px solid #6366f1;
    background-color: rgba(99, 102, 241, 0.08);
    color: #a1a1aa;
    padding: 8px 16px;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
}
a {
    color: #818cf8;
    text-decoration: underline;
}
hr {
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    margin: 20px 0;
}
</style>
"""

_DOCX_CSS_LIGHT = """
<style>
body {
    background-color: #ffffff;
    color: #27272a;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft JhengHei UI", "Microsoft JhengHei", "PingFang TC", sans-serif;
    font-size: 14px;
    line-height: 1.7;
    margin: 0;
    padding: 24px 32px;
}
h1, h2, h3, h4, h5, h6 {
    color: #09090b;
    font-weight: 700;
    margin-top: 24px;
    margin-bottom: 12px;
    line-height: 1.35;
}
h1 {
    font-size: 24px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.1);
    padding-bottom: 8px;
    color: #4f46e5;
}
h2 {
    font-size: 19px;
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    padding-bottom: 6px;
}
h3 { font-size: 16px; }
p {
    margin-top: 0;
    margin-bottom: 12px;
    text-align: justify;
}
strong, b {
    color: #09090b;
    font-weight: 600;
}
em, i {
    color: #3f3f46;
}
ul, ol {
    margin-top: 0;
    margin-bottom: 14px;
    padding-left: 24px;
}
li {
    margin-bottom: 6px;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 16px 0;
    font-size: 13px;
    background-color: #ffffff;
    border-radius: 6px;
    overflow: hidden;
}
th, td {
    border: 1px solid rgba(0, 0, 0, 0.1);
    padding: 8px 12px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #f4f4f5;
    color: #18181b;
    font-weight: 600;
}
tr:nth-child(even) {
    background-color: #fafafa;
}
img {
    max-width: 100%;
    height: auto;
    border-radius: 6px;
    margin: 10px 0;
    border: 1px solid rgba(0, 0, 0, 0.08);
}
blockquote {
    border-left: 4px solid #4f46e5;
    background-color: rgba(79, 70, 229, 0.06);
    color: #52525b;
    padding: 8px 16px;
    margin: 12px 0;
    border-radius: 0 4px 4px 0;
}
a {
    color: #4f46e5;
    text-decoration: underline;
}
hr {
    border: none;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    margin: 20px 0;
}
</style>
"""


def _read_doc_com(path: Path) -> Optional[str]:
    """嘗試透過 Windows COM 輕量擷取舊版 .doc 文字。"""
    try:
        import win32com.client
        import pythoncom
        pythoncom.CoInitialize()
        try:
            word = win32com.client.Dispatch("Word.Application")
            word.Visible = False
            word.DisplayAlerts = False
            doc = word.Documents.Open(str(path.resolve()), ReadOnly=True, AddToRecentFiles=False)
            chars_count = doc.Characters.Count
            read_len = min(6000, chars_count)
            text = doc.Range(0, read_len).Text if read_len > 0 else ""
            doc.Close(False)
            word.Quit()
            return text
        finally:
            pythoncom.CoUninitialize()
    except Exception:
        return None


def _extract_docx_meta(path: Path) -> dict:
    meta = {
        "creator": "未知",
        "modified": "未知",
        "created": "未知",
        "words": "未知",
        "pages": "未知",
    }
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        with zipfile.ZipFile(path, "r") as zf:
            nl = zf.namelist()
            if "docProps/core.xml" in nl:
                root = ET.fromstring(zf.read("docProps/core.xml"))
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if tag.endswith("creator") and elem.text:
                        meta["creator"] = elem.text.strip()
                    elif tag.endswith("created") and elem.text:
                        meta["created"] = elem.text.replace("T", " ").replace("Z", "")[:19]
                    elif tag.endswith("modified") and elem.text:
                        meta["modified"] = elem.text.replace("T", " ").replace("Z", "")[:19]
            if "docProps/app.xml" in nl:
                root = ET.fromstring(zf.read("docProps/app.xml"))
                for elem in root.iter():
                    tag = elem.tag.lower()
                    if tag.endswith("words") and elem.text:
                        meta["words"] = elem.text.strip()
                    elif tag.endswith("pages") and elem.text:
                        meta["pages"] = elem.text.strip()
    except Exception:
        pass
    return meta


class DocxRenderer(BaseRenderer):
    """Word 文件 (.docx / .doc) 極速預覽渲染器。"""

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        is_dark = settings.is_dark()
        suffix = path.suffix.lower()

        from core.license import LicenseManager
        if not LicenseManager.get_instance().is_unlimited():
            return self._create_pro_card(path, "Word 高保真排版預覽為專業版專屬功能")

        # ── 1. .docx 現代文檔處理 ──────────────────────────────────────────────
        if suffix == ".docx":
            cache_key = f"docx::{path}::{settings.theme}::{settings.font_size}"
            cached_html = cache.get(Path(cache_key))
            if cached_html:
                full_html = cached_html
            else:
                try:
                    import mammoth
                    with open(path, "rb") as docx_file:
                        result = mammoth.convert_to_html(docx_file)
                        raw_html = result.value
                except Exception as e:
                    return self._create_fallback_card(path, f"DOCX 解析失敗: {e}")

                css = _DOCX_CSS_DARK if is_dark else _DOCX_CSS_LIGHT
                full_html = f"<!DOCTYPE html><html><head>{css}</head><body>{raw_html}</body></html>"
                cache.set(Path(cache_key), full_html)

            browser = self._create_browser(full_html, is_dark)
            layout.addWidget(browser)
            return container

        # ── 2. .doc 舊版文檔相容處理 ──────────────────────────────────────────
        doc_text = _read_doc_com(path)
        if doc_text and doc_text.strip():
            css = _DOCX_CSS_DARK if is_dark else _DOCX_CSS_LIGHT
            paragraphs = doc_text.replace("\r\n", "\n").split("\n")
            p_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
            header_notice = (
                '<div style="background: rgba(99, 102, 241, 0.15); border-left: 3px solid #6366f1; '
                'padding: 8px 12px; margin-bottom: 16px; border-radius: 4px; font-size: 12px; color: #a1a1aa;">'
                'ℹ️ 舊版 Word 97-2003 格式 (.doc) 摘要預覽</div>'
            )
            full_html = f"<!DOCTYPE html><html><head>{css}</head><body>{header_notice}{p_html}</body></html>"
            browser = self._create_browser(full_html, is_dark)
            layout.addWidget(browser)
            return container

        # 若無 COM 或解析失敗，平滑降級為文檔資訊卡片
        return self._create_fallback_card(path, "舊版 Word 97-2003 二進位格式 (.doc)")

    def _create_browser(self, html: str, is_dark: bool) -> QTextBrowser:
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(html)
        browser.setFrameShape(QTextBrowser.Shape.NoFrame)

        bg_color = "#121214" if is_dark else "#ffffff"
        scroll_bg = "rgba(255, 255, 255, 0.2)" if is_dark else "rgba(0, 0, 0, 0.18)"
        scroll_hover = "rgba(255, 255, 255, 0.38)" if is_dark else "rgba(0, 0, 0, 0.35)"

        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_color};
                border: none;
                selection-background-color: {'#3b82f6' if is_dark else '#2563eb'};
                selection-color: #ffffff;
            }}
            QScrollBar:vertical {{
                background: transparent;
                width: 8px;
                margin: 4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {scroll_bg};
                border-radius: 4px;
                min-height: 28px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {scroll_hover};
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
                background: {scroll_bg};
                border-radius: 4px;
                min-width: 28px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {scroll_hover};
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
        return browser

    def _create_pro_card(self, path: Path, reason: str) -> QWidget:
        """免費版降級模式：顯示精美商務文件屬性卡片（字數、作者、時間）與解鎖引導。"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(14)

        is_dark = settings.is_dark()
        c = get_theme_colors()

        icon_lbl = QLabel("📘")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 42))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(path.name)
        title_lbl.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color: {c.text};")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        meta = _extract_docx_meta(path)
        try:
            size_kb = path.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        except Exception:
            size_str = "未知大小"

        card = QFrame()
        card.setFixedWidth(380)
        card_bg = "rgba(255, 255, 255, 0.04)" if is_dark else "rgba(0, 0, 0, 0.03)"
        card_border = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        card.setStyleSheet(f"""
            QFrame {{
                background: {card_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                padding: 12px 16px;
            }}
        """)
        c_layout = QVBoxLayout(card)
        c_layout.setSpacing(8)

        def add_row(k: str, v: str):
            row = QHBoxLayout()
            lbl_k = QLabel(k)
            lbl_k.setStyleSheet(f"color: {c.text_secondary}; font-size: 11px;")
            lbl_v = QLabel(v)
            lbl_v.setStyleSheet(f"color: {c.text}; font-size: 11px; font-weight: 500;")
            lbl_v.setAlignment(Qt.AlignmentFlag.AlignRight)
            row.addWidget(lbl_k)
            row.addWidget(lbl_v)
            c_layout.addLayout(row)

        add_row("文件大小", size_str)
        if meta["words"] != "未知":
            add_row("總字數", f"{meta['words']} 字")
        if meta["pages"] != "未知":
            add_row("預估頁數", f"{meta['pages']} 頁")
        if meta["creator"] != "未知":
            add_row("建立者", meta["creator"])
        if meta["modified"] != "未知":
            add_row("最後修改", meta["modified"])

        layout.addWidget(card)

        # 專業版提示橫條
        tip_lbl = QLabel(f"🔒 {reason}，免費版提供基礎屬性卡片檢視")
        tip_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 11px;")
        tip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_lbl)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_unlock = QPushButton("★ 解鎖完整圖文排版")
        btn_unlock.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_unlock.setFixedHeight(32)
        btn_unlock.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #4f46e5, stop:1 #6366f1);
                color: #ffffff;
                font-weight: 600;
                font-size: 11px;
                border-radius: 6px;
                padding: 4px 16px;
                border: none;
            }
            QPushButton:hover {
                background: #4338ca;
            }
        """)
        from ui.license_dialog import show_license_dialog
        btn_unlock.clicked.connect(lambda: show_license_dialog(container.window()))
        btn_box.addWidget(btn_unlock)

        btn_open = QPushButton("↗ 系統預設程式開啟")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(32)
        btn_open_bg = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        btn_open.setStyleSheet(f"""
            QPushButton {{
                background: {btn_open_bg};
                color: {c.text};
                font-size: 11px;
                border-radius: 6px;
                padding: 4px 14px;
                border: 1px solid {card_border};
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.14);
            }}
        """)
        btn_open.clicked.connect(lambda: os.startfile(str(path)))
        btn_box.addWidget(btn_open)

        layout.addLayout(btn_box)
        return container

    def _create_fallback_card(self, path: Path, reason: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(16)

        icon_lbl = QLabel("📄")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 44))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_lbl)

        title_lbl = QLabel(path.name)
        title_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        title_lbl.setStyleSheet("color: #f3f4f6;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        try:
            size_kb = path.stat().st_size / 1024
            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
        except Exception:
            size_str = "未知大小"

        ext_str = path.suffix.upper().lstrip(".")
        desc_lbl = QLabel(
            f"類型：Microsoft Word {ext_str} 文件  ·  大小：{size_str}\n"
            f"說明：{reason}\n"
            "建議轉換為現代 .docx 格式以獲得即時圖文排版預覽。"
        )
        desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px; line-height: 1.5;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)

        btn_open = QPushButton("↗ 使用系統預設程式開啟")
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_open.setFixedHeight(34)
        btn_open.setStyleSheet("""
            QPushButton {
                background: #2563eb;
                color: #ffffff;
                font-weight: bold;
                border-radius: 6px;
                padding: 6px 18px;
            }
            QPushButton:hover {
                background: #1d4ed8;
            }
        """)
        btn_open.clicked.connect(lambda: os.startfile(str(path)))
        layout.addWidget(btn_open)

        return container

