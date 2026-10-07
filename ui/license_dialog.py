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
from i18n import t, i18n


class LicenseDialog(QDialog):
    """授權啟用與狀態管理對話框。"""
    PURCHASE_URL = "https://kyteview.aisming.com/#pricing"

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.license_mgr = LicenseManager.get_instance()
        self.setWindowTitle(t("license.title"))
        self.setFixedSize(500, 545)
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowTitleHint
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowSystemMenuHint
        )

        self.license_mgr.license_changed.connect(self.refresh_ui_state)
        i18n.language_changed.connect(self._retranslate_ui)
        self._build_ui()
        self.refresh_ui_state()

    def reject(self) -> None:
        """覆寫 QDialog.reject()，確保在非模態或模態下點擊關閉按鈕/按 ESC 能順利關閉視窗。"""
        super().reject()
        self.close()

    def closeEvent(self, event) -> None:
        event.accept()
        super().closeEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return
        super().keyPressEvent(event)

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
        self.title_label = QLabel(t("license.dialog_header_title"))
        self.title_label.setStyleSheet(f"font-size: 18px; font-weight: 800; color: {c['title_color']};")
        self.subtitle_label = QLabel(t("license.dialog_header_subtitle"))
        self.subtitle_label.setStyleSheet(f"font-size: 12px; color: {c['subtitle_color']};")
        header_text.addWidget(self.title_label)
        header_text.addWidget(self.subtitle_label)
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

        self.key_label = QLabel(t("license.key_label"))
        self.key_label.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {c['title_color']};")
        input_layout.addWidget(self.key_label)

        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText(t("license.key_placeholder"))
        self.key_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.key_input.setFixedHeight(38)
        self.key_input.returnPressed.connect(self._on_activate_clicked)
        input_layout.addWidget(self.key_input)

        self.btn_activate = QPushButton(t("license.btn_activate"))
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
        self.mid_label = QLabel(f"{t('license.mid_label')}: <code style='color: #6366f1;'>{self.license_mgr.machine_id[:16]}...</code>")
        self.mid_label.setStyleSheet(f"font-size: 11px; color: {c['subtitle_color']};")
        mid_row.addWidget(self.mid_label)
        mid_row.addStretch()

        self.btn_copy_mid = QPushButton(t("license.btn_copy_mid"))
        self.btn_copy_mid.setFixedHeight(22)
        self.btn_copy_mid.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_copy_mid.clicked.connect(self._copy_machine_id)
        mid_row.addWidget(self.btn_copy_mid)
        bottom_box.addLayout(mid_row)

        # 購買與支援列
        action_row = QHBoxLayout()
        action_row.setSpacing(10)

        self.btn_buy = QPushButton(t("license.btn_buy"))
        self.btn_buy.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_buy.setFixedHeight(34)
        self.btn_buy.clicked.connect(self._open_buy_url)
        action_row.addWidget(self.btn_buy, 1)

        self.btn_deactivate = QPushButton(t("license.btn_deactivate"))
        self.btn_deactivate.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_deactivate.setFixedHeight(34)
        self.btn_deactivate.setVisible(False)
        self.btn_deactivate.clicked.connect(self._on_deactivate_clicked)
        action_row.addWidget(self.btn_deactivate, 1)

        bottom_box.addLayout(action_row)

        # 客服與技術支援列（預填 mailto 範本）
        mailto_url = (
            "mailto:support@aisming.com?subject=%5B%E5%95%8F%E9%A1%8C%E5%9B%9E%E5%A0%B1%5D%20KyteView%20%E4%BD%BF%E7%94%A8%E8%AB%AE%E8%A9%A2%20-%20%E8%A8%82%E5%96%AE/%E5%BA%8F%E8%99%9F%EF%BC%9A(%E8%8B%A5%E6%9C%89%E8%AB%8B%E5%A1%AB%E5%AF%AB)"
            "&body=1.%20%E4%BD%9C%E6%A5%AD%E7%B3%BB%E7%B5%B1%E7%89%88%E6%9C%AC%20(%E4%BE%8B%E5%A6%82%20Win11%2023H2)%EF%BC%9A%0A"
            "2.%20%E7%99%BC%E7%94%9F%E7%9A%84%E5%95%8F%E9%A1%8C%E6%8F%8F%E8%BF%B0%EF%BC%9A%0A"
            "3.%20%E9%A0%90%E8%A6%BD%E5%93%AA%E7%A8%AE%E9%A1%9E%E5%9E%8B%E7%9A%84%E6%AA%94%E6%A1%88%E6%99%82%E7%99%BC%E7%94%9F%20(%E4%BE%8B%E5%A6%82%20.xlsx%20/%20.mp4)%EF%BC%9A%0A"
            "4.%20%E6%88%AA%E5%9C%96%E6%88%96%E9%8C%AF%E8%AA%A4%E8%A8%8A%E6%81%AF%EF%BC%9A%0A"
        )
        self.support_lbl = QLabel(
            f"{t('license.support_contact')}：<a href='{mailto_url}' style='color: #818cf8; text-decoration: underline;'>support@aisming.com</a>"
        )
        self.support_lbl.setOpenExternalLinks(True)
        self.support_lbl.setStyleSheet(f"font-size: 11px; color: {c['subtitle_color']}; padding-top: 4px;")
        self.support_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_box.addWidget(self.support_lbl)

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
            self.status_badge.setText(t("license.status_pro_badge"))
            self.status_badge.setStyleSheet("color: #10b981; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(
                t("license.status_pro_desc", key=info.get('masked_key', ''), date=info.get('activated_at', ''))
            )
            self.input_card.setVisible(False)
            self.btn_deactivate.setVisible(True)
            self.btn_buy.setVisible(False)
        elif plan == "trial":
            days = info["trial_days_left"]
            self.status_badge.setText(t("license.status_trial_badge", days=days))
            self.status_badge.setStyleSheet("color: #6366f1; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(t("license.status_trial_desc", days=days))
            self.input_card.setVisible(True)
            self.btn_deactivate.setVisible(False)
            self.btn_buy.setVisible(True)
        else:
            self.status_badge.setText(t("license.status_expired_badge"))
            self.status_badge.setStyleSheet("color: #f59e0b; font-size: 15px; font-weight: 700;")
            self.status_desc.setText(t("license.status_expired_desc"))
            self.input_card.setVisible(True)
            self.btn_deactivate.setVisible(False)
            self.btn_buy.setVisible(True)

    def _retranslate_ui(self) -> None:
        """動態即時切換語言。"""
        self.setWindowTitle(t("license.title"))
        self.title_label.setText(t("license.dialog_header_title"))
        self.subtitle_label.setText(t("license.dialog_header_subtitle"))
        self.key_label.setText(t("license.key_label"))
        self.key_input.setPlaceholderText(t("license.key_placeholder"))
        self.btn_activate.setText(t("license.btn_activate"))
        self.mid_label.setText(f"{t('license.mid_label')}: <code style='color: #6366f1;'>{self.license_mgr.machine_id[:16]}...</code>")
        self.btn_copy_mid.setText(t("license.btn_copy_mid"))
        self.btn_buy.setText(t("license.btn_buy"))
        self.btn_deactivate.setText(t("license.btn_deactivate"))
        mailto_url = (
            "mailto:support@aisming.com?subject=%5B%E5%95%8F%E9%A1%8C%E5%9B%9E%E5%A0%B1%5D%20KyteView%20%E4%BD%BF%E7%94%A8%E8%AB%AE%E8%A9%A2%20-%20%E8%A8%82%E5%96%AE/%E5%BA%8F%E8%99%9F%EF%BC%9A(%E8%8B%A5%E6%9C%89%E8%AB%8B%E5%A1%AB%E5%AF%AB)"
            "&body=1.%20%E4%BD%9C%E6%A5%AD%E7%B3%BB%E7%B5%B1%E7%89%88%E6%9C%AC%20(%E4%BE%8B%E5%A6%82%20Win11%2023H2)%EF%BC%9A%0A"
            "2.%20%E7%99%BC%E7%94%9F%E7%9A%84%E5%95%8F%E9%A1%8C%E6%8F%8F%E8%BF%B0%EF%BC%9A%0A"
            "3.%20%E9%A0%90%E8%A6%BD%E5%93%AA%E7%A8%AE%E9%A1%9E%E5%9E%8B%E7%9A%84%E6%AA%94%E6%A1%88%E6%99%82%E7%99%BC%E7%94%9F%20(%E4%BE%8B%E5%A6%82%20.xlsx%20/%20.mp4)%EF%BC%9A%0A"
            "4.%20%E6%88%AA%E5%9C%96%E6%88%96%E9%8C%AF%E8%AA%A4%E8%A8%8A%E6%81%AF%EF%BC%9A%0A"
        )
        self.support_lbl.setText(
            f"{t('license.support_contact')}：<a href='{mailto_url}' style='color: #818cf8; text-decoration: underline;'>support@aisming.com</a>"
        )
        self.refresh_ui_state()

    def _on_activate_clicked(self) -> None:
        key = self.key_input.text().strip()
        if not key:
            QMessageBox.warning(self, t("license.warn_empty_key"), t("license.warn_empty_key"))
            return

        success, msg = self.license_mgr.activate_license(key)
        if success:
            QMessageBox.information(self, t("license.activate_success_title"), msg)
            self.key_input.clear()
            self.refresh_ui_state()
        else:
            QMessageBox.critical(self, t("license.activate_fail_title"), msg)

    def _on_deactivate_clicked(self) -> None:
        reply = QMessageBox.question(
            self,
            t("license.confirm_deactivate_title"),
            t("license.confirm_deactivate_msg"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.license_mgr.deactivate_license()
            QMessageBox.information(self, t("license.deactivate_result_title"), msg)
            self.refresh_ui_state()

    def _copy_machine_id(self) -> None:
        QApplication.clipboard().setText(self.license_mgr.machine_id)
        QMessageBox.information(self, t("license.mid_copied_title"), t("license.mid_copied_msg"))

    def _open_buy_url(self) -> None:
        webbrowser.open(self.PURCHASE_URL)
