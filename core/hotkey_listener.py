"""
core/hotkey_listener.py
全域 Space 熱鍵監聽，使用 ctypes WH_KEYBOARD_LL。

行為：
- 前景為 Explorer 且無輸入框焦點：
    - 視窗未開：彈出預覽，吞噬 Space
    - 視窗已開：關閉預覽，吞噬 Space
- 視窗開啟中按方向鍵：放行給 Explorer，50ms 後刷新預覽
- 其他情況：CallNextHookEx 放行
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import threading
from typing import Callable, Optional

import win32gui
import win32con
import win32process

# ── Windows API 常數 ──────────────────────────────────────────────────────────
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

VK_TAB = 0x09
VK_SPACE = 0x20
VK_ESCAPE = 0x1B
VK_UP = 0x26
VK_DOWN = 0x28
VK_LEFT = 0x25
VK_RIGHT = 0x27
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt key

# ── ctypes 結構 ───────────────────────────────────────────────────────────────
class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


HOOKPROC = ctypes.CFUNCTYPE(
    ctypes.c_long, ctypes.c_int, ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
)

# 64-bit 修正：必須設 restype，否則 HHOOK 被截斷成 0
_user32 = ctypes.windll.user32
_user32.SetWindowsHookExW.restype = ctypes.c_void_p
_user32.CallNextHookEx.restype    = ctypes.c_long
_user32.CallNextHookEx.argtypes   = [
    ctypes.c_void_p, ctypes.c_int,
    ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM,
]
_user32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]


def _has_edit_focus(hwnd: int) -> bool:
    """
    用 GetGUIThreadInfo 確認焦點是否在 Edit/RichEdit 控制項。
    涵蓋 F2 重命名、路徑列、搜尋列等輸入場景。
    """
    class GUITHREADINFO(ctypes.Structure):
        _fields_ = [
            ("cbSize", ctypes.wintypes.DWORD),
            ("flags", ctypes.wintypes.DWORD),
            ("hwndActive", ctypes.wintypes.HWND),
            ("hwndFocus", ctypes.wintypes.HWND),
            ("hwndCapture", ctypes.wintypes.HWND),
            ("hwndMenuOwner", ctypes.wintypes.HWND),
            ("hwndMoveSize", ctypes.wintypes.HWND),
            ("hwndCaret", ctypes.wintypes.HWND),
            ("rcCaret", ctypes.wintypes.RECT),
        ]

    tid = win32process.GetWindowThreadProcessId(hwnd)[0]
    info = GUITHREADINFO(cbSize=ctypes.sizeof(GUITHREADINFO))
    if ctypes.windll.user32.GetGUIThreadInfo(tid, ctypes.byref(info)):
        focus_hwnd = info.hwndFocus
        if focus_hwnd:
            cls = win32gui.GetClassName(focus_hwnd)
            return cls in ("Edit", "RichEdit", "RichEdit20W", "RICHEDIT50W",
                           "SearchBox", "NetUIHWND")
    return False


class HotkeyListener:
    """
    全域鍵盤 Hook，管理 Space / ESC / 方向鍵的攔截邏輯。
    使用方式：
        listener = HotkeyListener(
            on_open=lambda paths: ...,
            on_close=lambda: ...,
            on_navigate=lambda direction: ...,
            is_preview_visible=lambda: bool,
            is_explorer=lambda hwnd: bool,
        )
        listener.start()
        ...
        listener.stop()
    """

    def __init__(
        self,
        on_open: Callable[[list], None],
        on_close: Callable[[], None],
        on_navigate: Callable[[str], None],   # 'up'|'down'|'left'|'right'
        on_peek: Callable[[bool], None],      # True: semi-transparent, False: solid
        on_toggle_pin: Callable[[], None],    # Toggle split/side-dock mode
        is_preview_visible: Callable[[], bool],
        is_explorer: Callable[[int], bool],
    ):
        self._on_open = on_open
        self._on_close = on_close
        self._on_navigate = on_navigate
        self._on_peek = on_peek
        self._on_toggle_pin = on_toggle_pin
        self._is_preview_visible = is_preview_visible
        self._is_explorer = is_explorer

        self._hook: Optional[int] = None
        self._hook_proc: Optional[HOOKPROC] = None
        self._thread: Optional[threading.Thread] = None

    def _handler(
        self, nCode: int, wParam: int, lParam: int
    ) -> int:
        if nCode >= 0:
            kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
            vk = kb.vkCode

            # ── 暫時半透明「透視」機制 (Peek Through: Alt / Ctrl 按住微透) ─────
            # 涵蓋 VK_MENU(0x12), VK_LMENU(0xA4), VK_RMENU(0xA5), VK_CONTROL(0x11), VK_LCONTROL(0xA2), VK_RCONTROL(0xA3)
            if vk in (0x11, 0x12, 0xA2, 0xA3, 0xA4, 0xA5):
                if self._is_preview_visible():
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        self._on_peek(True)
                    elif wParam in (WM_KEYUP, WM_SYSKEYUP):
                        self._on_peek(False)

            if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                # ── Space ─────────────────────────────────────────────────────────
                if vk == VK_SPACE:
                    try:
                        if self._is_preview_visible():
                            self._on_close()
                            return 1  # 吞噬

                        hwnd = win32gui.GetForegroundWindow()
                        if self._is_explorer(hwnd) and not _has_edit_focus(hwnd):
                            self._on_open(hwnd)
                            return 1  # 吞噬
                    except Exception:
                        pass

                # ── ESC ───────────────────────────────────────────────────────────
                elif vk == VK_ESCAPE:
                    if self._is_preview_visible():
                        self._on_close()
                        return 1  # 吞噬

                # ── Tab: 快速側邊釘選切換 ──────────────────────────────────────────
                elif vk == VK_TAB:
                    if self._is_preview_visible():
                        self._on_toggle_pin()
                        return 1  # 吞噬

                # ── 方向鍵：放行給 Explorer，再通知刷新 ──────────────────────────
                elif vk in (VK_UP, VK_DOWN, VK_LEFT, VK_RIGHT):
                    if self._is_preview_visible():
                        direction = {
                            VK_UP: "up", VK_DOWN: "down",
                            VK_LEFT: "left", VK_RIGHT: "right",
                        }[vk]
                        result = ctypes.windll.user32.CallNextHookEx(
                            self._hook, nCode, wParam, lParam
                        )
                        self._on_navigate(direction)
                        return result

        return ctypes.windll.user32.CallNextHookEx(
            self._hook, nCode, wParam, lParam
        )

    def start(self) -> None:
        """在獨立執行緒中啟動訊息迴圈。"""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        self._hook_proc = HOOKPROC(self._handler)
        self._hook = _user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc,
            None,  # hMod=None for LL hooks（不需要 DLL）
            0,
        )
        # 訊息迴圈（Hook 需要訊息幫浦）
        msg = ctypes.wintypes.MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

    def stop(self) -> None:
        if self._hook:
            _user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        if self._thread and self._thread.is_alive():
            _user32.PostThreadMessageW(
                self._thread.ident, 0x0012, 0, 0  # WM_QUIT
            )
