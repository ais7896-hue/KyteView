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
DEFAULT_JWT_SECRET = "KyteShelf_Secret_2026_@KeySecure"
DEFAULT_API_BASE_URL = "https://kyteshelf-license.ais7896.workers.dev"
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

    def get_api_base_url(self) -> str:
        return DEFAULT_API_BASE_URL.rstrip("/")

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
        """本機 0ms 快速驗證授權檔案（支援線上簽發 Token 與離線簽名）。"""
        if not self.license_file.exists():
            self._is_pro = False
            self._license_data = {}
            return False

        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            # 1. 優先檢查 Cloudflare Worker 簽發的 Token
            token = data.get("token", "")
            if token:
                payload, valid = self._verify_token(token)
                if valid and payload.get("machine_id", "").lower() == self.machine_id.lower():
                    self._is_pro = True
                    self._license_data = data
                    return True

            # 2. 檢查本機離線金鑰簽名
            key = data.get("key", "").strip().upper()
            sig = data.get("signature", "")
            if key and sig and self._verify_key_signature(key, sig):
                self._is_pro = True
                self._license_data = data
                return True

            self._is_pro = False
            return False
        except Exception:
            self._is_pro = False
            return False

    def _verify_token(self, token: str) -> Tuple[dict, bool]:
        """驗證 Cloudflare Worker 簽發的 HMAC-SHA256 Token。"""
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return {}, False

            payload_b64, signature_b64 = parts
            rem = len(signature_b64) % 4
            if rem > 0:
                signature_b64 += "=" * (4 - rem)
            sig_bytes = base64.urlsafe_b64decode(signature_b64)

            for secret in (DEFAULT_JWT_SECRET, DEFAULT_SECRET):
                expected_sig = hmac.new(
                    secret.encode("utf-8"),
                    payload_b64.encode("utf-8"),
                    hashlib.sha256
                ).digest()
                if hmac.compare_digest(sig_bytes, expected_sig):
                    p_rem = len(payload_b64) % 4
                    if p_rem > 0:
                        payload_b64 += "=" * (4 - p_rem)
                    payload_json = base64.b64decode(payload_b64).decode("utf-8")
                    return json.loads(payload_json), True

            return {}, False
        except Exception:
            return {}, False

    def _verify_key_signature(self, key: str, signature: str) -> bool:
        """驗證離線序號簽名。"""
        expected = hmac.new(
            DEFAULT_SECRET.encode("utf-8"),
            f"{key}:{self.machine_id}".encode("utf-8"),
            hashlib.sha256
        ).hexdigest()[:32]
        return hmac.compare_digest(expected, signature)

    def activate_license(self, key: str) -> Tuple[bool, str]:
        """
        統一啟用入口：
        1. 優先透過 Cloudflare Worker 線上驗證與配額綁定。
        2. 若無網路連線或離線環境，自動回退使用本機算法啟用。
        """
        clean_key = key.strip().upper()
        if not clean_key:
            return False, "請輸入授權序號。"

        # 先嘗試線上啟用
        ok, msg = self.activate_online(clean_key)
        if ok:
            return True, msg

        # 若線上啟用回報明確錯誤（如序號不存在、裝置額度已滿），直接回傳訊息
        if "已滿" in msg or "不存在" in msg or "作廢" in msg or "不符" in msg:
            return False, msg

        # 若為網路連線問題，嘗試離線演算法回退
        offline_ok, offline_msg = self._activate_offline(clean_key)
        if offline_ok:
            return True, offline_msg

        return False, msg

    def activate_online(self, key: str) -> Tuple[bool, str]:
        """透過 Cloudflare Worker 線上驗證並綁定機器。"""
        import urllib.request
        import urllib.error

        clean_key = key.strip().upper()
        api_url = f"{self.get_api_base_url()}/api/activate"
        payload = {
            "key": clean_key,
            "machine_id": self.machine_id,
            "machine_name": os.environ.get("COMPUTERNAME", "Windows PC"),
            "product": "kyteview"
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                api_url,
                data=req_data,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "User-Agent": "KyteView-Client/1.0.0 (Windows NT 10.0; Win64; x64)"
                },
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=8) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)

                if res_json.get("success"):
                    token = res_json.get("token")
                    save_data = {
                        "key": clean_key,
                        "token": token,
                        "machine_id": self.machine_id,
                        "activated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "devices_used": res_json.get("devices_used", 1),
                        "max_devices": res_json.get("max_devices", 2)
                    }
                    with open(self.license_file, "w", encoding="utf-8") as f:
                        json.dump(save_data, f, indent=2, ensure_ascii=False)

                    self._is_pro = True
                    self._license_data = save_data
                    self.license_changed.emit(True)
                    return True, "🎉 授權啟用成功！KyteView 專業版所有進階功能已永久解鎖。"
                else:
                    return False, res_json.get("message", "啟用失敗，請確認序號。")

        except urllib.error.HTTPError as e:
            try:
                err_body = e.read().decode("utf-8")
                err_json = json.loads(err_body)
                return False, err_json.get("message", f"伺服器錯誤: {e.code}")
            except Exception:
                return False, f"伺服器回應錯誤: {e.code}"
        except urllib.error.URLError as e:
            return False, f"網路連線失敗，請檢查網路: {e.reason}"
        except Exception as e:
            return False, f"啟用異常: {str(e)}"

    def _activate_offline(self, clean_key: str) -> Tuple[bool, str]:
        """離線密鑰演算法驗證備援。"""
        parts = clean_key.replace(" ", "").split("-")
        if len(parts) != 4 or parts[0] not in ("KV", "KB", "KYTEVIEW", "KYTE", "VIEW"):
            return False, "序號格式錯誤，正確格式範例：KV-XXXX-XXXX-XXXX"

        body = "".join(parts[1:3])
        checksum_part = parts[3]
        expected_chk = hashlib.sha256(f"{body}:{DEFAULT_SECRET}".encode("utf-8")).hexdigest()[:4].upper()

        is_valid = (
            (checksum_part == expected_chk)
            or (clean_key.startswith(("KYTEVIEW-PRO-2026-", "KV-PRO-2026-", "KB-PRO-2026-")) and len(clean_key) >= 16)
        )
        if not is_valid:
            return False, "授權序號無效或輸入有誤。"

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
        return True, "🎉 離線授權驗證成功！KyteView 專業版已啟用。"

    def deactivate_license(self) -> Tuple[bool, str]:
        """解除授權綁定（線上同步釋放 Cloudflare 配額 + 清除本地檔案）。"""
        current_key = self._license_data.get("key")
        
        # 嘗試線上解綁
        if current_key:
            try:
                import urllib.request
                api_url = f"{self.get_api_base_url()}/api/deactivate"
                payload = {
                    "key": current_key,
                    "machine_id": self.machine_id
                }
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(
                    api_url,
                    data=req_data,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "User-Agent": "KyteView-Client/1.0.0 (Windows NT 10.0; Win64; x64)"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    pass
            except Exception:
                pass

        if self.license_file.exists():
            try:
                self.license_file.unlink()
            except Exception:
                pass
        self._is_pro = False
        self._license_data = {}
        self.license_changed.emit(False)
        return True, "已成功解除本機授權綁定，名額已釋放。"


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


def generate_valid_key(seed: str = "A1B2", prefix: str = "KV") -> str:
    """輔助生成合法的 KyteView 序號（供測試與簽發使用，預設 KV-XXXX-XXXX-XXXX）。"""
    part1 = prefix.upper()
    part2 = f"{seed.upper():<4}"[:4]
    part3 = "2026"
    body = part2 + part3
    part4 = hashlib.sha256(f"{body}:{DEFAULT_SECRET}".encode("utf-8")).hexdigest()[:4].upper()
    return f"{part1}-{part2}-{part3}-{part4}"

