import sys
import unittest
import tempfile
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.render_cache import RenderCache

class TestRenderCache(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.tdp = Path(self.td.name)
        self.cache = RenderCache(maxsize=3)

    def tearDown(self):
        self.td.cleanup()

    def test_cache_hit_and_miss(self):
        """測試快取命中與未命中"""
        f = self.tdp / "item1.txt"
        f.write_text("hello", encoding="utf-8")

        self.assertIsNone(self.cache.get(f))
        self.cache.set(f, "mock_widget_1")
        self.assertEqual(self.cache.get(f), "mock_widget_1")

    def test_cache_invalidation_on_mtime_change(self):
        """測試檔案修改後 (mtime 改變) 自動快取失效"""
        f = self.tdp / "item2.txt"
        f.write_text("v1", encoding="utf-8")
        self.cache.set(f, "widget_v1")
        self.assertEqual(self.cache.get(f), "widget_v1")

        # 修改檔案與時間
        time.sleep(0.02)
        f.write_text("v2", encoding="utf-8")
        # 由於 mtime 變動，原 key 失效
        self.assertIsNone(self.cache.get(f))

    def test_lru_eviction(self):
        """測試超出 maxsize 時剔除最舊項目"""
        files = []
        for i in range(4):
            fi = self.tdp / f"f{i}.txt"
            fi.write_text(f"content {i}", encoding="utf-8")
            files.append(fi)

        # 寫入 0, 1, 2 (達上限 3)
        self.cache.set(files[0], "val0")
        self.cache.set(files[1], "val1")
        self.cache.set(files[2], "val2")

        # 寫入第 4 個 (files[3])，files[0] 應被剔除
        self.cache.set(files[3], "val3")
        self.assertIsNone(self.cache.get(files[0]))
        self.assertEqual(self.cache.get(files[1]), "val1")
        self.assertEqual(self.cache.get(files[2]), "val2")
        self.assertEqual(self.cache.get(files[3]), "val3")

    def test_manual_invalidate_and_clear(self):
        """測試手動失效與清空快取"""
        f = self.tdp / "item3.txt"
        f.write_text("test", encoding="utf-8")
        self.cache.set(f, "val")
        self.assertEqual(self.cache.get(f), "val")

        self.cache.invalidate(f)
        self.assertIsNone(self.cache.get(f))

        self.cache.set(f, "val2")
        self.cache.clear()
        self.assertIsNone(self.cache.get(f))

if __name__ == "__main__":
    unittest.main()
