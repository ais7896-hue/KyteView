"""
renderers/code_renderer.py
程式碼語法高亮渲染器：
- Pygments HtmlFormatter + QTextBrowser
- 深色現代風格（OneDark / Monokai 色調）
- 支援行號、一鍵複製、等寬字型（Cascadia Code / Consolas）
- 超過上限自動截斷並提示
- 結合 LRU 快取加速重複預覽
"""
from __future__ import annotations

from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.util import ClassNotFound

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from core.render_cache import cache
from renderers.base import BaseRenderer

from config.settings import settings
from config.theme import get_theme_colors

MAX_CODE_LINES = 1000
MAX_CODE_BYTES = 512 * 1024  # 512 KB


def _get_lexer_for_path(path: Path, code: str):
    """智慧為常見設定/依賴檔提供專屬語法高亮 Lexer。"""
    name_lower = path.name.lower()
    suffix = path.suffix.lower()

    if name_lower == "requirements.txt" or suffix in (".env", ".ini", ".cfg", ".conf", ".properties"):
        try:
            from pygments.lexers.configs import IniLexer
            return IniLexer()
        except Exception:
            pass

    if name_lower == "makefile":
        try:
            from pygments.lexers.make import MakefileLexer
            return MakefileLexer()
        except Exception:
            pass

    if name_lower == "dockerfile":
        try:
            from pygments.lexers.templates import DockerLexer
            return DockerLexer()
        except Exception:
            pass

    try:
        return get_lexer_for_filename(path.name, code)
    except ClassNotFound:
        try:
            from pygments.lexers import guess_lexer
            return guess_lexer(code[:2048])
        except Exception:
            return TextLexer()


def _build_html(code: str, path: Path) -> str:
    """利用 Pygments 依當前主題產生 HTML 字串。"""
    lexer = _get_lexer_for_path(path, code)

    is_dark = settings.is_dark()
    c = get_theme_colors()

    bg_color = c["code_bg"]
    text_color = "#abb2bf" if is_dark else "#24292f"
    line_color = "#4b5263" if is_dark else "#8c959f"
    border_color = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
    pygments_style = c["code_style"]

    # 動態讀取當前 Pygments Style 的原生背景色，保持整頁底色 100% 渾然一體
    try:
        from pygments.styles import get_style_by_name
        st_obj = get_style_by_name(pygments_style)
        style_bg = getattr(st_obj, "background_color", None)
        if style_bg and style_bg.startswith("#"):
            bg_color = style_bg
    except Exception:
        pass

    font_size = settings.font_size
    font_code = settings.font_family_code or "Cascadia Code"
    white_space_rule = "white-space: pre-wrap; word-break: break-all;" if settings.word_wrap else "white-space: pre;"
    ligatures_rule = 'font-feature-settings: "liga" 1, "calt" 1;' if settings.enable_ligatures else 'font-feature-settings: normal;'
    line_number_color = "#63636e" if is_dark else "#9ca3af"

    css_template = f"""
    <style>
    html, body {{
        background-color: {bg_color};
        color: {text_color};
        font-family: '{font_code}', 'Cascadia Code', 'Fira Code', 'Consolas', 'Courier New', monospace;
        font-size: {font_size}px;
        line-height: 1.6;
        margin: 0;
        padding: 12px 16px;
        min-height: 100%;
        {ligatures_rule}
    }}
    .highlight, table.highlighttable {{
        background-color: {bg_color} !important;
        border-collapse: collapse;
        width: 100%;
    }}
    td.linenos {{
        color: {line_number_color};
        text-align: right;
        padding-right: 14px;
        user-select: none;
        vertical-align: top;
        border-right: 1px solid rgba(128, 128, 128, 0.15);
        font-size: {max(10, font_size - 1)}px;
        opacity: 0.75;
    }}
    td.code {{
        padding-left: 16px;
        vertical-align: top;
        background-color: {bg_color} !important;
        {white_space_rule}
        {ligatures_rule}
    }}
    td.code pre {{
        margin: 0;
        background-color: {bg_color} !important;
        font-family: inherit;
        {ligatures_rule}
    }}
    /*PYGMENTS_CSS*/
    </style>
    """

    try:
        formatter = HtmlFormatter(
            nowrap=False,
            linenos="table",
            style=pygments_style,
            linespans="line",
        )
    except Exception:
        fallback_style = "monokai" if is_dark else "friendly"
        formatter = HtmlFormatter(
            nowrap=False,
            linenos="table",
            style=fallback_style,
            linespans="line",
        )
    pygments_css = formatter.get_style_defs(".highlight")
    full_css = css_template.replace("/*PYGMENTS_CSS*/", pygments_css)
    highlighted = highlight(code, lexer, formatter)

    return f"<!DOCTYPE html><html><head>{full_css}</head><body>{highlighted}</body></html>"


class CodeRenderer(BaseRenderer):
    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 嘗試從快取讀取已產生的 (html, is_truncated, err)
        cache_key = f"{path}::{settings.theme}::{settings.code_theme}::{settings.font_size}::{settings.word_wrap}"
        theme_cache_path = Path(cache_key)
        cached = cache.get(theme_cache_path)
        if cached:
            html, truncated, error = cached
        else:
            text, truncated, error = self._read_source(path)
            if not error:
                html = _build_html(text, path)
            else:
                html = ""
            cache.set(theme_cache_path, (html, truncated, error))

        if error:
            err_label = QLabel(f"⚠️ 無法讀取程式碼檔案\n{error}")
            err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(err_label)
            return container

        browser = QTextBrowser()
        browser.setOpenExternalLinks(False)
        browser.setHtml(html)
        browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        try:
            from pygments.styles import get_style_by_name
            st_obj = get_style_by_name(settings.code_theme)
            code_bg = getattr(st_obj, "background_color", None) or ("#18181b" if settings.is_dark() else "#ffffff")
        except Exception:
            code_bg = "#18181b" if settings.is_dark() else "#ffffff"

        scroll_handle_bg = "rgba(255, 255, 255, 0.2)" if settings.is_dark() else "rgba(0, 0, 0, 0.18)"
        scroll_handle_hover = "rgba(255, 255, 255, 0.38)" if settings.is_dark() else "rgba(0, 0, 0, 0.35)"

        browser.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {code_bg};
                border: none;
                selection-background-color: #264f78;
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
        layout.addWidget(browser)

        if truncated:
            bar = QLabel(
                f"⚠️ 僅預覽前 {MAX_CODE_LINES} 行  ·  檔案大小：{path.stat().st_size:,} bytes"
            )
            bar.setStyleSheet("""
                background: #1e1e24;
                color: #858585;
                font-size: 11px;
                padding: 4px 12px;
                border-top: 1px solid rgba(255, 255, 255, 0.05);
            """)
            layout.addWidget(bar)

        return container

    def _read_source(self, path: Path) -> tuple[str, bool, str]:
        try:
            for encoding in ("utf-8-sig", "utf-8", "gbk", "cp950", "big5", "latin-1"):
                try:
                    with path.open("r", encoding=encoding) as f:
                        lines = []
                        total_bytes = 0
                        truncated = False
                        for i, line in enumerate(f):
                            if i >= MAX_CODE_LINES:
                                truncated = True
                                break
                            total_bytes += len(line.encode("utf-8", errors="replace"))
                            if total_bytes > MAX_CODE_BYTES:
                                truncated = True
                                break
                            lines.append(line)
                        return "".join(lines), truncated, ""
                except UnicodeDecodeError:
                    continue
            return "", False, "無法解讀編碼"
        except OSError as e:
            return "", False, str(e)
