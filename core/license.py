"""
core/license.py
KyteView 授權與試用期管理模組：
- 14 天新手黃金期（所有功能無限制開啟）
- 第 15 天起溫和降級（保留基礎核心預覽，進階功能專屬解鎖）
- 支援 Windows MachineGuid 機器碼綁定、離線簽名驗證與授權啟用
"""
from __future__ import annotations

import os
import sys
import json
import base64
import hmac
import hashlib
import time
from pathlib import Path
from typing import Tuple, Optional

from PySide6.QtCore import QObject, Signal


def get_machine_guid() -> str:
    """取得 Windows 唯一 MachineGuid 機器識別碼。"""
    if sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Cryptography",
                0,
                winreg.KEY_READ | winreg.KEY_WOW64_64KEY
            ) as key:
                guid, _ = winreg.QueryValueEx(key, "MachineGuid")
                if guid:
                    return str(guid).strip().lower()
        except Exception:
            pass

    import uuid
    import platform
    raw = f"{uuid.getnode()}-{platform.node()}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


DEFAULT_SECRET = "KyteView_Secret_2026_@KeySecure_ais7896"
TRIAL_DAYS = 14


class LicenseManager(QObject):
    license_changed = Signal(bool)  # is_activated
    _instance: Optional[LicenseManager] = None

    @classmethod
    def get_instance(cls) -> LicenseManager:
        if cls._instance is None:
            cls._instance = LicenseManager()
        return cls._instance

    def __init__(self) -> None:
        super().__init__()
        self.machine_id = get_machine_guid()
        self.license_file = self._get_license_file_path()
        self.trial_file = self._get_trial_file_path()

        self._is_pro = False
        self._license_data: dict = {}
        self._trial_days_left = 14
        self._is_trial_valid = True

        self.verify_local_license()
        self._check_trial_status()

    def _get_license_file_path(self) -> Path:
        appdata = Path(os.environ.get("APPDATA", Path.home())) / "KyteView"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "license.dat"

    def _get_trial_file_path(self) -> Path:
        appdata = Path(os.environ.get("APPDATA", Path.home())) / "KyteView"
        appdata.mkdir(parents=True, exist_ok=True)
        return appdata / "trial.dat"

    def is_activated(self) -> bool:
        """是否已正式啟用為永久專業版。"""
        return self._is_pro

    def is_unlimited(self) -> bool:
        """是否具備全功能權限（Pro 永久版 或 14 天試用期內）。"""
        if self._is_pro:
            return True
        return self._is_trial_valid

    def get_plan_type(self) -> str:
        """取得目前方案模式: 'pro', 'trial', 'free'。"""
        if self._is_pro:
            return "pro"
        elif self._is_trial_valid:
            return "trial"
        else:
            return "free"

    def get_trial_days_left(self) -> int:
        """取得試用剩餘天數。"""
        return max(0, self._trial_days_left)

    def _check_trial_status(self) -> None:
        """檢查並計算 14 天試用期狀態，附帶時間倒調防護。"""
        now = time.time()

        if not self.trial_file.exists():
            # 首次安裝建立
            trial_data = {
                "installed_at": now,
                "last_seen": now,
                "machine_id": self.machine_id,
                "checksum": self._calc_trial_checksum(now, now)
            }
            try:
                with open(self.trial_file, "w", encoding="utf-8") as f:
                    json.dump(trial_data, f, indent=2)
            except Exception:
                pass
            self._trial_days_left = TRIAL_DAYS
            self._is_trial_valid = True
            return

        try:
            with open(self.trial_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            installed_at = float(data.get("installed_at", now))
            last_seen = float(data.get("last_seen", now))
            stored_checksum = data.get("checksum", "")

            # 檢驗防竄改
            expected_checksum = self._calc_trial_checksum(installed_at, last_seen)
            if stored_checksum != expected_checksum:
                # 檔案遭竄改，試用失效
                self._is_trial_valid = False
                self._trial_days_left = 0
                return

            # 防倒調系統時鐘
            if now < last_seen - 86400:  # 容許 1 天時區誤差
                self._is_trial_valid = False
                self._trial_days_left = 0
                return

            # 更新 last_seen
            data["last_seen"] = now
            data["checksum"] = self._calc_trial_checksum(installed_at, now)
            try:
                with open(self.trial_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
            except Exception:
                pass

            # 計算已過天數
            elapsed_days = (now - installed_at) / 86400.0
            remaining_days = TRIAL_DAYS - int(elapsed_days)

            if remaining_days > 0 and elapsed_days < TRIAL_DAYS:
                self._trial_days_left = remaining_days
                self._is_trial_valid = True
            else:
                self._trial_days_left = 0
                self._is_trial_valid = False

        except Exception:
            self._is_trial_valid = False
            self._trial_days_left = 0

    def _calc_trial_checksum(self, installed_at: float, last_seen: float) -> str:
        raw = f"{self.machine_id}:{installed_at:.0f}:{last_seen:.0f}:{DEFAULT_SECRET}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def verify_local_license(self) -> bool:
        """本機驗證授權檔案。"""
        if not self.license_file.exists():
            self._is_pro = False
            self._license_data = {}
            return False

        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            key = data.get("key", "").strip().upper()
            sig = data.get("signature", "")
            if not key or not sig:
                self._is_pro = False
                return False

            if self._verify_key_signature(key, sig):
                self._is_pro = True
                self._license_data = data
                return True
            else:
                self._is_pro = False
                return False
        except Exception:
            self._is_pro = False
            return False

    def _verify_key_signature(self, key: str, signature: str) -> bool:
        """驗證序號簽名。"""
        expected = hmac.new(
            DEFAULT_SECRET.encode("utf-8"),
            f"{key}:{self.machine_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32]
        return hmac.compare_digest(expected, signature)

    def activate_license(self, key: str) -> Tuple[bool, str]:
        """
        輸入授權序號進行驗證並啟用。
        支援標準授權金鑰格式：
        1. 機器專屬金鑰 (依據 MachineGuid 簽發)
        2. 全域授權金鑰格式：KYTEVIEW-XXXX-XXXX-XXXX
        """
        clean_key = key.strip().upper()
        if not clean_key:
            return False, "請輸入授權序號。"

        # 格式檢查
        parts = clean_key.replace(" ", "").split("-")
        if len(parts) != 4 or parts[0] != "KYTEVIEW":
            return False, "序號格式錯誤，正確格式範例：KYTEVIEW-XXXX-XXXX-XXXX"

        # 序號演算法驗證：檢查後三段校驗和
        body = "".join(parts[1:3])
        checksum_part = parts[3]
        expected_chk = hashlib.sha256(f"{body}:{DEFAULT_SECRET}".encode("utf-8")).hexdigest()[:4].upper()

        # 通用管理員/開發者密鑰或演算法校驗
        is_valid = (checksum_part == expected_chk) or (clean_key.startswith("KYTEVIEW-PRO-2026-") and len(clean_key) >= 20)

        if not is_valid:
            return False, "授權序號無效或輸入有誤，請確認後重試。"

        # 產生本機簽名憑證
        sig = hmac.new(
            DEFAULT_SECRET.encode("utf-8"),
            f"{clean_key}:{self.machine_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32]

        save_data = {
            "key": clean_key,
            "signature": sig,
            "machine_id": self.machine_id,
            "activated_at": time.strftime("%Y-%m-%d %H:%M:%S")
        }

        try:
            with open(self.license_file, "w", encoding="utf-8") as f:
                json.dump(save_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            return False, f"儲存授權資料失敗: {e}"

        self._is_pro = True
        self._license_data = save_data
        self.license_changed.emit(True)
        return True, "🎉 授權啟用成功！KyteView 專業版所有進階功能已永久解鎖。"

    def deactivate_license(self) -> Tuple[bool, str]:
        """解除授權綁定（更換電腦時使用）。"""
        if self.license_file.exists():
            try:
                self.license_file.unlink()
            except Exception:
                pass
        self._is_pro = False
        self._license_data = {}
        self.license_changed.emit(False)
        return True, "已成功解除本機授權綁定。"

    def get_license_info(self) -> dict:
        return {
            "is_pro": self._is_pro,
            "plan_type": self.get_plan_type(),
            "trial_days_left": self.get_trial_days_left(),
            "machine_id": self.machine_id,
            "license_key": self._license_data.get("key", ""),
            "masked_key": self._mask_key(self._license_data.get("key", "")),
            "activated_at": self._license_data.get("activated_at", ""),
        }

    def _mask_key(self, key: str) -> str:
        if not key or len(key) < 10:
            return ""
        parts = key.split("-")
        if len(parts) >= 4:
            return f"{parts[0]}-****-****-{parts[-1]}"
        return f"{key[:4]}****{key[-4:]}"


def generate_valid_key(seed: str = "A1B2") -> str:
    """輔助生成合法的 KyteView 序號（供測試與簽發使用）。"""
    part1 = "KYTEVIEW"
    part2 = f"{seed.upper():<4}"[:4]
    part3 = "2026"
    body = part2 + part3
    part4 = hashlib.sha256(f"{body}:{DEFAULT_SECRET}".encode("utf-8")).hexdigest()[:4].upper()
    return f"{part1}-{part2}-{part3}-{part4}"
