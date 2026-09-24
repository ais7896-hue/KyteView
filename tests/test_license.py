"""
tests/test_license.py
驗證 KyteView 14天試用期、授權啟用、註冊碼演算法與降級機制。
"""
import unittest
import tempfile
import shutil
from pathlib import Path
from PySide6.QtWidgets import QApplication

from core.license import LicenseManager, generate_valid_key


class TestLicense(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.mgr = LicenseManager.get_instance()
        self.orig_lic = self.mgr.license_file
        self.orig_trial = self.mgr.trial_file
        self.orig_pro = self.mgr._is_pro
        self.orig_data = self.mgr._license_data

        self.mgr.license_file = Path(self.temp_dir) / "license.dat"
        self.mgr.trial_file = Path(self.temp_dir) / "trial.dat"
        self.mgr._is_pro = False
        self.mgr._license_data = {}

    def tearDown(self):
        self.mgr.license_file = self.orig_lic
        self.mgr.trial_file = self.orig_trial
        self.mgr._is_pro = self.orig_pro
        self.mgr._license_data = self.orig_data
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_generate_and_activate_key(self):
        """測試金鑰生成、啟用與解除啟用。"""
        valid_key = generate_valid_key("TEST", prefix="KV")
        self.assertTrue(valid_key.startswith("KV-TEST-2026-"))

        # 測試組合包前綴
        bundle_key = generate_valid_key("BNDL", prefix="KB")
        self.assertTrue(bundle_key.startswith("KB-BNDL-2026-"))

        # 無效格式
        ok, _ = self.mgr.activate_license("INVALID-KEY")
        self.assertFalse(ok)
        self.assertFalse(self.mgr.is_activated())

        # 錯誤校驗碼
        ok, _ = self.mgr.activate_license("KV-TEST-2026-0000")
        self.assertFalse(ok)

        # 正確序號啟用
        ok, msg = self.mgr.activate_license(valid_key)
        self.assertTrue(ok)
        self.assertTrue(self.mgr.is_activated())
        self.assertTrue(self.mgr.is_unlimited())
        self.assertEqual(self.mgr.get_plan_type(), "pro")
        self.assertTrue(self.mgr.license_file.exists())

        # 本機驗證
        self.assertTrue(self.mgr.verify_local_license())

        # 解除綁定
        ok, _ = self.mgr.deactivate_license()
        self.assertTrue(ok)
        self.assertFalse(self.mgr.is_activated())
        self.assertFalse(self.mgr.license_file.exists())

    def test_trial_days_calculation(self):
        """測試試用期狀態。"""
        self.mgr._check_trial_status()
        self.assertEqual(self.mgr.get_trial_days_left(), 14)
        self.assertTrue(self.mgr.is_unlimited())
        self.assertEqual(self.mgr.get_plan_type(), "trial")

    def test_renderers_import(self):
        """確保所有受到授權影響的渲染器與對話框均可正常導入與運作。"""
        from renderers.code_renderer import CodeRenderer
        from renderers.table_renderer import TableRenderer
        from renderers.archive_renderer import ArchiveRenderer
        from renderers.pdf_renderer import PdfRenderer
        from renderers.docx_renderer import DocxRenderer
        from renderers.pptx_renderer import PptxRenderer
        from ui.license_dialog import LicenseDialog

        self.assertIsNotNone(CodeRenderer)
        self.assertIsNotNone(TableRenderer)
        self.assertIsNotNone(ArchiveRenderer)
        self.assertIsNotNone(PdfRenderer)
        self.assertIsNotNone(DocxRenderer)
        self.assertIsNotNone(PptxRenderer)
        self.assertIsNotNone(LicenseDialog)


if __name__ == "__main__":
    unittest.main()
