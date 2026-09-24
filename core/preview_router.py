"""
core/preview_router.py
根據副檔名將路徑路由到對應的 Renderer。
Phase 1 只有 text_renderer（fallback），後續 Phase 逐步擴充。
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from renderers.base import BaseRenderer

# ── 副檔名對應表（後續 Phase 逐步填入）─────────────────────────────────────
_CODE_EXTS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".php", ".rb", ".swift",
    ".kt", ".kts", ".json", ".yaml", ".yml", ".toml", ".xml",
    ".html", ".htm", ".css", ".scss", ".sass", ".sql", ".sh",
    ".bash", ".zsh", ".ps1", ".bat", ".cmd", ".lua", ".r",
    ".dart", ".ex", ".exs", ".hs", ".ml", ".clj", ".vim",
}

_DOCX_EXTS = {".docx", ".doc"}

_PPTX_EXTS = {".pptx", ".ppt"}

_TABLE_EXTS = {".csv", ".tsv", ".xlsx", ".xls"}

_IMAGE_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg", ".tiff",
}

_AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"}

_VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".wmv", ".flv", ".ts"}

_FONT_EXTS = {".ttf", ".otf", ".woff", ".woff2"}

_PDF_EXTS = {".pdf"}

_MARKDOWN_EXTS = {".md", ".mdx", ".rst"}

_ARCHIVE_EXTS = {".zip", ".7z", ".rar", ".tar", ".gz", ".tar.gz", ".tar.bz2", ".tar.xz", ".tgz"}

_TEXT_EXTS = {".txt", ".log", ".env", ".cfg", ".ini", ".conf", ".properties"}


def get_renderer(path: Path) -> "BaseRenderer":
    """
    根據副檔名回傳對應 Renderer 實例。
    """
    suffix = path.suffix.lower()
    suffixes = "".join(path.suffixes).lower()

    if suffix in _ARCHIVE_EXTS or any(suffixes.endswith(x) for x in (".tar.gz", ".tar.bz2", ".tar.xz")):
        from renderers.archive_renderer import ArchiveRenderer
        return ArchiveRenderer()

    if suffix in _DOCX_EXTS:
        from renderers.docx_renderer import DocxRenderer
        return DocxRenderer()

    if suffix in _PPTX_EXTS:
        from renderers.pptx_renderer import PptxRenderer
        return PptxRenderer()

    if suffix in _VIDEO_EXTS:
        from renderers.video_renderer import VideoRenderer
        return VideoRenderer()

    if suffix in _CODE_EXTS:
        from renderers.code_renderer import CodeRenderer
        return CodeRenderer()

    if suffix in _TABLE_EXTS:
        from renderers.table_renderer import TableRenderer
        return TableRenderer()

    if suffix in _IMAGE_EXTS:
        from renderers.image_renderer import ImageRenderer
        return ImageRenderer()

    if suffix in _MARKDOWN_EXTS:
        from renderers.markdown_renderer import MarkdownRenderer
        return MarkdownRenderer()

    if suffix in _PDF_EXTS:
        from renderers.pdf_renderer import PdfRenderer
        return PdfRenderer()

    if suffix in _AUDIO_EXTS:
        from renderers.audio_renderer import AudioRenderer
        return AudioRenderer()

    if suffix in _FONT_EXTS:
        from renderers.font_renderer import FontRenderer
        return FontRenderer()

    # 包含 .txt, .log, .env, .ini, .cfg, requirements.txt 等所有純文字/設定檔
    from renderers.code_renderer import CodeRenderer
    return CodeRenderer()
