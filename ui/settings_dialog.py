"""
ui/settings_dialog.py
KyteView 現代卡片式偏好設定對話框。
包含：
一、 外觀模式、毛玻璃材質、Pygments 程式碼風格 + 迷你即時預覽
二、 字體大小滑桿、等寬/閱讀字型選擇、換行設定
三、 預設尺寸模式、圖片縮放上限、智慧避讓與輔助互動開關
"""
from __future__ import annotations

import copy
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QFontDatabase, QIcon, QIntValidator
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config.settings import settings
from config.theme import get_theme_colors

# 專屬深色模式風格
DARK_CODE_THEMES = [
    ("Monokai (經典深色)", "monokai"),
    ("One Dark (Atom 風格)", "one-dark"),
    ("Dracula (吸血鬼深色)", "dracula"),
    ("GitHub Dark (現代深色)", "github-dark"),
    ("Nord (極地冷調深色)", "nord"),
    ("Material (質感深色)", "material"),
    ("Solarized Dark (低對比護眼)", "solarized-dark"),
]

# 專屬淺色模式風格
LIGHT_CODE_THEMES = [
    ("Friendly (柔和淺色)", "friendly"),
    ("Visual Studio (清爽淺色)", "vs"),
    ("Default (經典簡約)", "default"),
    ("Solarized Light (暖調護眼)", "solarized-light"),
    ("Gruvbox Light (復古暖黃)", "gruvbox-light"),
    ("Tango (清晰淺色)", "tango"),
    ("Pastie (Ruby 風格淺色)", "pastie"),
]


class SettingsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("KyteView 設定")
        self.resize(740, 560)
        self.setMinimumSize(660, 500)

        # 備份進入設定時的狀態，供取消時完整還原
        self._initial_data = copy.deepcopy(settings._data)
        self._is_saved = False

        # 監聽主題變化動態重繪
        settings.theme_changed.connect(self._on_theme_updated)

        self._build_ui()
        self._load_values()
        self._apply_theme()

    def _build_ui(self) -> None:
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 左側導航欄 ────────────────────────────────────────────────────────
        self._nav_frame = QFrame()
        self._nav_frame.setObjectName("nav_frame")
        self._nav_frame.setFixedWidth(190)
        nav_layout = QVBoxLayout(self._nav_frame)
        nav_layout.setContentsMargins(12, 20, 12, 20)
        nav_layout.setSpacing(8)

        # Logo / 標題
        lbl_title = QLabel("KyteView")
        lbl_title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        lbl_sub = QLabel("偏好設定")
        lbl_sub.setFont(QFont("Segoe UI", 10))
        nav_layout.addWidget(lbl_title)
        nav_layout.addWidget(lbl_sub)
        nav_layout.addSpacing(16)

        # 導航按鈕
        self._btn_group = QButtonGroup(self)
        self._nav_buttons: list[QPushButton] = []
        tabs_info = [
            ("🎨 外觀與主題", 0),
            ("🔤 字體與排版", 1),
            ("📐 視窗與行為", 2),
        ]
        for text, idx in tabs_info:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setFixedHeight(38)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._btn_group.addButton(btn, idx)
            nav_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        self._nav_buttons[0].setChecked(True)
        self._btn_group.idClicked.connect(self._on_nav_tab_changed)

        nav_layout.addStretch()

        # 版本提示
        lbl_ver = QLabel("v1.2.0 • 64-bit")
        lbl_ver.setStyleSheet("color: #71717a; font-size: 11px;")
        nav_layout.addWidget(lbl_ver)

        main_layout.addWidget(self._nav_frame)

        # ── 右側分頁容器 ──────────────────────────────────────────────────────
        self._content_frame = QFrame()
        content_layout = QVBoxLayout(self._content_frame)
        content_layout.setContentsMargins(24, 24, 24, 20)
        content_layout.setSpacing(14)

        self._pages = QStackedWidget()
        self._pages.addWidget(self._create_page_appearance())
        self._pages.addWidget(self._create_page_typography())
        self._pages.addWidget(self._create_page_behavior())

        content_layout.addWidget(self._pages, 1)

        # ── 底部操作按鈕列 (Cancel / Save) ───────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(0, 6, 0, 0)
        bottom_bar.setSpacing(10)

        # 儲存成功即時反饋標籤
        self._lbl_save_status = QLabel("")
        self._lbl_save_status.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        bottom_bar.addWidget(self._lbl_save_status)

        bottom_bar.addStretch()

        self._btn_cancel = QPushButton("關閉 (Close)")
        self._btn_cancel.setObjectName("btn_dialog_cancel")
        self._btn_cancel.setFixedWidth(100)
        self._btn_cancel.setFixedHeight(34)
        self._btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_cancel.clicked.connect(self.reject)

        self._btn_save = QPushButton("儲存設定 (Save)")
        self._btn_save.setObjectName("btn_dialog_save")
        self._btn_save.setFixedWidth(125)
        self._btn_save.setFixedHeight(34)
        self._btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_save.clicked.connect(self._on_save_clicked)

        bottom_bar.addWidget(self._btn_cancel)
        bottom_bar.addWidget(self._btn_save)
        content_layout.addLayout(bottom_bar)

        main_layout.addWidget(self._content_frame, 1)

    def reload_values(self) -> None:
        """重新開啟對話框時重新整理資料快照與表單值。"""
        self._initial_data = copy.deepcopy(settings._data)
        self._is_saved = False
        self._load_values()

    # ── 分頁 1：外觀與主題 ────────────────────────────────────────────────────
    def _create_page_appearance(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # 1. 外觀模式
        grp_theme = QGroupBox("外觀模式 (Appearance Mode)")
        grp_theme_layout = QVBoxLayout(grp_theme)
        grp_theme_layout.setSpacing(10)

        theme_btn_row = QHBoxLayout()
        self._rb_theme_system = QRadioButton("跟隨系統 (System)")
        self._rb_theme_dark = QRadioButton("深色模式 (Dark)")
        self._rb_theme_light = QRadioButton("淺色模式 (Light)")

        self._theme_btn_group = QButtonGroup(self)
        self._theme_btn_group.addButton(self._rb_theme_system, 0)
        self._theme_btn_group.addButton(self._rb_theme_dark, 1)
        self._theme_btn_group.addButton(self._rb_theme_light, 2)
        self._theme_btn_group.idClicked.connect(self._on_theme_mode_changed)

        theme_btn_row.addWidget(self._rb_theme_system)
        theme_btn_row.addWidget(self._rb_theme_dark)
        theme_btn_row.addWidget(self._rb_theme_light)
        theme_btn_row.addStretch()
        grp_theme_layout.addLayout(theme_btn_row)

        lbl_theme_hint = QLabel("💡 選擇跟隨系統將自動即時響應 Windows 11/10 的深淺色切換。")
        lbl_theme_hint.setStyleSheet("font-size: 11px; color: #71717a;")
        grp_theme_layout.addWidget(lbl_theme_hint)
        layout.addWidget(grp_theme)

        # 2. 背景材質效果
        grp_material = QGroupBox("視窗材質 (Background Effect)")
        grp_material_layout = QVBoxLayout(grp_material)
        self._cb_acrylic = QCheckBox("啟用毛玻璃半透明效果 (Acrylic / Mica Effect)")
        self._cb_acrylic.toggled.connect(self._on_acrylic_toggled)
        grp_material_layout.addWidget(self._cb_acrylic)
        lbl_mat_hint = QLabel("若顯卡或筆電處於省電模式，關閉毛玻璃可降低 GPU 渲染功耗。")
        lbl_mat_hint.setStyleSheet("font-size: 11px; color: #71717a;")
        grp_material_layout.addWidget(lbl_mat_hint)
        layout.addWidget(grp_material)

        # 3. 程式碼著色風格與即時預覽
        grp_code = QGroupBox("程式碼著色風格 (Code Highlighter Theme)")
        grp_code_layout = QVBoxLayout(grp_code)
        grp_code_layout.setSpacing(10)

        code_row = QHBoxLayout()
        code_row.addWidget(QLabel("主題風格："))
        self._combo_code_theme = QComboBox()
        self._combo_code_theme.setView(QListView())
        self._combo_code_theme.currentIndexChanged.connect(self._on_code_theme_changed)
        code_row.addWidget(self._combo_code_theme, 1)
        grp_code_layout.addLayout(code_row)

        # 即時迷你程式碼預覽
        self._code_preview = QTextBrowser()
        self._code_preview.setFixedHeight(88)
        self._code_preview.setStyleSheet("border-radius: 6px; border: 1px solid rgba(128, 128, 128, 0.2);")
        grp_code_layout.addWidget(self._code_preview)

        layout.addWidget(grp_code)
        layout.addStretch()
        return w

    # ── 分頁 2：字體與排版 ────────────────────────────────────────────────────
    def _create_page_typography(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # 1. 字體大小滑桿
        grp_size = QGroupBox("字體大小 (Font Size)")
        grp_size_layout = QVBoxLayout(grp_size)
        grp_size_layout.setSpacing(10)

        size_row = QHBoxLayout()
        self._slider_font_size = QSlider(Qt.Orientation.Horizontal)
        self._slider_font_size.setRange(11, 20)
        self._slider_font_size.setSingleStep(1)
        self._slider_font_size.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._slider_font_size.setTickInterval(1)

        self._lbl_font_size_val = QLabel("13 px")
        self._lbl_font_size_val.setFixedWidth(50)
        self._lbl_font_size_val.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))

        btn_reset_font = QPushButton("重設")
        btn_reset_font.setFixedWidth(60)
        btn_reset_font.clicked.connect(lambda: self._slider_font_size.setValue(13))

        size_row.addWidget(self._slider_font_size, 1)
        size_row.addWidget(self._lbl_font_size_val)
        size_row.addWidget(btn_reset_font)
        grp_size_layout.addLayout(size_row)

        self._slider_font_size.valueChanged.connect(self._on_font_size_changed)
        layout.addWidget(grp_size)

        # 2. 字型設定
        grp_family = QGroupBox("字型族系 (Font Families)")
        grp_family_layout = QVBoxLayout(grp_family)
        grp_family_layout.setSpacing(12)

        # 程式碼等寬字型
        code_f_row = QHBoxLayout()
        code_f_row.addWidget(QLabel("等寬字型（程式碼/文字）："))
        self._combo_code_font = QComboBox()
        self._combo_code_font.setView(QListView())
        common_mono = [
            "Cascadia Code",
            "Consolas",
            "Fira Code",
            "JetBrains Mono",
            "Courier New",
        ]
        # 加上系統已安裝的字型
        installed_families = set(QFontDatabase.families())
        for f in common_mono:
            if f in installed_families:
                self._combo_code_font.addItem(f, f)
        if self._combo_code_font.count() == 0:
            self._combo_code_font.addItem("Consolas", "Consolas")
        self._combo_code_font.currentIndexChanged.connect(self._on_code_font_changed)
        code_f_row.addWidget(self._combo_code_font, 1)
        grp_family_layout.addLayout(code_f_row)

        # 閱讀字型
        text_f_row = QHBoxLayout()
        text_f_row.addWidget(QLabel("閱讀字型（Markdown/文字）："))
        self._combo_text_font = QComboBox()
        self._combo_text_font.setView(QListView())
        common_text = [
            "Microsoft JhengHei UI",
            "Segoe UI Variable",
            "Segoe UI",
            "Arial",
        ]
        for f in common_text:
            if f in installed_families:
                self._combo_text_font.addItem(f, f)
        if self._combo_text_font.count() == 0:
            self._combo_text_font.addItem("Microsoft JhengHei UI", "Microsoft JhengHei UI")
        self._combo_text_font.currentIndexChanged.connect(self._on_text_font_changed)
        text_f_row.addWidget(self._combo_text_font, 1)
        grp_family_layout.addLayout(text_f_row)

        layout.addWidget(grp_family)

        # 3. 排版選項
        grp_opt = QGroupBox("排版選項 (Typography Options)")
        grp_opt_layout = QVBoxLayout(grp_opt)
        grp_opt_layout.setSpacing(10)

        self._cb_ligatures = QCheckBox("啟用連字效果 (Font Ligatures，若字型支援如 !=、-> 自動轉化)")
        self._cb_ligatures.toggled.connect(lambda v: setattr(settings, "enable_ligatures", v))
        grp_opt_layout.addWidget(self._cb_ligatures)

        self._cb_word_wrap = QCheckBox("長行自動換行 (Word Wrap，避免超出視窗邊界強制橫向滾動)")
        self._cb_word_wrap.toggled.connect(lambda v: setattr(settings, "word_wrap", v))
        grp_opt_layout.addWidget(self._cb_word_wrap)

        layout.addWidget(grp_opt)
        layout.addStretch()
        return w

    # ── 分頁 3：視窗與行為 ────────────────────────────────────────────────────
    def _create_page_behavior(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)

        # 1. 預設視窗大小模式
        grp_size_mode = QGroupBox("預設視窗大小模式 (Window Sizing)")
        grp_size_mode_layout = QVBoxLayout(grp_size_mode)
        grp_size_mode_layout.setSpacing(10)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("尺寸策略："))
        self._combo_size_mode = QComboBox()
        self._combo_size_mode.setView(QListView())
        self._combo_size_mode.addItem("智慧記憶 (自動記憶最後調整的大小)", "remember")
        self._combo_size_mode.addItem("自訂固定解析度 (依下方自訂寬高固定顯示)", "fixed")
        self._combo_size_mode.addItem("螢幕比例自適應 (寬55% x 高60%)", "adaptive")
        self._combo_size_mode.currentIndexChanged.connect(self._on_size_mode_changed)
        mode_row.addWidget(self._combo_size_mode, 1)
        grp_size_mode_layout.addLayout(mode_row)

        # 自訂固定寬高 (QLineEdit 支援鍵盤直接輸入與選取)
        self._fixed_row = QHBoxLayout()
        self._fixed_row.setSpacing(8)

        lbl_w = QLabel("自訂寬度：")
        self._edit_fixed_w = QLineEdit()
        self._edit_fixed_w.setValidator(QIntValidator(200, 3840, self))
        self._edit_fixed_w.setFixedWidth(85)
        self._edit_fixed_w.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_fixed_w.setPlaceholderText("820")
        lbl_w_unit = QLabel("px")
        lbl_w_unit.setStyleSheet("color: #71717a; font-size: 12px;")

        lbl_h = QLabel("自訂高度：")
        self._edit_fixed_h = QLineEdit()
        self._edit_fixed_h.setValidator(QIntValidator(150, 2160, self))
        self._edit_fixed_h.setFixedWidth(85)
        self._edit_fixed_h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._edit_fixed_h.setPlaceholderText("600")
        lbl_h_unit = QLabel("px")
        lbl_h_unit.setStyleSheet("color: #71717a; font-size: 12px;")

        self._fixed_row.addWidget(lbl_w)
        self._fixed_row.addWidget(self._edit_fixed_w)
        self._fixed_row.addWidget(lbl_w_unit)
        self._fixed_row.addSpacing(16)
        self._fixed_row.addWidget(lbl_h)
        self._fixed_row.addWidget(self._edit_fixed_h)
        self._fixed_row.addWidget(lbl_h_unit)
        self._fixed_row.addStretch()
        grp_size_mode_layout.addLayout(self._fixed_row)

        self._lbl_size_hint = QLabel("")
        self._lbl_size_hint.setStyleSheet("font-size: 11px; color: #71717a; margin-top: 2px;")
        grp_size_mode_layout.addWidget(self._lbl_size_hint)

        layout.addWidget(grp_size_mode)

        # 2. 圖片顯示設定
        grp_img = QGroupBox("圖片預覽設定 (Image Preview)")
        grp_img_layout = QVBoxLayout(grp_img)
        grp_img_layout.setSpacing(10)

        img_ratio_row = QHBoxLayout()
        img_ratio_row.addWidget(QLabel("大圖片縮放上限 (螢幕佔比)："))
        self._slider_img_ratio = QSlider(Qt.Orientation.Horizontal)
        self._slider_img_ratio.setRange(50, 90)
        self._slider_img_ratio.setValue(settings.img_max_screen_ratio)
        self._lbl_img_ratio_val = QLabel(f"{settings.img_max_screen_ratio}%")
        self._slider_img_ratio.valueChanged.connect(self._on_img_ratio_changed)
        img_ratio_row.addWidget(self._slider_img_ratio, 1)
        img_ratio_row.addWidget(self._lbl_img_ratio_val)
        grp_img_layout.addLayout(img_ratio_row)

        self._cb_keep_orig_img = QCheckBox("小圖片保持 1:1 原生尺寸顯示（不強制放大）")
        self._cb_keep_orig_img.toggled.connect(lambda v: setattr(settings, "img_keep_original", v))
        grp_img_layout.addWidget(self._cb_keep_orig_img)

        layout.addWidget(grp_img)

        # 3. 智慧避讓與互動輔助
        grp_interact = QGroupBox("智慧避讓與互動輔助 (Interactions)")
        grp_interact_layout = QVBoxLayout(grp_interact)
        grp_interact_layout.setSpacing(10)

        self._cb_smart_offset = QCheckBox("智慧避讓偏移（依檔案總管視窗位置自動靠左/靠右偏移微調）")
        self._cb_smart_offset.toggled.connect(lambda v: setattr(settings, "smart_offset", v))
        grp_interact_layout.addWidget(self._cb_smart_offset)

        self._cb_enable_peek = QCheckBox("長按修飾鍵（Ctrl / Alt）視窗暫時微透機制")
        self._cb_enable_peek.toggled.connect(lambda v: setattr(settings, "enable_peek", v))
        grp_interact_layout.addWidget(self._cb_enable_peek)

        self._cb_enable_pin = QCheckBox("按 Tab 鍵切換側邊釘選模式 (Split Dock)")
        self._cb_enable_pin.toggled.connect(lambda v: setattr(settings, "enable_pin_dock", v))
        grp_interact_layout.addWidget(self._cb_enable_pin)

        layout.addWidget(grp_interact)
        layout.addStretch()
        return w

    # ── 載入數值 ──────────────────────────────────────────────────────────────
    def _load_values(self) -> None:
        # 外觀模式
        mode = settings.theme_mode
        if mode == "system":
            self._rb_theme_system.setChecked(True)
        elif mode == "dark":
            self._rb_theme_dark.setChecked(True)
        else:
            self._rb_theme_light.setChecked(True)

        self._cb_acrylic.setChecked(settings.enable_acrylic)

        # 程式碼風格（依深淺色模式動態過濾）
        self._populate_code_themes()

        # 字體大小
        self._slider_font_size.setValue(settings.font_size)
        self._lbl_font_size_val.setText(f"{settings.font_size} px")

        # 字型
        c_font_idx = self._combo_code_font.findData(settings.font_family_code)
        if c_font_idx >= 0:
            self._combo_code_font.setCurrentIndex(c_font_idx)

        t_font_idx = self._combo_text_font.findData(settings.font_family_text)
        if t_font_idx >= 0:
            self._combo_text_font.setCurrentIndex(t_font_idx)

        self._cb_ligatures.setChecked(settings.enable_ligatures)
        self._cb_word_wrap.setChecked(settings.word_wrap)

        # 視窗行為
        sm_idx = self._combo_size_mode.findData(settings.window_size_mode)
        if sm_idx >= 0:
            self._combo_size_mode.setCurrentIndex(sm_idx)

        # 讀取寬度與高度預填入 QLineEdit
        if settings.window_size_mode == "fixed":
            cur_w = settings.fixed_width
            cur_h = settings.fixed_height
        else:
            cur_w, cur_h = settings.window_size
        self._edit_fixed_w.setText(str(cur_w))
        self._edit_fixed_h.setText(str(cur_h))
        self._on_size_mode_changed(self._combo_size_mode.currentIndex())

        self._cb_keep_orig_img.setChecked(settings.img_keep_original)
        self._cb_smart_offset.setChecked(settings.smart_offset)
        self._cb_enable_peek.setChecked(settings.enable_peek)
        self._cb_enable_pin.setChecked(settings.enable_pin_dock)

    def _populate_code_themes(self) -> None:
        """依當前深淺色模式過濾出專屬適合的程式碼著色風格。"""
        is_dark = settings.is_dark()
        themes = DARK_CODE_THEMES if is_dark else LIGHT_CODE_THEMES

        self._combo_code_theme.blockSignals(True)
        self._combo_code_theme.clear()

        current_val = settings.code_theme
        selected_idx = 0

        for idx, (label, val) in enumerate(themes):
            self._combo_code_theme.addItem(label, val)
            if val == current_val:
                selected_idx = idx

        # 若目前設定的風格不在本模式清單中，自動採用第 1 款預設風格
        val_list = [v for _, v in themes]
        if current_val not in val_list and themes:
            selected_idx = 0
            settings.code_theme = themes[0][1]

        self._combo_code_theme.setCurrentIndex(selected_idx)
        self._combo_code_theme.blockSignals(False)
        self._update_code_preview()

    # ── 事件響應 ──────────────────────────────────────────────────────────────
    def _on_nav_tab_changed(self, idx: int) -> None:
        self._pages.setCurrentIndex(idx)

    def _on_theme_mode_changed(self, btn_id: int) -> None:
        modes = ["system", "dark", "light"]
        if 0 <= btn_id < len(modes):
            settings.theme_mode = modes[btn_id]
            self._populate_code_themes()

    def _on_acrylic_toggled(self, enabled: bool) -> None:
        settings.enable_acrylic = enabled

    def _on_code_theme_changed(self, idx: int) -> None:
        val = self._combo_code_theme.itemData(idx)
        if val:
            settings.code_theme = val
            self._update_code_preview()

    def _on_font_size_changed(self, val: int) -> None:
        self._lbl_font_size_val.setText(f"{val} px")
        settings.font_size = val
        self._update_code_preview()

    def _on_code_font_changed(self, idx: int) -> None:
        val = self._combo_code_font.itemData(idx)
        if val:
            settings.font_family_code = val
            self._update_code_preview()

    def _on_text_font_changed(self, idx: int) -> None:
        val = self._combo_text_font.itemData(idx)
        if val:
            settings.font_family_text = val

    def _on_size_mode_changed(self, idx: int) -> None:
        val = self._combo_size_mode.itemData(idx)
        if val == "fixed":
            self._edit_fixed_w.setEnabled(True)
            self._edit_fixed_h.setEnabled(True)
            self._lbl_size_hint.setText("💡 固定尺寸模式：視窗開啟時一律強制以自訂的像素寬高呈現。")
        elif val == "remember":
            self._edit_fixed_w.setEnabled(True)
            self._edit_fixed_h.setEnabled(True)
            self._lbl_size_hint.setText("💡 智慧記憶模式：上方數值為預設基準；手動拉伸視窗時將自動記憶最新大小。")
        elif val == "adaptive":
            self._edit_fixed_w.setEnabled(False)
            self._edit_fixed_h.setEnabled(False)
            self._lbl_size_hint.setText("💡 螢幕自適應模式：按螢幕解析度比例自動計算視窗大小，自訂尺寸暫不生效。")

    def _on_img_ratio_changed(self, val: int) -> None:
        self._lbl_img_ratio_val.setText(f"{val}%")
        settings.img_max_screen_ratio = val

    def _on_save_clicked(self) -> None:
        """按下儲存設定按鈕：批次寫入 settings 並一次性寫入 JSON，消除所有卡頓。"""
        # 1. 寬度與高度解析（允許自訂至 200x150）
        try:
            w_val = int(self._edit_fixed_w.text().strip())
        except (ValueError, TypeError):
            w_val = 820
        w_val = max(200, min(3840, w_val))

        try:
            h_val = int(self._edit_fixed_h.text().strip())
        except (ValueError, TypeError):
            h_val = 600
        h_val = max(150, min(2160, h_val))

        # 2. 彙整所有更新欄位，單次 I/O 寫入
        size_mode = self._combo_size_mode.currentData() or "remember"
        mode_idx = self._theme_btn_group.checkedId()
        modes = ["system", "dark", "light"]
        theme_m = modes[mode_idx] if 0 <= mode_idx < len(modes) else "system"

        updates: dict[str, Any] = {
            "window_size_mode": size_mode,
            "fixed_width": w_val,
            "fixed_height": h_val,
            "window_width": w_val,
            "window_height": h_val,
            "theme_mode": theme_m,
            "enable_acrylic": self._cb_acrylic.isChecked(),
            "font_size": self._slider_font_size.value(),
            "enable_ligatures": self._cb_ligatures.isChecked(),
            "word_wrap": self._cb_word_wrap.isChecked(),
            "img_max_screen_ratio": self._slider_img_ratio.value(),
            "img_keep_original": self._cb_keep_orig_img.isChecked(),
            "smart_offset": self._cb_smart_offset.isChecked(),
            "enable_peek": self._cb_enable_peek.isChecked(),
            "enable_pin_dock": self._cb_enable_pin.isChecked(),
        }

        code_theme = self._combo_code_theme.currentData()
        if code_theme:
            updates["code_theme"] = code_theme

        cf = self._combo_code_font.currentData()
        if cf:
            updates["font_family_code"] = cf
        tf = self._combo_text_font.currentData()
        if tf:
            updates["font_family_text"] = tf

        # 單次寫入硬碟與統一發送信號（0 延遲，極速流暢）
        settings.batch_update(updates)

        # 更新基準快照為本次已儲存之資料
        self._initial_data = copy.deepcopy(settings._data)
        self._is_saved = True

        # 介面即時反饋：顯示已儲存提示，視窗保持開啟
        self._lbl_save_status.setText("✓ 設定已儲存")
        self._btn_save.setText("✓ 已儲存")
        QTimer.singleShot(1500, self._reset_save_btn_state)

    def _reset_save_btn_state(self) -> None:
        self._lbl_save_status.setText("")
        self._btn_save.setText("儲存設定 (Save)")

    def reject(self) -> None:
        """點擊關閉或按 ESC 時，若有未儲存的暫存更動則還原回最後一次儲存的快照。"""
        if hasattr(self, "_initial_data") and settings._data != self._initial_data:
            settings._data = copy.deepcopy(self._initial_data)
            settings._save()
            settings.theme_changed.emit(settings.effective_theme)
            settings.settings_changed.emit("all")
        super().reject()

    def _update_code_preview(self) -> None:
        """即時渲染迷你 3 行代碼預覽塊。"""
        from pygments import highlight
        from pygments.formatters import HtmlFormatter
        from pygments.lexers import PythonLexer

        code_snippet = "def hello_kyteview():\n    print('Instant Preview Ready!')\n    return True"
        theme_name = settings.code_theme
        font_code = settings.font_family_code or "Cascadia Code"
        font_size = max(11, settings.font_size - 1)
        c = get_theme_colors()

        try:
            formatter = HtmlFormatter(style=theme_name, nowrap=False)
        except Exception:
            theme_name = "monokai" if settings.is_dark() else "friendly"
            formatter = HtmlFormatter(style=theme_name, nowrap=False)
        pygments_css = formatter.get_style_defs(".highlight")

        # 自動提取該風格的原生專屬背景色
        bg_color = c["code_bg"]
        try:
            from pygments.styles import get_style_by_name
            st_obj = get_style_by_name(theme_name)
            style_bg = getattr(st_obj, "background_color", None)
            if style_bg and style_bg.startswith("#"):
                bg_color = style_bg
        except Exception:
            pass

        # 同步更新預覽框外框與底色
        self._code_preview.setStyleSheet(f"""
            QTextBrowser {{
                background-color: {bg_color};
                border: 1px solid rgba(128, 128, 128, 0.25);
                border-radius: 6px;
            }}
        """)

        css = f"""
        <style>
        html, body {{
            background-color: {bg_color};
            color: {c['text_color']};
            font-family: '{font_code}', Consolas, monospace;
            font-size: {font_size}px;
            margin: 0;
            padding: 8px 10px;
        }}
        .highlight, pre {{
            background-color: {bg_color} !important;
            margin: 0;
        }}
        {pygments_css}
        </style>
        """
        html = f"<html><head>{css}</head><body>{highlight(code_snippet, PythonLexer(), formatter)}</body></html>"
        self._code_preview.setHtml(html)

    def _on_theme_updated(self, new_theme: str) -> None:
        self._apply_theme()
        self._populate_code_themes()

    def _apply_theme(self) -> None:
        c = get_theme_colors()
        is_dark = settings.is_dark()
        dlg_bg = "#18181b" if is_dark else "#f4f4f5"
        nav_bg = "#121214" if is_dark else "#e4e4e7"
        text_c = c["title_color"]
        border_c = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        active_btn_bg = "#6366f1" if is_dark else "#4f46e5"

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {dlg_bg};
                color: {text_c};
            }}
            QFrame {{
                border: none;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 1px solid {border_c};
                border-radius: 8px;
                margin-top: 8px;
                padding-top: 14px;
                background-color: {'rgba(255, 255, 255, 0.02)' if is_dark else '#ffffff'};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                color: {text_c};
            }}
            QLabel {{
                color: {text_c};
            }}
            QRadioButton, QCheckBox {{
                color: {text_c};
                spacing: 8px;
            }}
            QComboBox, QSpinBox {{
                background-color: {'#27272a' if is_dark else '#ffffff'};
                color: {'#f3f4f6' if is_dark else '#111827'};
                border: 1px solid {border_c};
                border-radius: 6px;
                padding: 5px 10px;
            }}
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {'#1f1f23' if is_dark else '#ffffff'};
                color: {'#f3f4f6' if is_dark else '#111827'};
                border: 1px solid {'#3f3f46' if is_dark else '#e4e4e7'};
                border-radius: 8px;
                padding: 4px;
                selection-background-color: {active_btn_bg};
                selection-color: #ffffff;
                outline: none;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 28px;
                padding: 4px 10px;
                border-radius: 4px;
                color: {'#f3f4f6' if is_dark else '#111827'};
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {'#374151' if is_dark else '#f3f4f6'};
                color: {'#ffffff' if is_dark else '#111827'};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {active_btn_bg};
                color: #ffffff;
            }}
            QLineEdit {{
                background-color: {'#27272a' if is_dark else '#ffffff'};
                color: {'#f3f4f6' if is_dark else '#111827'};
                border: 1px solid {border_c};
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 13px;
                font-family: 'Consolas', 'Segoe UI', monospace;
            }}
            QLineEdit:focus {{
                border: 1px solid {active_btn_bg};
            }}
            QLineEdit:disabled {{
                background-color: {'#1c1c1f' if is_dark else '#f4f4f5'};
                color: {'#71717a' if is_dark else '#a1a1aa'};
            }}
            QPushButton {{
                background: {'#27272a' if is_dark else '#ffffff'};
                color: {text_c};
                border: 1px solid {border_c};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton:checked {{
                background: {active_btn_bg};
                color: #ffffff;
                font-weight: bold;
            }}
            QPushButton#btn_dialog_save {{
                background-color: {active_btn_bg};
                color: #ffffff;
                font-weight: bold;
                border: none;
                border-radius: 6px;
                padding: 6px 16px;
            }}
            QPushButton#btn_dialog_save:hover {{
                background-color: {'#4f46e5' if is_dark else '#4338ca'};
            }}
            QPushButton#btn_dialog_cancel {{
                background-color: {'#27272a' if is_dark else '#f4f4f5'};
                color: {text_c};
                border: 1px solid {border_c};
                border-radius: 6px;
                padding: 6px 14px;
            }}
            QPushButton#btn_dialog_cancel:hover {{
                background-color: {'#3f3f46' if is_dark else '#e4e4e7'};
            }}
        """)

        nav_btn_color = "#a1a1aa" if is_dark else "#3f3f46"
        nav_btn_hover = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.06)"
        nav_btn_hover_text = "#ffffff" if is_dark else "#09090b"

        self._nav_frame.setStyleSheet(f"""
            QFrame#nav_frame {{
                background-color: {nav_bg};
                border-right: 1px solid {border_c};
            }}
            QFrame#nav_frame QLabel {{
                color: {text_c};
            }}
            QPushButton {{
                background-color: transparent;
                color: {nav_btn_color};
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                text-align: left;
                font-size: 13px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: {nav_btn_hover};
                color: {nav_btn_hover_text};
            }}
            QPushButton:checked {{
                background-color: {active_btn_bg};
                color: #ffffff;
                font-weight: bold;
            }}
        """)
