"""
tests/test_pptx.py
測試 PowerPoint 預覽功能（pptx 路由、封面縮圖提取、多頁大綱翻頁、ppt 降級）。
"""
import sys
import tempfile
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication

from core.preview_router import get_renderer
from renderers.pptx_renderer import PptxRenderer, PptxBrowserWidget, _PptLegacyWidget, _extract_thumbnail


def test_pptx():
    app = QApplication.instance() or QApplication([])

    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        pptx_path = tdp / "mock_sample.pptx"

        # 模擬建立包含封面縮圖的 pptx
        with zipfile.ZipFile(pptx_path, "w") as zf:
            # 建立假 JPEG 檔頭
            fake_jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xff\xdb"
            zf.writestr("docProps/thumbnail.jpeg", fake_jpeg)
            zf.writestr("[Content_Types].xml", "<Types></Types>")

        # 1. 路由測試
        renderer = get_renderer(pptx_path)
        assert isinstance(renderer, PptxRenderer)

        # 2. 封面提取測試
        thumb = _extract_thumbnail(pptx_path)
        assert thumb is not None
        assert thumb.startswith(b"\xff\xd8")

        # 3. Widget 載入與結構
        widget = renderer.render(pptx_path)
        assert isinstance(widget, PptxBrowserWidget)
        assert len(widget._slides) >= 1

        # 4. 舊版 .ppt 降級測試
        ppt_path = tdp / "old_doc.ppt"
        ppt_path.write_bytes(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1 mock ppt")
        ppt_renderer = get_renderer(ppt_path)
        assert isinstance(ppt_renderer, PptxRenderer)
        ppt_widget = ppt_renderer.render(ppt_path)
        assert isinstance(ppt_widget, _PptLegacyWidget)

    print("[SUCCESS] All PPTX tests passed successfully!")


if __name__ == "__main__":
    test_pptx()
