"""
tests/test_archive.py
測試壓縮檔瀏覽器功能（zip、tar、截斷保護、單檔解壓與路由）。
"""
import sys
import tempfile
import zipfile
import tarfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from PySide6.QtWidgets import QApplication

from core.preview_router import get_renderer
from renderers.archive_renderer import ArchiveRenderer, ArchiveBrowserWidget

class TestArchiveRenderer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tdp = Path(self.td.name)

    def tearDown(self):
        self.td.cleanup()

    def test_zip_routing_and_render(self):
        """1. 驗證 ZIP 路由、Widget 讀取與渲染"""
        zip_path = self.tdp / "test_sample.zip"
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("root.txt", "Hello KyteView Root")
            zf.writestr("subfolder/inner.txt", "Inner text content")
            zf.writestr("subfolder/deep/doc.pdf", b"%PDF-1.4 mock")

        renderer = get_renderer(zip_path)
        self.assertIsInstance(renderer, ArchiveRenderer)

        widget = renderer.render(zip_path)
        self.assertIsInstance(widget, ArchiveBrowserWidget)
        self.assertEqual(len(widget._entries), 3)
        self.assertGreater(widget._total_uncompressed, 0)
        self.assertFalse(widget._is_truncated)

        # 驗證單檔抽出功能
        extracted = widget._extract_single_file("subfolder/inner.txt")
        self.assertIsNotNone(extracted)
        self.assertTrue(extracted.exists())
        self.assertEqual(extracted.read_text(encoding="utf-8"), "Inner text content")

    def test_truncation_protection(self):
        """2. 驗證 1,000 筆上限防卡死截斷保護"""
        big_zip_path = self.tdp / "big.zip"
        with zipfile.ZipFile(big_zip_path, "w") as zf:
            for i in range(1200):
                zf.writestr(f"item_{i}.txt", "x")

        big_widget = ArchiveBrowserWidget(big_zip_path)
        self.assertTrue(big_widget._is_truncated)
        self.assertEqual(len(big_widget._entries), 1000)

    def test_tar_gz_reading(self):
        """3. 驗證 tar.gz 讀取"""
        tar_path = self.tdp / "test_sample.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            f1 = self.tdp / "file1.txt"
            f1.write_text("Tar content", encoding="utf-8")
            tf.add(f1, arcname="folder/file1.txt")

        tar_renderer = get_renderer(tar_path)
        self.assertIsInstance(tar_renderer, ArchiveRenderer)
        tar_widget = tar_renderer.render(tar_path)
        self.assertGreaterEqual(len(tar_widget._entries), 1)

def test_archive():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestArchiveRenderer)
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)

if __name__ == "__main__":
    unittest.main()
