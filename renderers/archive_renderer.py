"""
renderers/archive_renderer.py
KyteView 壓縮檔極速瀏覽器：
- 支援 .zip, .tar, .tar.gz, .tar.bz2, .tar.xz, .tgz, .7z, .rar
- 階梯式零依賴：內建 zipfile / tarfile 5ms 秒讀 Central Directory，完全無需解壓整個封裝包。
- 樹狀結構階層瀏覽 (QTreeView + QStandardItemModel)，預設自動展開第 1~2 層。
- 頂部即時過濾搜尋框 (QSortFilterProxyModel 遞迴過濾)。
- 殺手級「單檔拖曳抽出」(Drag & Drop Extract)：直接拖曳單一檔案至桌面或資料夾。
- 雙擊或 Enter 巢狀就地解壓預覽，按 Backspace 返回。
- 防卡死機制：上限 1,000 項目保護，超大專案包毫秒級瞬開不凍結。
"""
from __future__ import annotations

import os
import sys
import tempfile
import zipfile
import tarfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import (
    Qt, QModelIndex, QPoint, QRect, QSize, Signal, QSortFilterProxyModel, QUrl,
)
from PySide6.QtGui import (
    QStandardItemModel, QStandardItem, QFont, QIcon,
    QMouseEvent, QKeyEvent, QDrag, QCursor, QColor,
)
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QTreeView, QHeaderView, QFrame, QPushButton, QApplication,
)
from PySide6.QtCore import QMimeData

from renderers.base import BaseRenderer
from config.settings import settings
from config.theme import get_theme_colors


@dataclass
class ArchiveEntry:
    path: str
    is_dir: bool
    size: int
    compress_size: Optional[int]
    mtime: str


def _format_size(n: Optional[int]) -> str:
    if n is None or n < 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def _get_file_icon_symbol(ext: str) -> str:
    ext = ext.lower()
    if ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".c", ".cpp", ".cs", ".go", ".rs", ".html", ".css", ".json", ".xml", ".yaml", ".yml"):
        return "📜"
    if ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".svg"):
        return "🖼️"
    if ext in (".mp3", ".wav", ".flac", ".ogg", ".aac", ".m4a"):
        return "🎵"
    if ext in (".mp4", ".mkv", ".avi", ".mov", ".webm"):
        return "🎬"
    if ext in (".pdf", ".docx", ".doc", ".xlsx", ".csv", ".pptx", ".txt", ".md"):
        return "📄"
    if ext in (".zip", ".7z", ".rar", ".tar", ".gz"):
        return "📦"
    return "📄"


class _ArchiveTreeView(QTreeView):
    """自訂 TreeView，支援單檔按住左鍵向外拖曳抽出 (Drag & Drop Extract)。"""
    def __init__(self, parent: ArchiveBrowserWidget) -> None:
        super().__init__(parent)
        self._browser = parent
        self._drag_start_pos: Optional[QPoint] = None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_start_pos and (event.buttons() & Qt.MouseButton.LeftButton):
            dist = (event.position().toPoint() - self._drag_start_pos).manhattanLength()
            if dist >= QApplication.startDragDistance():
                self._browser.start_drag_extract()
                self._drag_start_pos = None
                return
        super().mouseMoveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            selected = self._browser._get_selected_entry_info()
            if selected and not selected[1]:
                inner_path = selected[0]
                extracted_file = self._browser._extract_single_file(inner_path)
                if extracted_file and extracted_file.exists():
                    self._browser.open_nested_file.emit(extracted_file)
                    return
        super().keyPressEvent(event)


class ArchiveBrowserWidget(QWidget):
    """壓縮檔樹狀瀏覽主畫面。"""
    open_nested_file = Signal(Path)

    def __init__(self, archive_path: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._archive_path = archive_path
        self._entries: list[ArchiveEntry] = []
        self._total_uncompressed = 0
        self._total_compressed = 0
        self._is_truncated = False

        self._read_archive_entries()
        self._build_ui()
        self._populate_tree()

    def _read_archive_entries(self) -> None:
        """根據副檔名快速讀取 Central Directory / 檔頭目錄清單。"""
        suffix = self._archive_path.suffix.lower()
        suffixes = "".join(self._archive_path.suffixes).lower()
        count = 0
        limit = 1000

        try:
            if suffix == ".zip":
                with zipfile.ZipFile(self._archive_path, "r") as zf:
                    for info in zf.infolist():
                        count += 1
                        if count > limit:
                            self._is_truncated = True
                            break
                        mtime_str = f"{info.date_time[0]:04d}-{info.date_time[1]:02d}-{info.date_time[2]:02d} {info.date_time[3]:02d}:{info.date_time[4]:02d}"
                        self._entries.append(ArchiveEntry(
                            path=info.filename,
                            is_dir=info.is_dir(),
                            size=info.file_size,
                            compress_size=info.compress_size,
                            mtime=mtime_str,
                        ))
                        self._total_uncompressed += info.file_size
                        self._total_compressed += info.compress_size

            elif ".tar" in suffixes or suffix in (".tgz", ".tar"):
                with tarfile.open(self._archive_path, "r:*") as tf:
                    for member in tf.getmembers():
                        count += 1
                        if count > limit:
                            self._is_truncated = True
                            break
                        dt = datetime.fromtimestamp(member.mtime) if member.mtime else None
                        mtime_str = dt.strftime("%Y-%m-%d %H:%M") if dt else "—"
                        self._entries.append(ArchiveEntry(
                            path=member.name,
                            is_dir=member.isdir(),
                            size=member.size,
                            compress_size=member.size,
                            mtime=mtime_str,
                        ))
                        self._total_uncompressed += member.size
                        self._total_compressed += member.size

            elif suffix == ".7z":
                try:
                    import py7zr
                    with py7zr.SevenZipFile(self._archive_path, "r") as zf:
                        for item in zf.list():
                            count += 1
                            if count > limit:
                                self._is_truncated = True
                                break
                            mtime_str = item.creationtime.strftime("%Y-%m-%d %H:%M") if item.creationtime else "—"
                            u_size = item.uncompressed or 0
                            c_size = item.compressed  # 7z 固實壓縮時為 None
                            self._entries.append(ArchiveEntry(
                                path=item.filename,
                                is_dir=item.is_directory,
                                size=u_size,
                                compress_size=c_size,
                                mtime=mtime_str,
                            ))
                            self._total_uncompressed += u_size
                            if c_size is not None:
                                self._total_compressed += c_size
                except Exception as e:
                    print(f"[Archive] 7z 讀取失敗: {e}")

            elif suffix == ".rar":
                try:
                    import rarfile
                    with rarfile.RarFile(self._archive_path) as rf:
                        for info in rf.infolist():
                            count += 1
                            if count > limit:
                                self._is_truncated = True
                                break
                            dt_str = datetime(*info.date_time).strftime("%Y-%m-%d %H:%M") if info.date_time else "—"
                            self._entries.append(ArchiveEntry(
                                path=info.filename,
                                is_dir=info.isdir(),
                                size=info.file_size,
                                compress_size=info.compress_size,
                                mtime=dt_str,
                            ))
                            self._total_uncompressed += info.file_size
                            self._total_compressed += info.compress_size
                except Exception as e:
                    print(f"[Archive] rar 讀取失敗: {e}")

        except Exception as e:
            print(f"[Archive] 解析異常: {e}")

        # 若壓縮大小總和為 0（如 7z 固實壓縮沒有提供單檔壓縮大小），採用封裝包實體大小
        if self._total_compressed == 0 and self._total_uncompressed > 0:
            try:
                self._total_compressed = self._archive_path.stat().st_size
            except Exception:
                pass

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(10)

        # 頂部控制列：即時過濾搜尋框 + 拖曳提示
        top_bar = QHBoxLayout()
        top_bar.setSpacing(10)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍  即時搜尋壓縮包內部檔案...")
        self._search_edit.setFixedHeight(32)
        self._search_edit.textChanged.connect(self._on_search_changed)
        top_bar.addWidget(self._search_edit, 1)

        from core.license import LicenseManager
        is_pro = LicenseManager.get_instance().is_unlimited()

        if is_pro:
            lbl_drag_hint = QLabel("💡 支援選中檔案直接拖曳抽出")
            lbl_drag_hint.setStyleSheet("color: #71717a; font-size: 11px;")
        else:
            lbl_drag_hint = QPushButton("🔒 拖曳抽出與巢狀預覽 (點擊解鎖)")
            lbl_drag_hint.setCursor(Qt.CursorShape.PointingHandCursor)
            lbl_drag_hint.setStyleSheet("""
                QPushButton {
                    color: #818cf8;
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                    border: none;
                    text-decoration: underline;
                }
                QPushButton:hover {
                    color: #a5b4fc;
                }
            """)
            def _open_lic():
                from ui.license_dialog import LicenseDialog
                dlg = LicenseDialog(self)
                dlg.exec()
            lbl_drag_hint.clicked.connect(_open_lic)

        top_bar.addWidget(lbl_drag_hint)
        layout.addLayout(top_bar)

        # 樹狀視圖
        self._model = QStandardItemModel(0, 4)
        self._model.setHorizontalHeaderLabels(["名稱", "原始大小", "壓縮大小", "修改日期"])

        self._proxy_model = QSortFilterProxyModel(self)
        self._proxy_model.setSourceModel(self._model)
        self._proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._proxy_model.setRecursiveFilteringEnabled(True)

        self._tree = _ArchiveTreeView(self)
        self._tree.setModel(self._proxy_model)
        self._tree.setAlternatingRowColors(True)
        self._tree.setAnimated(True)
        self._tree.setUniformRowHeights(True)
        self._tree.header().setStretchLastSection(False)
        self._tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.header().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self._tree.doubleClicked.connect(self._on_item_double_clicked)
        layout.addWidget(self._tree, 1)

        # 底部狀態列（統計摘要與防卡死限制說明）
        bot_bar = QHBoxLayout()
        bot_bar.setContentsMargins(4, 2, 4, 0)

        total_files = len(self._entries)
        uncomp_str = _format_size(self._total_uncompressed)
        comp_str = _format_size(self._total_compressed)
        ratio_pct = int(self._total_compressed / max(1, self._total_uncompressed) * 100)

        status_text = f"共 {total_files} 個項目  ·  未壓縮：{uncomp_str}  ·  壓縮後：{comp_str} ({ratio_pct}%)"
        if self._is_truncated:
            status_text += "  ⚠️ (超過 1,000 個檔案已啟用安全截斷以保證流暢)"

        self._lbl_status = QLabel(status_text)
        self._lbl_status.setStyleSheet("color: #a1a1aa; font-size: 11px;")
        bot_bar.addWidget(self._lbl_status)
        bot_bar.addStretch()
        layout.addLayout(bot_bar)

        self._apply_theme()

    def _apply_theme(self) -> None:
        is_dark = settings.is_dark()
        c = get_theme_colors()

        bg = "#121214" if is_dark else "#ffffff"
        item_bg = "#18181b" if is_dark else "#ffffff"
        alt_bg = "#1e1e24" if is_dark else "#f9fafb"
        text_c = "#f3f4f6" if is_dark else "#111827"
        border_c = "rgba(255, 255, 255, 0.08)" if is_dark else "rgba(0, 0, 0, 0.08)"
        header_bg = "#27272a" if is_dark else "#f4f4f5"

        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {'#27272a' if is_dark else '#ffffff'};
                color: {text_c};
                border: 1px solid {border_c};
                border-radius: 6px;
                padding: 4px 10px;
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border: 1px solid #6366f1;
            }}
            QTreeView {{
                background-color: {bg};
                alternate-background-color: {alt_bg};
                color: {text_c};
                border: 1px solid {border_c};
                border-radius: 8px;
                outline: none;
                font-size: 12px;
            }}
            QTreeView::item {{
                height: 26px;
                padding: 2px 4px;
            }}
            QTreeView::item:hover {{
                background-color: {'rgba(99, 102, 241, 0.15)' if is_dark else 'rgba(79, 70, 229, 0.1)'};
            }}
            QTreeView::item:selected {{
                background-color: {'#4f46e5' if is_dark else '#6366f1'};
                color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: {header_bg};
                color: {'#a1a1aa' if is_dark else '#4b5563'};
                font-weight: 600;
                font-size: 11px;
                padding: 4px 8px;
                border: none;
                border-right: 1px solid {border_c};
                border-bottom: 1px solid {border_c};
            }}
        """)

    def _populate_tree(self) -> None:
        """建立階層式 QStandardItem 目錄樹結構。"""
        root_node = self._model.invisibleRootItem()
        dir_map: dict[str, QStandardItem] = {}

        for entry in self._entries:
            raw_path = entry.path.replace("\\", "/").strip("/")
            parts = raw_path.split("/")
            curr_parent = root_node
            accum_path = ""

            for i, part in enumerate(parts):
                accum_path = f"{accum_path}/{part}" if accum_path else part
                is_last = (i == len(parts) - 1)

                if is_last and not entry.is_dir:
                    # 檔案節點
                    ext = Path(part).suffix
                    icon_sym = _get_file_icon_symbol(ext)
                    item_name = QStandardItem(f"{icon_sym}  {part}")
                    item_name.setData(entry.path, Qt.ItemDataRole.UserRole)
                    item_name.setData(False, Qt.ItemDataRole.UserRole + 1)

                    item_size = QStandardItem(_format_size(entry.size))
                    item_size.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    item_comp = QStandardItem(_format_size(entry.compress_size))
                    item_comp.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

                    item_date = QStandardItem(entry.mtime)
                    item_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                    curr_parent.appendRow([item_name, item_size, item_comp, item_date])
                else:
                    # 目錄節點
                    if accum_path not in dir_map:
                        item_dir = QStandardItem(f"📁  {part}")
                        item_dir.setData(accum_path, Qt.ItemDataRole.UserRole)
                        item_dir.setData(True, Qt.ItemDataRole.UserRole + 1)
                        item_dir_size = QStandardItem("—")
                        item_dir_comp = QStandardItem("—")
                        item_dir_date = QStandardItem(entry.mtime if is_last else "—")
                        item_dir_date.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                        curr_parent.appendRow([item_dir, item_dir_size, item_dir_comp, item_dir_date])
                        dir_map[accum_path] = item_dir
                    curr_parent = dir_map[accum_path]

        # 預設自動展開第 1~2 層
        self._tree.expandToDepth(1)

    def _on_search_changed(self, text: str) -> None:
        self._proxy_model.setFilterRegularExpression(text.strip())
        if text.strip():
            self._tree.expandAll()
        else:
            self._tree.collapseAll()
            self._tree.expandToDepth(1)

    def _get_selected_entry_info(self) -> Optional[tuple[str, bool]]:
        indexes = self._tree.selectedIndexes()
        if not indexes:
            return None
        # 轉換為來源模型索引
        src_idx = self._proxy_model.mapToSource(indexes[0])
        item = self._model.itemFromIndex(src_idx)
        if not item:
            return None
        rel_path = item.data(Qt.ItemDataRole.UserRole)
        is_dir = bool(item.data(Qt.ItemDataRole.UserRole + 1))
        return (rel_path, is_dir)

    def _extract_single_file(self, inner_path: str) -> Optional[Path]:
        """解壓單一檔案至系統臨時目錄。"""
        temp_dir = Path(tempfile.gettempdir()) / "KyteView_Extract"
        temp_dir.mkdir(parents=True, exist_ok=True)
        dest_path = temp_dir / Path(inner_path).name

        suffix = self._archive_path.suffix.lower()
        suffixes = "".join(self._archive_path.suffixes).lower()

        try:
            if suffix == ".zip":
                with zipfile.ZipFile(self._archive_path, "r") as zf:
                    with zf.open(inner_path) as source, open(dest_path, "wb") as target:
                        target.write(source.read())
                return dest_path

            elif ".tar" in suffixes or suffix in (".tgz", ".tar"):
                with tarfile.open(self._archive_path, "r:*") as tf:
                    member = tf.getmember(inner_path)
                    extracted = tf.extractfile(member)
                    if extracted:
                        with open(dest_path, "wb") as target:
                            target.write(extracted.read())
                return dest_path

            elif suffix == ".7z":
                import py7zr
                with py7zr.SevenZipFile(self._archive_path, "r") as zf:
                    zf.extract(path=str(temp_dir), targets=[inner_path])
                extracted_file = temp_dir / inner_path
                if extracted_file.exists():
                    return extracted_file
        except Exception as e:
            print(f"[Archive] 單檔解壓失敗: {e}")
            return None

        return None

    def start_drag_extract(self) -> None:
        """單檔拖曳抽出核心：使用者拖動樹狀項目，直接將單檔拖到 Windows 桌面或資料夾。"""
        from core.license import LicenseManager
        if not LicenseManager.get_instance().is_unlimited():
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.information(
                self,
                "專業版專屬功能",
                "「單檔直接拖曳抽出」為 KyteView 專業版專屬功能。\n升級專業版即可直接拖曳壓縮檔內單一檔案至桌面或資料夾，省去整包解壓縮的繁瑣步驟！",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open,
            )
            if reply == QMessageBox.StandardButton.Open:
                from ui.license_dialog import LicenseDialog
                dlg = LicenseDialog(self)
                dlg.exec()
            return

        selected = self._get_selected_entry_info()
        if not selected or selected[1]:  # 是目錄則忽略
            return

        inner_path = selected[0]
        extracted_file = self._extract_single_file(inner_path)
        if not extracted_file or not extracted_file.exists():
            return

        drag = QDrag(self._tree)
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(extracted_file.resolve()))])
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.CopyAction)

    def _on_item_double_clicked(self, index: QModelIndex) -> None:
        """雙擊檔案觸發就地巢狀預覽。"""
        from core.license import LicenseManager
        if not LicenseManager.get_instance().is_unlimited():
            from PySide6.QtWidgets import QMessageBox
            reply = QMessageBox.information(
                self,
                "專業版專屬功能",
                "壓縮包「巢狀就地預覽」為 KyteView 專業版專屬功能。\n升級專業版即可就地檢視壓縮包內部的文字、代碼與圖片，並可一鍵返回目錄樹！",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Open,
            )
            if reply == QMessageBox.StandardButton.Open:
                from ui.license_dialog import LicenseDialog
                dlg = LicenseDialog(self)
                dlg.exec()
            return

        selected = self._get_selected_entry_info()
        if not selected or selected[1]:
            return
        inner_path = selected[0]
        extracted_file = self._extract_single_file(inner_path)
        if extracted_file and extracted_file.exists():
            self.open_nested_file.emit(extracted_file)


class ArchiveRenderer(BaseRenderer):
    """壓縮檔案全能預覽渲染器。"""
    def __init__(self) -> None:
        self._current_widget: Optional[ArchiveBrowserWidget] = None

    def render(self, path: Path) -> QWidget:
        self._current_widget = ArchiveBrowserWidget(path)
        return self._current_widget

    def cleanup(self) -> None:
        self._current_widget = None
