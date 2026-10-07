"""
tests/test_pptx.py
測試 PowerPoint 預覽功能（pptx 路由、封面縮圖提取、多頁大綱翻頁、ppt 降級）。
"""
import sys
import tempfile
import zipfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication

from core.preview_router import get_renderer
from renderers.pptx_renderer import PptxRenderer, PptxBrowserWidget, _PptLegacyWidget, _extract_thumbnail

class TestPptxRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tdp = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_pptx_routing_and_thumbnail(self):
        """1. 測試 PPTX 路由與封面縮圖提取"""
        pptx_path = self.tdp / "mock_sample.pptx"

        # 模擬建立包含封面縮圖的 pptx
        with zipfile.ZipFile(pptx_path, "w") as zf:
            fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
            zf.writestr("docProps/thumbnail.jpeg", fake_jpeg)
            zf.writestr("[Content_Types].xml", "<Types></Types>")

        renderer = get_renderer(pptx_path)
        self.assertIsInstance(renderer, PptxRenderer)

        thumb = _extract_thumbnail(pptx_path)
        self.assertIsNotNone(thumb)
        self.assertTrue(thumb.startswith(b"\xff\xd8"))

        widget = renderer.render(pptx_path)
        self.assertIsInstance(widget, PptxBrowserWidget)
        self.assertGreaterEqual(len(widget._slides), 1)

    def test_ppt_legacy_fallback(self):
        """2. 舊版 .ppt 降級測試"""
        ppt_path = self.tdp / "old_doc.ppt"
        ppt_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 mock ppt")
        ppt_renderer = get_renderer(ppt_path)
        self.assertIsInstance(ppt_renderer, PptxRenderer)
        ppt_widget = ppt_renderer.render(ppt_path)
        self.assertIsInstance(ppt_widget, _PptLegacyWidget)

def test_pptx():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPptxRenderer)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

if __name__ == "__main__":
    unittest.main()
