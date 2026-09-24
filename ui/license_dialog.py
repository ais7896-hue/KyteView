"""
ui/license_dialog.py
KyteView 授權啟用與方案狀態視窗：
- 現代深淺主題適配
- 顯示目前方案狀態 (Pro / Trial / Free)
- 輸入序號即時啟用與解除綁定
- 複製機器碼與線上購買指引
"""
from __future__ import annotations

import webbrowser
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QFrame, QMessageBox, QApplication, QWidget,
)

from core.license import LicenseManager
from config.settings import settings
from config.theme import get_theme_colors


class LicenseDialog(QDialog):
    """授權啟用與狀態管理對話框。"""
    PURCHASE_URL = "https://github.com/ais7896-hue/KyteView"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.license_mgr = LicenseManager.get_instance()
        self.setWindowTitle("KyteView 軟體授權與專業版啟用")
        self.setFixedSize(500, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.license_mgr.license_changed.connect(self.refresh_ui_state)
        self._build_ui()
        self.refresh_ui_state()

    def _build_ui(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()
        bg_color = "#18181b" if is_dark else "#f8fafc"
        text_color = "#f4f4f5" if is_dark else "#0f172a"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_color};
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }}
            QLabel {{
                color: {text_color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 頂部標題區
        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)

        icon_label = QLabel("🪁")
        icon_label.setStyleSheet("font-size: 32px;")
        header_layout.addWidget(icon_label)

        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        title_label = QLabel("KyteView 專業版授權")
        title_label.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {c['title_color']};")
        subtitle_label = QLabel("一次買斷 · 永久使用 · 支持個人電腦獨立啟動")
        subtitle_label.setStyleSheet(f"font-size: 12px; color: {c['subtitle_color']};")
        header_text.addWidget(title_label)
        header_text.addWidget(subtitle_label)
        header_layout.addLayout(header_text)
        header_layout.addStretch()

        layout.addLayout(header_layout)

        # 狀態卡片 (動態更新)
        self.status_card = QFrame()
        self.status_card.setObjectName("StatusCard")
        self.status_layout = QVBoxLayout(self.status_card)
        self.status_layout.setContentsMargins(18, 14, 18, 14)
        self.status_layout.setSpacing(8)

        self.status_badge = QLabel()
        self.status_badge.setStyleSheet("font-size: 14px; font-weight: 700;")
        self.status_layout.addWidget(self.status_badge)

        self.status_desc = QLabel()
        self.status_desc.setWordWrap(True)
        self.status_desc.setStyleSheet(f"font-size: 12px; color: {c['subtitle_color']}; line-height: 1.5;")
        self.status_layout.addWidget(self.status_desc)

        layout.addWidget(self.status_card)

        # 輸入序號卡片
        self.input_card = QFrame()
        self.input_card.setObjectName("InputCard")
        input_layout = QVBoxLayout(self.input_card)
        input_layout.setContentsMargins(16, 14, 16, 14)
        input_layout.setSpacing(10)

        key_label = QLabel("輸入授權序號：")
        key_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['title_color']};")
        input_layout.addWidget(key_label)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("例：KYTEVIEW-XXXX-XXXX-XXXX")
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_input.setFixedHeight(38)
        self.key_input.returnPressed.connect(self._on_activate_clicked)
        input_layout.addWidget(self.key_input)

        self.btn_activate = QPushButton("立即驗證並啟用")
        self.btn_activate.setFixedHeight(36)
        self.btn_activate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_activate.clicked.connect(self._on_activate_clicked)
        input_layout.addWidget(self.btn_activate)

        layout.addWidget(self.input_card)

        # 底部資訊與機器碼
        bottom_box = QVBoxLayout()
        bottom_box.setSpacing(8)

        # 機器碼列
        mid_row = QHBoxLayout()
        mid_label = QLabel(f"本機識別碼: <code style='color: #6366f1;'>{self.license_mgr.machine_id[:16]}...</code>")
        mid_label.setStyleSheet(f"font-size: 11px; color: {c['subtitle_color']};")
        mid_row.addWidget(mid_label)
        mid_row.addStretch()

        btn_copy_mid = QPushButton("複製機器碼")
        btn_copy_mid.setFixedHeight(22)
        btn_copy_mid.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_copy_mid.clicked.connect(self._copy_machine_id)
        mid_row.addWidget(btn_copy_mid)
        bottom_box.addLayout(mid_row)

        # 購買與支援列
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_buy = QPushButton("🛒 前往購買正式授權")
        self.btn_buy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buy.setFixedHeight(34)
        self.btn_buy.clicked.connect(self._open_buy_url)
        action_row.addWidget(self.btn_buy, 1)

        self.btn_deactivate = QPushButton("解除授權綁定")
        self.btn_deactivate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deactivate.setFixedHeight(34)
        self.btn_deactivate.setVisible(False)
        self.btn_deactivate.clicked.connect(self._on_deactivate_clicked)
        action_row.addWidget(self.btn_deactivate, 1)

        bottom_box.addLayout(action_row)
        layout.addLayout(bottom_box)

        self._apply_dialog_styles()

    def _apply_dialog_styles(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()
        card_bg = "rgba(255, 255, 255, 0.05)" if is_dark else "#ffffff"
        card_border = "rgba(255, 255, 255, 0.10)" if is_dark else "#e2e8f0"
        input_bg = "rgba(0, 0, 0, 0.2)" if is_dark else "#f1f5f9"

        self.status_card.setStyleSheet(f"""
            QFrame#StatusCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
        """)

        self.input_card.setStyleSheet(f"""
            QFrame#InputCard {{
                background-color: {card_bg};
                border: 1px solid {card_border};
                border-radius: 12px;
            }}
            QLineEdit {{
                background-color: {input_bg};
                border: 1px solid {card_border};
                border-radius: 8px;
                color: {c['title_color']};
                font-family: 'JetBrains Mono', 'Consolas', monospace;
                font-size: 14px;
                font-weight: 600;
                letter-spacing: 1px;
            }}
            QLineEdit:focus {{
                border: 1px solid #6366f1;
            }}
            QPushButton {{
                background-color: #4f46e5;
                color: #ffffff;
                border-radius: 8px;
                font-size: 13px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #6366f1;
            }}
        """)

        btn_sec_style = f"""
            QPushButton {{
                background-color: {'rgba(255, 255, 255, 0.08)' if is_dark else '#e2e8f0'};
                color: {c['title_color']};
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 0 10px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {'rgba(255, 255, 255, 0.15)' if is_dark else '#cbd5e1'};
            }}
        """
        self.btn_buy.setStyleSheet(btn_sec_style)
        self.btn_deactivate.setStyleSheet(f"""
            QPushButton {{
                background-color: {'rgba(239, 68, 68, 0.15)' if is_dark else '#fee2e2'};
                color: #ef4444;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 600;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {'rgba(239, 68, 68, 0.25)' if is_dark else '#fecaca'};
            }}
        """)

    def refresh_ui_state(self) -> None:
        info = self.license_mgr.get_license_info()
        plan = info["plan_type"]

        if plan == "pro":
            self.status_badge.setText("★ 已啟用永久專業版 (Pro)")
            self.status_badge.setStyleSheet("color: #10b981; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(
                f"感謝您的支持！所有進階功能（程式碼高亮、完整表格、壓縮檔單檔抽出、PPTX大綱、Mica毛玻璃）已全面永久解鎖。\n"
                f"啟用序號: {info['masked_key']}\n"
                f"啟用時間: {info['activated_at']}"
            )
            self.input_card.setVisible(False)
            self.btn_deactivate.setVisible(True)
            self.btn_buy.setVisible(False)
        elif plan == "trial":
            days = info["trial_days_left"]
            self.status_badge.setText(f"✨ 14 天免費全功能試用中 (剩餘 {days} 天)")
            self.status_badge.setStyleSheet("color: #6366f1; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(
                "試用期間享有所有專業版完整功能無任何限制！\n"
                "試用期結束後將溫和降級為基礎免費版（核心預覽永遠可用，進階功能設為專業版專屬）。"
            )
            self.input_card.setVisible(True)
            self.btn_deactivate.setVisible(False)
            self.btn_buy.setVisible(True)
        else:
            self.status_badge.setText("🔒 免費版 (溫和降級模式)")
            self.status_badge.setStyleSheet("color: #f59e0b; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(
                "您的 14 天試用期已結束，核心 Space 預覽操作與基礎檢視仍可永久免費使用。\n"
                "進階功能（程式碼高亮、完整表格、單檔直接拖曳抽出、商務文件、Mica/側邊釘選）為專業版專屬，歡迎輸入序號一鍵永久解鎖！"
            )
            self.input_card.setVisible(True)
            self.btn_deactivate.setVisible(False)
            self.btn_buy.setVisible(True)

    def _on_activate_clicked(self) -> None:
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "提示", "請先輸入授權序號。")
            return

        success, msg = self.license_mgr.activate_license(key)
        if success:
            QMessageBox.information(self, "啟用成功", msg)
            self.key_input.clear()
            self.refresh_ui_state()
        else:
            QMessageBox.critical(self, "啟用失敗", msg)

    def _on_deactivate_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            "解除授權確認",
            "確定要解除本機的授權綁定嗎？解除後本機將恢復為免費版模式，序號可在其他電腦重新啟用。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.license_mgr.deactivate_license()
            QMessageBox.information(self, "解除授權", msg)
            self.refresh_ui_state()

    def _copy_machine_id(self) -> None:
        QApplication.clipboard().setText(self.license_mgr.machine_id)
        QMessageBox.information(self, "已複製", "本機識別碼已複製到剪貼簿。")

    def _open_buy_url(self) -> None:
        webbrowser.open(self.PURCHASE_URL)
