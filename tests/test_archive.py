"""
tests/test_archive.py
測試壓縮檔瀏覽器功能（zip、tar、截斷保護、單檔解壓與路由）。
"""
import sys
import tempfile
import zipfile
import tarfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from core.preview_router import get_renderer
from renderers.archive_renderer import ArchiveRenderer, ArchiveBrowserWidget

def test_archive():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        zip_path = tdp / "test_sample.zip"

        # 建立測試 ZIP，包含多層目錄與多個檔案
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("root.txt", "Hello KyteView Root")
            zf.writestr("subfolder/inner.txt", "Inner text content")
            zf.writestr("subfolder/deep/doc.pdf", b"%PDF-1.4 mock")

        # 1. 驗證路由
        renderer = get_renderer(zip_path)
        assert isinstance(renderer, ArchiveRenderer), f"Expected ArchiveRenderer, got {renderer}"

        # 2. 驗證 widget 讀取與渲染
        widget = renderer.render(zip_path)
        assert isinstance(widget, ArchiveBrowserWidget)
        assert len(widget._entries) == 3
        assert widget._total_uncompressed > 0
        assert not widget._is_truncated

        # 3. 驗證單檔抽出功能
        extracted = widget._extract_single_file("subfolder/inner.txt")
        assert extracted is not None
        assert extracted.exists()
        assert extracted.read_text(encoding="utf-8") == "Inner text content"

        # 4. 驗證 1,000 筆上限防卡死截斷保護
        big_zip_path = tdp / "big.zip"
        with zipfile.ZipFile(big_zip_path, "w") as zf:
            for i in range(1200):
                zf.writestr(f"item_{i}.txt", "x")

        big_widget = ArchiveBrowserWidget(big_zip_path)
        assert big_widget._is_truncated is True
        assert len(big_widget._entries) == 1000

        # 5. 驗證 tar.gz 讀取
        tar_path = tdp / "test_sample.tar.gz"
        with tarfile.open(tar_path, "w:gz") as tf:
            f1 = tdp / "file1.txt"
            f1.write_text("Tar content", encoding="utf-8")
            tf.add(f1, arcname="folder/file1.txt")

        tar_renderer = get_renderer(tar_path)
        assert isinstance(tar_renderer, ArchiveRenderer)
        tar_widget = tar_renderer.render(tar_path)
        assert len(tar_widget._entries) >= 1

    print("[SUCCESS] All archive tests passed successfully!")

if __name__ == "__main__":
    test_archive()
