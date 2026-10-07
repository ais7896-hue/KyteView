"""
renderers/docx_renderer.py
Word 文檔高保真向量預覽器：
1. 本機安裝有 Microsoft Word 時：
   - 使用官方 Word COM 引擎 (ExportAsFixedFormat) 輸出高保真向量 PDF。
   - 格式、表格、字型、頁面完全 100% 精準零跑版。
   - 支援 mtime 自動快取：首次 1~2 秒背景生成，後續按下 Space 於 5ms 內秒開。
2. 無安裝 Word 或 COM 例外時：
   - .docx：以超輕量 mammoth 語義化 HTML 渲染於 QTextBrowser。
   - .doc：降級為文檔資訊卡片。
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import tempfile
from typing import Callable, Optional
import winreg

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextBrowser, QFrame, QProgressBar,
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


def _has_word_application() -> bool:
    """檢查註冊表是否具備 Microsoft Word Application。"""
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, r"Word.Application"):
            return True
    except OSError:
        return False


_active_export_threads: set['WordPdfExportThread'] = set()


def wait_all_export_threads(timeout_ms: int = 1500):
    """安全等待並終止所有背景轉譯執行緒，防止處理序退出時崩潰。"""
    threads = list(_active_export_threads)
    for th in threads:
        try:
            if th.isRunning():
                th.quit()
                if not th.wait(timeout_ms):
                    th.terminate()
                    th.wait(500)
        except Exception:
            pass
    _active_export_threads.clear()


class WordPdfExportThread(QThread):
    finished = Signal(Path)
    failed = Signal(str)

    def __init__(self, doc_path: Path, out_pdf: Path):
        super().__init__()
        self.doc_path = doc_path
        self.out_pdf = out_pdf
        _active_export_threads.add(self)
        self.finished.connect(self._cleanup_self)
        self.failed.connect(self._cleanup_self)

    def _cleanup_self(self, *args):
        _active_export_threads.discard(self)

    def run(self):
        try:
            import pythoncom
            import win32com.client
            pythoncom.CoInitialize()
            try:
                word = win32com.client.Dispatch("Word.Application")
                word.Visible = False
                word.DisplayAlerts = False
                doc = word.Documents.Open(
                    str(self.doc_path.resolve()), ReadOnly=True, AddToRecentFiles=False
                )
                # 17 = wdExportFormatPDF
                doc.ExportAsFixedFormat(str(self.out_pdf.resolve()), 17)
                doc.Close(False)
                word.Quit()
                self.finished.emit(self.out_pdf)
            finally:
                pythoncom.CoUninitialize()
        except Exception as e:
            self.failed.emit(str(e))


class AsyncWordWidget(QWidget):
    """Word 高保真渲染容器：支援秒開進度動畫 + 背景轉譯 + 無縫切換。"""

    def __init__(
        self,
        doc_path: Path,
        cached_pdf: Path,
        fallback_factory: Callable[[], QWidget],
        is_dark: bool,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        self.doc_path = doc_path
        self.cached_pdf = cached_pdf
        self.fallback_factory = fallback_factory
        self.is_dark = is_dark
        self._thread: Optional[WordPdfExportThread] = None

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # 頂部平滑載入動畫
        self.loading_box = QWidget()
        l_layout = QVBoxLayout(self.loading_box)
        l_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.setSpacing(14)

        icon_lbl = QLabel("📘")
        icon_lbl.setFont(QFont("Segoe UI Emoji", 40))
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.addWidget(icon_lbl)

        from i18n import t
        txt_lbl = QLabel(t("renderer.docx_rendering"))
        txt_color = "#a1a1aa" if is_dark else "#71717a"
        txt_lbl.setStyleSheet(f"color: {txt_color}; font-size: 13px; font-weight: 500;")
        txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        l_layout.addWidget(txt_lbl)

        bar = QProgressBar()
        bar.setRange(0, 0)
        bar.setFixedWidth(200)
        bar.setFixedHeight(4)
        bar.setTextVisible(False)
        bar_bg = "rgba(255, 255, 255, 0.1)" if is_dark else "rgba(0, 0, 0, 0.08)"
        bar.setStyleSheet(f"""
            QProgressBar {{
                background: {bar_bg};
                border-radius: 2px;
                border: none;
            }}
            QProgressBar::chunk {{
                background: #6366f1;
                border-radius: 2px;
            }}
        """)
        l_layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.loading_box)

        # 啟動非同步轉譯
        self._thread = WordPdfExportThread(doc_path, cached_pdf)
        self._thread.finished.connect(self._on_pdf_ready)
        self._thread.failed.connect(self._on_export_failed)
        self._thread.start()

    def _on_pdf_ready(self, pdf_path: Path):
        self.loading_box.hide()
        from renderers.pdf_renderer import PdfRenderer
        pdf_r = PdfRenderer()
        w = pdf_r.render(pdf_path)
        self.layout.addWidget(w)

    def _on_export_failed(self, err_msg: str):
        self.loading_box.hide()
        fallback_w = self.fallback_factory()
        self.layout.addWidget(fallback_w)

    def cleanup(self):
        if self._thread and self._thread.isRunning():
            try:
                self._thread.disconnect()
                self._thread.quit()
                if not self._thread.wait(1000):
                    self._thread.terminate()
                    self._thread.wait(500)
            except Exception:
                pass


def _read_doc_com(path: Path) -> Optional[str]:
    """舊版 .doc 文字快速擷取後備。"""
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
        "creator": "",
        "modified": "",
        "created": "",
        "words": "",
        "pages": "",
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
    """Word 文件 (.docx / .doc) 原生高保真 + 極速預覽渲染器。"""

    def __init__(self):
        super().__init__()
        self._active_async_widget: Optional[AsyncWordWidget] = None
        self._active_pdf_renderer: Optional[BaseRenderer] = None

    def cleanup(self) -> None:
        """安全釋放預覽控制項與執行緒。"""
        if self._active_async_widget:
            try:
                self._active_async_widget.cleanup()
            except Exception:
                pass
            self._active_async_widget = None

        if self._active_pdf_renderer:
            try:
                self._active_pdf_renderer.cleanup()
            except Exception:
                pass
            self._active_pdf_renderer = None

    def render(self, path: Path) -> QWidget:
        is_dark = settings.is_dark()
        suffix = path.suffix.lower()

        from core.license import LicenseManager
        if not LicenseManager.get_instance().is_unlimited():
            from i18n import t
            return self._create_pro_card(path, t("renderer.docx_pro_hint"))

        # ── 1. 檢查本機向量 PDF 快取 (依路徑與修改時間，命中則 5ms 秒開) ──
        cache_dir = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "KyteView" / "office_pdf_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)
        try:
            mtime = path.stat().st_mtime
        except OSError:
            mtime = 0
        pdf_name = f"{hashlib.md5(f'{path.resolve()}_{mtime}'.encode()).hexdigest()}.pdf"
        cached_pdf = cache_dir / pdf_name

        if cached_pdf.exists():
            from renderers.pdf_renderer import PdfRenderer
            pdf_r = PdfRenderer()
            self._active_pdf_renderer = pdf_r
            return pdf_r.render(cached_pdf)

        # ── 2. 若尚未快取且系統有 Word，啟動官方引擎非同步精準排版 ────────
        if _has_word_application():
            def make_fallback():
                return self._create_software_view(path, suffix, is_dark)

            async_widget = AsyncWordWidget(path, cached_pdf, make_fallback, is_dark)
            self._active_async_widget = async_widget
            return async_widget

        # ── 3. 無微軟 Office 降級處理 ───────────────────────────────────────
        return self._create_software_view(path, suffix, is_dark)

    def _create_software_view(self, path: Path, suffix: str, is_dark: bool) -> QWidget:
        """免安裝 Office 時的跨平台純軟體極速降級渲染。"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── .docx 現代文檔純軟體解析 ──────────────────────────────────────────
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

        # ── .doc 舊版文檔相容處理 ──────────────────────────────────────────
        doc_text = _read_doc_com(path)
        if doc_text and doc_text.strip():
            css = _DOCX_CSS_DARK if is_dark else _DOCX_CSS_LIGHT
            paragraphs = doc_text.replace("\r\n", "\n").split("\n")
            p_html = "".join(f"<p>{p.strip()}</p>" for p in paragraphs if p.strip())
            from i18n import t
            header_notice = (
                '<div style="background: rgba(99, 102, 241, 0.15); border-left: 3px solid #6366f1; '
                f'padding: 8px 12px; margin-bottom: 16px; border-radius: 4px; font-size: 12px; color: #a1a1aa;">'
                f'{t("renderer.doc_legacy_summary")}</div>'
            )
            full_html = f"<!DOCTYPE html><html><head>{css}</head><body>{header_notice}{p_html}</body></html>"
            browser = self._create_browser(full_html, is_dark)
            layout.addWidget(browser)
            return container

        # 若無 COM 或解析失敗，平滑降級為文檔資訊卡片
        from i18n import t
        return self._create_fallback_card(path, t("renderer.doc_legacy_binary"))

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
            from i18n import t
            size_str = t("renderer.unknown_size")

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

        from i18n import t
        add_row(t("renderer.doc_size"), size_str)
        if meta["words"]:
            add_row(t("renderer.total_words"), t("renderer.words_format", words=meta['words']))
        if meta["pages"]:
            add_row(t("renderer.est_pages"), t("renderer.pages_format", pages=meta['pages']))
        if meta["creator"]:
            add_row(t("renderer.author"), meta["creator"])
        if meta["modified"]:
            add_row(t("renderer.last_modified"), meta["modified"])

        layout.addWidget(card)

        # 專業版提示橫條
        tip_lbl = QLabel(f"🔒 {reason}")
        tip_lbl.setStyleSheet(f"color: {c.text_secondary}; font-size: 11px;")
        tip_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(tip_lbl)

        btn_box = QHBoxLayout()
        btn_box.setSpacing(10)
        btn_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        btn_unlock = QPushButton(t("renderer.unlock_docx"))
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

        btn_open = QPushButton(t("renderer.open_default"))
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
            from i18n import t
            size_str = t("renderer.unknown_size")

        from i18n import t
        ext_str = path.suffix.upper().lstrip(".")
        desc_lbl = QLabel(t(
            "renderer.doc_fallback_desc",
            ext=ext_str,
            size=size_str,
            reason=reason,
        ))
        desc_lbl.setStyleSheet("color: #a1a1aa; font-size: 11px; line-height: 1.5;")
        desc_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc_lbl)

        from i18n import t
        btn_open = QPushButton(t("renderer.open_default"))
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
