"""
renderers/table_renderer.py
極速表格渲染器：
- CSV / TSV：內建 csv 模組串流解析
- XLSX / XLS：Rust 實作的 python-calamine（速度極快、記憶體極小）
- QTableView + QAbstractTableModel 虛擬滾動
- 支援 Sheet 切換（XLSX）與統計列
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from renderers.base import BaseRenderer

MAX_TABLE_ROWS = 500
MAX_TABLE_COLS = 50


class _TableModel(QAbstractTableModel):
    def __init__(self, headers: list[str], rows: list[list[Any]]):
        super().__init__()
        self._headers = headers
        self._rows = rows

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            val = self._rows[index.row()][index.column()]
            if val is None:
                return ""
            return str(val)
        elif role == Qt.ItemDataRole.TextAlignmentRole:
            return Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
        return None

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ) -> Any:
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section < len(self._headers):
                    return self._headers[section]
                return f"Col {section + 1}"
            else:
                return str(section + 1)
        return None


class TableRenderer(BaseRenderer):
    def render(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        suffix = path.suffix.lower()

        try:
            if suffix in (".xlsx", ".xls"):
                widget = self._render_excel(path)
            else:
                widget = self._render_csv(path)
            layout.addWidget(widget)
        except Exception as e:
            err_label = QLabel(f"⚠️ 無法讀取表格內容\n{e}")
            err_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            err_label.setStyleSheet("color: #ff6b6b; font-size: 13px;")
            layout.addWidget(err_label)

        return container

    def _render_csv(self, path: Path) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        encoding, delimiter = self._detect_csv_format(path)

        rows: list[list[str]] = []
        try:
            with path.open("r", encoding=encoding, errors="replace", newline="") as f:
                reader = csv.reader(f, delimiter=delimiter)
                for row in reader:
                    # 過濾空行
                    if not any(cell.strip() for cell in row):
                        continue
                    if len(rows) >= MAX_TABLE_ROWS:
                        break
                    rows.append([c.strip() for c in row[:MAX_TABLE_COLS]])
        except Exception as e:
            return QLabel(f"無法解析 CSV 檔案: {e}")

        if not rows:
            return QLabel("空白表格或無法讀取")

        # 首列作為表頭，其餘為數據
        headers = [f"Col {j + 1}" if not col else col for j, col in enumerate(rows[0])]
        data_rows = rows[1:]

        # 補齊各列長度
        max_col = len(headers)
        for r in data_rows:
            if len(r) < max_col:
                r.extend([""] * (max_col - len(r)))
            elif len(r) > max_col:
                for j in range(max_col, len(r)):
                    headers.append(f"Col {j + 1}")
                max_col = len(r)

        table_view = self._create_table_view(headers, data_rows)
        layout.addWidget(table_view)

        # 底部統計
        stat = QLabel(
            f"編碼: {encoding.upper()} · 分隔符: '{delimiter}' · 預覽 {len(data_rows)} 列 · 共 {max_col} 欄"
        )
        stat.setStyleSheet("color: #777; font-size: 11px; padding: 2px 4px;")
        layout.addWidget(stat)

        return container

    def _detect_csv_format(self, path: Path) -> tuple[str, str]:
        """精準探測 CSV 的編碼與分隔符號（支援 UTF-16LE/BE、BOM、Sniffer）。"""
        delimiter = "\t" if path.suffix.lower() == ".tsv" else ","

        with path.open("rb") as f:
            raw = f.read(4096)

        if not raw:
            return "utf-8", delimiter

        # 1. 優先檢查 BOM
        if raw.startswith(b"\xff\xfe"):
            encoding = "utf-16-le"
        elif raw.startswith(b"\xfe\xff"):
            encoding = "utf-16-be"
        elif raw.startswith(b"\xef\xbb\xbf"):
            encoding = "utf-8-sig"
        # 2. 檢查是否有 UTF-16 常見的交替 null-byte
        elif len(raw) >= 4 and (raw[1::2].count(0) > len(raw) // 4 or raw[0::2].count(0) > len(raw) // 4):
            encoding = "utf-16"
        else:
            # 3. 嘗試常見中英文編碼
            encoding = "utf-8"
            for enc in ("utf-8", "cp950", "big5", "gbk"):
                try:
                    raw.decode(enc)
                    encoding = enc
                    break
                except UnicodeDecodeError:
                    continue

        # 4. 探測分隔符號
        try:
            text_sample = raw.decode(encoding, errors="ignore")[:2048]
            lines = [l for l in text_sample.splitlines() if l.strip()]
            if lines and path.suffix.lower() != ".tsv":
                sample = "\n".join(lines[:5])
                sniffed = csv.Sniffer().sniff(sample, delimiters=",\t;|")
                delimiter = sniffed.delimiter
        except Exception:
            pass

        return encoding, delimiter

    def _render_excel(self, path: Path) -> QWidget:
        import python_calamine

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        wb = python_calamine.CalamineWorkbook.from_path(str(path))
        sheet_names = wb.sheet_names

        if not sheet_names:
            return QLabel("Excel 活頁簿中無工作表")

        # 頂部工作表切換器
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("工作表:"))
        sheet_combo = QComboBox()
        sheet_combo.addItems(sheet_names)
        sheet_combo.setStyleSheet("""
            QComboBox {
                background: #252528;
                color: #e0e0e0;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 4px;
                padding: 2px 8px;
                font-size: 12px;
            }
            QComboBox QAbstractItemView {
                background: #202022;
                color: #e0e0e0;
                selection-background-color: #3b3b40;
            }
        """)
        top_bar.addWidget(sheet_combo)
        top_bar.addStretch()
        layout.addLayout(top_bar)

        content_layout = QVBoxLayout()
        layout.addLayout(content_layout)

        def switch_sheet(idx: int):
            while content_layout.count():
                item = content_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            sheet = wb.get_sheet_by_index(idx)
            raw_data = sheet.to_python()
            if not raw_data:
                content_layout.addWidget(QLabel("此工作表為空"))
                return

            preview_data = raw_data[:MAX_TABLE_ROWS]
            first_row = preview_data[0]
            headers = [
                str(c) if c is not None and str(c).strip() else f"Col {j + 1}"
                for j, c in enumerate(first_row)
            ]
            rows = preview_data[1:]

            max_col = len(headers)
            for r in rows:
                if len(r) < max_col:
                    r.extend([""] * (max_col - len(r)))

            t_view = self._create_table_view(headers, rows)
            content_layout.addWidget(t_view)

            info = QLabel(
                f"工作表: {sheet.name} · 預覽 {len(rows)} 列 · 共 {max_col} 欄 (總行數: {sheet.total_height})"
            )
            info.setStyleSheet("color: #777; font-size: 11px; padding: 2px 4px;")
            content_layout.addWidget(info)

        sheet_combo.currentIndexChanged.connect(switch_sheet)
        switch_sheet(0)

        return container

    def _create_table_view(
        self, headers: list[str], rows: list[list[Any]]
    ) -> QTableView:
        from config.theme import get_theme_colors
        c = get_theme_colors()

        table = QTableView()
        model = _TableModel(headers, rows)
        table.setModel(model)

        table.setFrameShape(QTableView.Shape.NoFrame)
        table.setAlternatingRowColors(True)
        table.setShowGrid(True)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        table.verticalHeader().setDefaultSectionSize(26)
        table.horizontalHeader().setDefaultSectionSize(110)

        table.setStyleSheet(f"""
            QTableView {{
                background: {c['table_bg']};
                alternate-background-color: {c['table_alt_bg']};
                color: {c['table_text']};
                gridline-color: {c['table_grid']};
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 6px;
                font-family: 'Segoe UI', sans-serif;
                font-size: 12px;
                selection-background-color: {c['table_select_bg']};
            }}
            QHeaderView::section {{
                background: {c['table_header_bg']};
                color: {c['table_header_text']};
                padding: 4px 8px;
                border: none;
                border-right: 1px solid {c['table_grid']};
                border-bottom: 1px solid {c['table_grid']};
                font-weight: 600;
                font-size: 11px;
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: transparent;
                width: 8px;
                height: 8px;
            }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: rgba(128, 128, 128, 0.25);
                border-radius: 4px;
            }}
        """)

        return table
