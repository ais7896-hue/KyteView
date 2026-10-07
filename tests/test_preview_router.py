import sys
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.preview_router import get_renderer
from renderers.archive_renderer import ArchiveRenderer
from renderers.docx_renderer import DocxRenderer
from renderers.pptx_renderer import PptxRenderer
from renderers.video_renderer import VideoRenderer
from renderers.code_renderer import CodeRenderer
from renderers.table_renderer import TableRenderer
from renderers.image_renderer import ImageRenderer
from renderers.markdown_renderer import MarkdownRenderer
from renderers.pdf_renderer import PdfRenderer
from renderers.audio_renderer import AudioRenderer
from renderers.font_renderer import FontRenderer

class TestPreviewRouter(unittest.TestCase):
    def test_routing_by_extension(self):
        """測試各種副檔名之精確路由分配"""
        test_cases = [
            (Path("doc.zip"), ArchiveRenderer),
            (Path("archive.tar.gz"), ArchiveRenderer),
            (Path("notes.docx"), DocxRenderer),
            (Path("slides.pptx"), PptxRenderer),
            (Path("video.mp4"), VideoRenderer),
            (Path("code.py"), CodeRenderer),
            (Path("config.json"), CodeRenderer),
            (Path("data.csv"), TableRenderer),
            (Path("sheet.xlsx"), TableRenderer),
            (Path("photo.png"), ImageRenderer),
            (Path("readme.md"), MarkdownRenderer),
            (Path("manual.pdf"), PdfRenderer),
            (Path("music.mp3"), AudioRenderer),
            (Path("custom.ttf"), FontRenderer),
            (Path("unknown.xyz"), CodeRenderer), # fallback
        ]

        for path, expected_cls in test_cases:
            renderer = get_renderer(path)
            self.assertIsInstance(
                renderer,
                expected_cls,
                f"Failed for {path}: expected {expected_cls.__name__}, got {type(renderer).__name__}"
            )

if __name__ == "__main__":
    unittest.main()
