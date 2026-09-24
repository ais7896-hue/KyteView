# KyteView — Windows 極速空白鍵預覽器 計劃書

## 專案定位

macOS QuickLook 的 Windows 精緻復刻，但功能超越原版：語法高亮、表格解析、音訊波形、字型預覽一體整合。

**核心效能目標：Space 按下後 50～100ms 內彈出視窗，常駐記憶體 < 50MB。**

---

## 技術選型

| 層級         | 技術                                                  | 理由                                                                                                                      |
| ------------ | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- |
| GUI 框架     | **PySide6**                                     | Qt 原生效能、無 Chromium 常駐負擔                                                                                         |
| 全域熱鍵監聽 | **`ctypes SetWindowsHookEx(WH_KEYBOARD_LL)`** | 可真正吞噬 Space 事件（return 1）；pynput 無法乾淨 Suppress，會觸發 Explorer 原生捲軸行為                                 |
| 檔案總管整合 | **pywin32 (win32api)**                          | 取得當前選取檔案路徑，含桌面 Progman 特例處理                                                                             |
| 語法高亮     | **Pygments + QTextBrowser**                     | `HtmlFormatter` 產出 HTML → `setHtml()` 直接渲染；QPlainTextEdit 不吃 HTML，QTextBrowser 唯讀預覽最省事；打包僅 +5MB |
| 表格解析     | **csv 模組（CSV）+ python-calamine（XLSX）**    | 零依賴 CSV；calamine 為 Rust 實作，比 openpyxl 快 10-50x；捨棄 pandas+openpyxl                                            |
| 影像/SVG     | Qt 原生 QPixmap / QSvgWidget                          | 零依賴                                                                                                                    |
| 音訊波形     | **`wave` / `miniaudio` + Qt QPainter**      | 純 Python 峰值抽樣繪製柱狀波形，載入 < 10ms；捨棄 librosa+matplotlib（+300MB+，import 需 1.5s）                           |
| 字型預覽     | **freetype-py** 或 Qt QFont                     | 渲染字型樣本                                                                                                              |
| 打包         | **PyInstaller** + NSIS installer                | 單執行檔分發                                                                                                              |

---

## 架構設計

```
KyteView/
├── main.py                  # 入口：系統托盤 + 全域監聽
├── core/
│   ├── file_watcher.py      # 偵測 Explorer 選取的檔案（回傳 List[Path]，支援多選）
│   ├── hotkey_listener.py   # 全域 Space 鍵監聽
│   ├── preview_router.py    # 根據副檔名路由到對應 renderer
│   └── render_cache.py      # LRU 快取（key: 檔案路徑+mtime，避免重複渲染）
├── renderers/
│   ├── base.py              # 抽象 Renderer 介面
│   ├── code_renderer.py     # 程式碼 (.py .js .ts .json .yaml .toml .xml...)
│   ├── table_renderer.py    # 表格 (.csv .xlsx .xls)
│   ├── image_renderer.py    # 圖片 (.png .jpg .gif .webp .svg .ico)
│   ├── audio_renderer.py    # 音訊 (.mp3 .wav .flac .ogg)
│   ├── video_renderer.py    # 影片 (.mp4 .mkv .avi .mov)（QMediaPlayer + QVideoWidget）
│   ├── font_renderer.py     # 字型 (.ttf .otf .woff)
│   ├── pdf_renderer.py      # PDF（用 pymupdf/fitz）
│   ├── text_renderer.py     # 純文字 fallback
│   ├── archive_renderer.py  # 壓縮檔 (.zip .7z .rar .tar.gz)，顯示檔案樹
│   └── markdown_renderer.py # Markdown 預覽
├── ui/
│   ├── preview_window.py    # 主視窗（無邊框、毛玻璃效果）
│   ├── toolbar.py           # 頂部工具列（複製、開啟、縮放）
│   └── assets/              # 靜態資源（CSS 主題等）
├── config/
│   └── settings.py          # 使用者設定（主題、視窗大小等）
└── requirements.txt
```

---

## 分階段開發計劃

### Phase 1 — 骨架 + 核心機制（1-2天）

**目標：按 Space 能彈出視窗，顯示純文字**

- [ ] 系統托盤常駐程式（PySide6 QSystemTrayIcon）
- [ ] 全域 Space 熱鍵監聽（`ctypes WH_KEYBOARD_LL`）：條件成立時 return 1 **吞噬**事件；條件不成立時 `CallNextHookEx` 放行。**不用 pynput**（無法 Suppress，會觸發 Explorer 捲軸）
- [ ] **二次 Space 關閉**：視窗顯示中再按 Space → `preview_window.hide()` + `return 1`（吞噬）
- [ ] **方向鍵即時切換**：視窗顯示中按上/下/左/右 → 更新 Explorer 選取並刷新預覽（視窗不關閉）
- [ ] 取得 Explorer 當前選取檔案（win32api COM 自動化，回傳 `List[Path]`）
- [ ] 無邊框浮動視窗（含 ESC 關閉、拖曳移動）
- [ ] 基本 fallback 純文字渲染
- [ ] render_cache.py：LRU 快取渲染結果，key = `(path, mtime)`

**關鍵技術點：**

```python
# 取得 Explorer 選取檔案
import win32com.client
shell = win32com.client.Dispatch("Shell.Application")
for window in shell.Windows():
    if "explorer" in window.FullName.lower():
        selected = window.Document.SelectedItems()
        return [item.Path for item in selected]
```

---

### Phase 2 — 主力 Renderer（3-5天）

**程式碼渲染器（最高優先）**

- **Pygments `HtmlFormatter`** 產出帶樣式 HTML → **`QTextBrowser.setHtml()`** 渲染（唯讀預覽，自帶顏色，一鍵複製）
- ⚠️ 注意：`QPlainTextEdit` 不吃 HTML；`QTextEdit` 可以但效能較差；唯讀場景用 `QTextBrowser` 最省事
- 支援 500+ 語言，啟動幾乎零延遲，打包僅 +5MB
- 深色/淺色主題：切換 `HtmlFormatter(style='monokai'/'default')`
- ⚠️ 若未來需要 CodeMirror 等 Web 渲染：改用 **pywebview + WebView2**（呼叫系統 Edge 核心，免打包 Chromium，體積小 90%）

**表格渲染器**

- CSV：Python 內建 **`csv` 模組**逐行讀取前 500 行，零依賴
- XLSX：**`python-calamine`**（Rust 實作），速度比 openpyxl 快 10-50x，記憶體極小
- 虛擬滾動（QTableView + QAbstractTableModel，不一次塞入 DOM）
- 凍結首列、欄寬自動調整，顯示「前 N 行，共 X 行」統計

**圖片渲染器**

- Qt 原生 QPixmap（PNG/JPG/GIF/WEBP）
- QSvgWidget（SVG）
- 縮放、100% 實際大小、適合視窗

---

### Phase 3 — 進階 Renderer（3-5天）

**音訊渲染器**

- **`wave`（WAV）/ `miniaudio`（MP3/FLAC/OGG）** 讀取音訊峰值資料
- 用 **Qt QPainter** 繪製柱狀波形（類 SoundCloud 風格），載入 < 10ms
- QMediaPlayer 播放（含播放/暫停控制）
- 顯示：時長、取樣率、位元率
- ❌ 不使用 librosa（import 耗時 1.5-3s，打包 +300MB）

**字型渲染器**

- freetype-py 渲染字型樣本字串
- 顯示：字型名稱、風格、字元集覆蓋

**PDF 渲染器**

- pymupdf (fitz) 渲染頁面為圖片
- 多頁翻頁

**Markdown 渲染器**

- markdown-it-py 轉 HTML → **`QTextBrowser.setHtml()`** 渲染（同 code_renderer 路徑，統一用 QTextBrowser）
- GitHub 風格樣式（內嵌 CSS）

---

### Phase 4 — UX 打磨（2天）

- [ ] 視窗動畫（淡入 + 輕微縮放）
- [ ] 毛玻璃/Acrylic 效果（Windows 11 DWM）
- [ ] 多檔案切換（`file_watcher` 回傳 `List[Path]`，Preview 視窗維護當前 index，左右箭頭切換）
- [ ] 設定頁面（主題、字體大小、預覽視窗大小）
- [ ] 檔案資訊側邊欄（大小、修改日期、MIME 類型）

---

### Phase 5 — 打包與分發（1天）

- [ ] PyInstaller 打包成單一 .exe
- [ ] NSIS 製作安裝程式（自動加入開機啟動登錄）
- [ ] GitHub Actions CI 自動打包

---

## 格式支援矩陣

| 類別     | 格式                                                                                                      | Renderer          | 特色功能                   |
| -------- | --------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------- |
| 程式碼   | .py .js .ts .go .rs .java .c .cpp .cs .php .rb .swift .kt .json .yaml .toml .xml .html .css .sql .sh .ps1 | code_renderer     | 語法高亮、行號、折疊、複製 |
| 表格     | .csv .xlsx .xls .tsv                                                                                      | table_renderer    | 虛擬滾動、統計資訊         |
| 圖片     | .png .jpg .jpeg .gif .webp .bmp .ico .svg .tiff                                                           | image_renderer    | 縮放、EXIF 資訊            |
| 文件     | .pdf                                                                                                      | pdf_renderer      | 多頁翻頁                   |
| Markdown | .md .mdx .rst                                                                                             | markdown_renderer | GitHub 樣式渲染            |
| 音訊     | .mp3 .wav .flac .ogg .aac .m4a                                                                            | audio_renderer    | 波形、播放控制             |
| 影片     | .mp4 .mkv .avi .mov .webm                                                                                 | video_renderer    | 縮圖+播放                  |
| 字型     | .ttf .otf .woff .woff2                                                                                    | font_renderer     | 字型樣本預覽               |
| 純文字   | .txt .log .env .cfg .ini                                                                                  | text_renderer     | 大檔案分頁                 |
| 壓縮檔   | .zip .7z .rar .tar.gz                                                                                     | archive_renderer  | 檔案樹列表                 |

---

## 潛在技術難點與解法

### 1. Space 鍵攔截：必須用 `WH_KEYBOARD_LL` 吞噬事件

**pynput 的致命問題**：pynput 以「監聽」為主，無法在 Windows 底層乾淨地 Suppress Space 鍵。若用 pynput，按 Space 彈出預覽的同時，Explorer 仍會收到 Space 事件（反選檔案、捲軸往下滾一頁）。

**正確做法：`ctypes SetWindowsHookEx(WH_KEYBOARD_LL)`**

```python
import ctypes, ctypes.wintypes, win32gui

def low_level_handler(nCode, wParam, lParam):
    if nCode >= 0 and wParam == WM_KEYDOWN:
        vk = lParam.contents.vkCode

        # Space：開啟或關閉預覽
        if vk == VK_SPACE:
            if preview_window.isVisible():
                preview_window.hide()      # 二次 Space → 關閉
                return 1                   # 吞噬
            hwnd = win32gui.GetForegroundWindow()
            if is_explorer(hwnd) and not has_edit_focus(hwnd):
                trigger_preview()          # 首次 Space → 彈出
                return 1                   # 吞噬

        # 方向鍵：視窗開啟中即時切換檔案，視窗不關閉
        if vk in (VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT):
            if preview_window.isVisible():
                # 讓 Explorer 先處理選取變更（放行事件）
                result = ctypes.windll.user32.CallNextHookEx(hook, nCode, wParam, lParam)
                QTimer.singleShot(50, refresh_preview)  # 50ms 後重新取得選取並刷新
                return result

    return ctypes.windll.user32.CallNextHookEx(hook, nCode, wParam, lParam)
```

- 條件成立 → `return 1`（吞噬）
- 條件不成立 → `CallNextHookEx`（放行）

**`has_edit_focus` 判定**：用 `GetGUIThreadInfo` 確認焦點是否在 Edit/RichEdit 控制項，涵蓋 F2 重命名、路徑列、搜尋列等場景。

### 2. Explorer 選取檔案 COM 效能優化

**問題**：若使用者開了 8 個資料夾視窗，遍歷所有 `shell.Windows()` 並逐一檢查 `FullName`，偶爾產生 20~50ms COM IPC 延遲。

**優化：先拿 hwnd，對中立刻 break**

```python
hwnd = win32gui.GetForegroundWindow()  # 當前焦點視窗
shell = win32com.client.Dispatch("Shell.Application")
for window in shell.Windows():
    if window.HWND == hwnd:            # 直接比對，不用看 FullName
        selected = window.Document.SelectedItems()
        return [item.Path for item in selected]
        break                          # 找到立刻停止，不繼續遍歷
```

**桌面死角**：桌面不是一般 Explorer 視窗，而是 `Progman` → `WorkerW` → `SHELLDLL_DefView`，需透過 `IShellWindows` 特殊處理或指向 `CSIDL_DESKTOP`

- Fallback：讀剪貼簿路徑（Ctrl+C 複製路徑）

### 3. 多螢幕彈出位置

- 彈出預覽視窗前，先用 `QCursor.pos()` 取得游標所在螢幕
- 用 `QApplication.screenAt(cursor_pos)` 確認目標螢幕，避免在副螢幕按 Space 卻彈到主螢幕

### 4. 大型 CSV/Excel 不卡頓

- CSV：`csv` 模組逐行讀取前 500 行，顯示「前 500 行，共 N 行」
- XLSX：`python-calamine` 串流讀取，速度比 openpyxl 快 10-50x
- 表格用 QTableView + QAbstractTableModel（虛擬化，不一次塞進 DOM）

### 5. Windows 11 毛玻璃效果

```python
import ctypes
# 呼叫 DwmSetWindowAttribute 啟用 Acrylic/Mica 材質
DWMWA_SYSTEMBACKDROP_TYPE = 38
ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ...)
```

---

## 依賴清單

> 精簡原則：零資料科學庫，全部換成桌面專用輕量武器。

```txt
# 核心框架與系統整合
PySide6>=6.7.0
# ctypes 內建，無需額外安裝（WH_KEYBOARD_LL 熱鍵）
pywin32>=306

# 文字與程式碼渲染（極輕量，啟動 < 20ms）
Pygments>=2.17.0       # 語法高亮（替代 QWebEngine+CodeMirror，打包僅 +5MB）
markdown-it-py>=3.0    # Markdown 轉 HTML（配合 QTextBrowser）

# 表格解析
python-calamine>=0.2   # Rust 極速讀 Excel（替代 pandas+openpyxl）
# csv 模組：Python 內建，零依賴

# 多媒體
pymupdf>=1.24.0        # PDF 渲染（極快）
miniaudio>=1.58        # 音訊峰值讀取（替代 librosa，無重型依賴）
Pillow>=10.3.0         # 圖片輔助（EXIF 等）
freetype-py>=2.4       # 字型預覽

# 壓縮檔
py7zr>=0.21.0          # 7z/zip 解析

# ❌ 已移除：keyboard, pandas, openpyxl, librosa, matplotlib
```

---

## 開發順序建議

```
Phase 1 (骨架) → Phase 2 程式碼渲染 → Phase 2 表格渲染 → Phase 2 圖片渲染
→ Phase 3 依需求優先度 → Phase 4 UX → Phase 5 打包
```

> 建議先跑通 Phase 1+2，就已經是 80% 日常使用需求。Phase 3 可以邊用邊補。
