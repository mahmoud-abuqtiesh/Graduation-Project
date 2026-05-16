import ctypes
from ctypes import wintypes
from typing import Tuple

from src.cursor.base import Cursor

user32 = ctypes.WinDLL("user32", use_last_error=True)

SM_XVIRTUALSCREEN = 76
SM_YVIRTUALSCREEN = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

INPUT_MOUSE = 0

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_WHEEL = 0x0800
MOUSEEVENTF_VIRTUALDESK = 0x4000
MOUSEEVENTF_ABSOLUTE = 0x8000

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", ctypes.c_long),
        ("dy", ctypes.c_long),
        ("mouseData", ctypes.c_ulong),
        ("dwFlags", ctypes.c_ulong),
        ("time", ctypes.c_ulong),
        ("dwExtraInfo", ctypes.c_void_p),
    ]

class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", ctypes.c_ulong), ("u", _INPUT_UNION)]

user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

def _send_mouse(dx: int, dy: int, mouse_data: int, flags: int) -> None:
    inp = INPUT()
    inp.type = INPUT_MOUSE
    inp.u.mi.dx = int(dx)
    inp.u.mi.dy = int(dy)
    inp.u.mi.mouseData = int(mouse_data) & 0xFFFFFFFF
    inp.u.mi.dwFlags = int(flags)
    inp.u.mi.time = 0
    inp.u.mi.dwExtraInfo = None
    user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(INPUT))

class WindowsCursor(Cursor):
    def get_pos(self) -> Tuple[int, int]:
        pt = POINT()
        user32.GetCursorPos(ctypes.byref(pt))
        return pt.x, pt.y

    def set_pos(self, x: int, y: int) -> None:
        minx, miny, maxx, maxy = self.get_virtual_bounds()
        w = max(1, maxx - minx + 1)
        h = max(1, maxy - miny + 1)
        rel_x = max(0, min(w - 1, int(x) - minx))
        rel_y = max(0, min(h - 1, int(y) - miny))
        norm_x = (rel_x * 65535) // max(1, w - 1)
        norm_y = (rel_y * 65535) // max(1, h - 1)
        _send_mouse(
            norm_x,
            norm_y,
            0,
            MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
        )

    def get_virtual_bounds(self) -> Tuple[int, int, int, int]:
        minx = user32.GetSystemMetrics(SM_XVIRTUALSCREEN)
        miny = user32.GetSystemMetrics(SM_YVIRTUALSCREEN)
        w = user32.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        h = user32.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        maxx = minx + w - 1
        maxy = miny + h - 1
        return minx, miny, maxx, maxy

    def left_click(self) -> None:
        self.left_down()
        self.left_up()

    def left_down(self) -> None:
        _send_mouse(0, 0, 0, MOUSEEVENTF_LEFTDOWN)

    def left_up(self) -> None:
        _send_mouse(0, 0, 0, MOUSEEVENTF_LEFTUP)

    def right_click(self) -> None:
        self.right_down()
        self.right_up()

    def right_down(self) -> None:
        _send_mouse(0, 0, 0, MOUSEEVENTF_RIGHTDOWN)

    def right_up(self) -> None:
        _send_mouse(0, 0, 0, MOUSEEVENTF_RIGHTUP)

    def scroll(self, delta: int) -> None:
        _send_mouse(0, 0, int(delta), MOUSEEVENTF_WHEEL)
