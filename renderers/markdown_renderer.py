"""
renderers/markdown_renderer.py
Markdown 極速渲染器：
- markdown-it-py 轉 HTML
- GitHub 現代深色風格 CSS（適應無邊框暗色主題）
- QTextBrowser 唯讀渲染
"""
from __future__ import annotations

from pathlib import Path

from markdown_it import MarkdownIt

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTextBrowser, QVBoxLayout, QWidget

from core.render_cache import cache
from renderers.base import BaseRenderer

from config.settings import settings

_MD_CSS_DARK = """
<style>
body {
    background-color: #121214;
    color: #e6edf3;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
    padding: 16px 24px;
}
h1, h2, h3, h4, h5, h6 {
    color: #ffffff;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 6px;
}
h1 { font-size: 24px; }
h2 { font-size: 20px; }
h3 { font-size: 16px; }
p, ul, ol, blockquote { margin-top: 0; margin-bottom: 14px; }
a { color: #58a6ff; text-decoration: none; }
code {
    background-color: rgba(110, 118, 129, 0.2);
    color: #f0883e;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
}
pre {
    background-color: #1a1a1e;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
}
pre code { background-color: transparent; color: #abb2bf; padding: 0; }
blockquote {
    border-left: 4px solid #3b82f6;
    color: #8b949e;
    padding-left: 14px;
    margin-left: 0;
}
table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
th, td { border: 1px solid rgba(255, 255, 255, 0.12); padding: 6px 12px; }
th { background-color: #1e1e24; color: #ffffff; }
tr:nth-child(even) { background-color: #16161a; }
hr { border: none; border-top: 1px solid rgba(255, 255, 255, 0.1); margin: 20px 0; }
</style>
"""

_MD_CSS_LIGHT = """
<style>
body {
    background-color: #ffffff;
    color: #1f2328;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    margin: 0;
    padding: 16px 24px;
}
h1, h2, h3, h4, h5, h6 {
    color: #1f2328;
    font-weight: 600;
    margin-top: 24px;
    margin-bottom: 12px;
    border-bottom: 1px solid #d1d9e0;
    padding-bottom: 6px;
}
h1 { font-size: 24px; }
h2 { font-size: 20px; }
h3 { font-size: 16px; }
p, ul, ol, blockquote { margin-top: 0; margin-bottom: 14px; }
a { color: #0969da; text-decoration: none; }
code {
    background-color: rgba(175, 184, 193, 0.2);
    color: #cf222e;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: 'Cascadia Code', 'Consolas', monospace;
    font-size: 13px;
}
pre {
    background-color: #f6f8fa;
    border: 1px solid #d0d7de;
    border-radius: 6px;
    padding: 12px 16px;
    overflow-x: auto;
}
pre code { background-color: transparent; color: #1f2328; padding: 0; }
blockquote {
    border-left: 4px solid #0969da;
    color: #59636e;
    padding-left: 14px;
    margin-left: 0;
}
table { border-collapse: collapse; width: 100%; margin-bottom: 16px; }
th, td { border: 1px solid #d0d7de; padding: 6px 12px; }
th { background-color: #f6f8fa; color: #1f2328; }
tr:nth-child(even) { background-color: #f6f8fa; }
hr { border: none; border-top: 1px solid #d1d9e0; margin: 20px 0; }
</style>
"""


class MarkdownRenderer(BaseRenderer):
    def __init__(self) -> None:
        self._md = MarkdownIt("commonmark", {"breaks": True, "html": True})

    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        theme_cache_path = Path(f"{path}::{settings.theme}")
        cached_html = cache.get(theme_cache_path)
        if cached_html is None:
            try:
                for enc in ("utf-8-sig", "utf-8", "cp950", "gbk"):
                    try:
                        raw = path.read_text(encoding=enc)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raw = path.read_text(encoding="utf-8", errors="replace")

                html_content = self._md.render(raw)
                css = _MD_CSS_DARK if settings.is_dark() else _MD_CSS_LIGHT
                cached_html = f"<!DOCTYPE html><html><head>{css}</head><body>{html_content}</body></html>"
                cache.set(theme_cache_path, cached_html)
            except Exception as e:
                err_label = QLabel(f"⚠️ 無法解析 Markdown\n{e}")
                err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                err_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
                layout.addWidget(err_label)
                return container

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(cached_html)
        browser.setFrameShape(QTextBrowser.Shape.NoFrame)
        browser.setStyleSheet("""
            QTextBrowser {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: rgba(255, 255, 255, 0.15);
                border-radius: 4px;
            }
        """)
        layout.addWidget(browser)

        return container
