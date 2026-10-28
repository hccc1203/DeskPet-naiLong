#!/usr/bin/env python3
"""把 X11 窗口移出任务栏 / Dock。

Electron 的 skipTaskbar 选项仅在 macOS 与 Windows 生效，Linux 下需要按
EWMH 规范向窗口管理器发送 _NET_WM_STATE 客户端消息。
"""
import ctypes
import ctypes.util
import sys


def send_skip_taskbar(x11, display, root, window_id: int) -> bool:
    atom_state = x11.XInternAtom(display, b"_NET_WM_STATE", 0)
    atom_skip_taskbar = x11.XInternAtom(
        display, b"_NET_WM_STATE_SKIP_TASKBAR", 0
    )
    atom_skip_pager = x11.XInternAtom(display, b"_NET_WM_STATE_SKIP_PAGER", 0)

    class ClientMessage(ctypes.Structure):
        _fields_ = [
            ("type", ctypes.c_int),
            ("serial", ctypes.c_ulong),
            ("send_event", ctypes.c_int),
            ("display", ctypes.c_void_p),
            ("window", ctypes.c_ulong),
            ("message_type", ctypes.c_ulong),
            ("format", ctypes.c_int),
            ("data", ctypes.c_long * 5),
        ]

    class XEvent(ctypes.Union):
        _fields_ = [("xclient", ClientMessage), ("pad", ctypes.c_long * 24)]

    event = XEvent()
    event.xclient.type = 33  # ClientMessage
    event.xclient.serial = 0
    event.xclient.send_event = 1
    event.xclient.display = display
    event.xclient.window = window_id
    event.xclient.message_type = atom_state
    event.xclient.format = 32
    event.xclient.data[0] = 1  # _NET_WM_STATE_ADD
    event.xclient.data[1] = atom_skip_taskbar
    event.xclient.data[2] = atom_skip_pager
    event.xclient.data[3] = 1  # 来源：应用
    event.xclient.data[4] = 0

    mask = 0x00100000 | 0x00080000  # SubstructureRedirect | SubstructureNotify
    return bool(x11.XSendEvent(display, root, 0, mask, ctypes.byref(event)))


def main() -> int:
    if len(sys.argv) < 2:
        print(f"用法：{sys.argv[0]} <x11-window-id> [...]", file=sys.stderr)
        return 2

    window_ids = []
    for value in sys.argv[1:]:
        try:
            window_ids.append(int(value, 0))
        except ValueError:
            print(f"无效的窗口 ID：{value}", file=sys.stderr)
            return 2

    libx11 = ctypes.util.find_library("X11")
    if not libx11:
        print("未找到 libX11", file=sys.stderr)
        return 1

    x11 = ctypes.CDLL(libx11)
    x11.XOpenDisplay.restype = ctypes.c_void_p
    x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
    x11.XInternAtom.restype = ctypes.c_ulong
    x11.XInternAtom.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_int]
    x11.XDefaultRootWindow.restype = ctypes.c_ulong
    x11.XDefaultRootWindow.argtypes = [ctypes.c_void_p]
    x11.XSendEvent.restype = ctypes.c_int
    x11.XSendEvent.argtypes = [
        ctypes.c_void_p,
        ctypes.c_ulong,
        ctypes.c_int,
        ctypes.c_long,
        ctypes.c_void_p,
    ]
    x11.XFlush.argtypes = [ctypes.c_void_p]
    x11.XCloseDisplay.argtypes = [ctypes.c_void_p]

    display = x11.XOpenDisplay(None)
    if not display:
        print("无法打开 X display", file=sys.stderr)
        return 1

    root = x11.XDefaultRootWindow(display)
    success = True
    for window_id in window_ids:
        if not send_skip_taskbar(x11, display, root, window_id):
            print(f"窗口 {window_id:#x} 处理失败", file=sys.stderr)
            success = False

    x11.XFlush(display)
    x11.XCloseDisplay(display)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
