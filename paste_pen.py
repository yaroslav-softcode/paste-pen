import sys
import math
import random
import ctypes
import webbrowser
import os
import time
import tempfile
import numpy as np
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QToolBar, QAction, QLabel,
                             QFileDialog, QColorDialog, QMainWindow, QToolButton, QMenu, QLineEdit, QFrame, QVBoxLayout,
                             QHBoxLayout, QSizePolicy, QMessageBox, QSystemTrayIcon,
                             QDialog, QListWidget, QDialogButtonBox, QListWidgetItem, QShortcut)
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QCursor, QPolygonF, QFont, QFontMetrics, QIcon, QTransform, \
    QPainterPath, QPainterPathStroker, QImage, QDesktopServices, QFontDatabase, QKeySequence, QLinearGradient
from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize, QPointF, QPropertyAnimation, QEasingCurve, QSettings, QUrl, \
    QEvent, QTimer

# --- GUID-константы питания (значения из Windows SDK).
# v2.5 подписывалась на GUID 0272C0DA-3E02-4AEF-89B4-0F4A4A62C71F — это НЕ
# GUID_MONITOR_POWER_ON, такого события Windows не присылает. ---
class _GUID(ctypes.Structure):
    _fields_ = [('Data1', ctypes.c_ulong),
                ('Data2', ctypes.c_ushort),
                ('Data3', ctypes.c_ushort),
                ('Data4', ctypes.c_ubyte * 8)]


def _guid(d1, d2, d3, tail):
    return _GUID(d1, d2, d3, (ctypes.c_ubyte * 8)(*tail))


# Гашение/включение экрана по таймеру простоя (главный рецидив «через 15 минут»).
# Значение проверено эмпирически: при DPMS-цикле Windows присылает именно его
# (PBT_POWERSETTINGCHANGE, Data=0 off / 1 on). Вариант с Data3=0x4A26 и хвостом
# 8BC1-7E607926A3A, который гуляет по блогам, НЕ приходит вообще.
GUID_MONITOR_POWER_ON = _guid(0x02731015, 0x4510, 0x4526,
                              (0x99, 0xE6, 0xE5, 0xA1, 0x7E, 0xBD, 0x1A, 0xEA))
# Состояние дисплея консоли (on/off/dim)
GUID_CONSOLE_DISPLAY_STATE = _guid(0x6FE69556, 0x704A, 0x47A0,
                                   (0x8F, 0x24, 0xC2, 0x8D, 0x93, 0x6F, 0xDA, 0x47))
DEVICE_NOTIFY_WINDOW_HANDLE = 0

# --- Win32: ЯВНЫЕ ПРОТОТИПЫ. Без argtypes ctypes усекает 64-битные HWND/HANDLE
# до 32 бит: SetWindowPos(hwnd, HWND_TOPMOST=-1, ...) получает 0x00000000FFFFFFFF
# вместо -1 и МОЛЧА возвращает 0. A/B-проверка на этой машине: ret=0 без
# прототипов, ret=1 с прототипами. В v2.5 из-за этого не работал НИ ОДИН способ
# вернуть «поверх всех» (таймер 2 с, агрессивное восстановление, фокус) —
# оставался только Qt-хинт, и первый же DPMS-цикл ронял окна НАВСЕГДА. ---
_u32 = ctypes.windll.user32
_gdi32 = ctypes.windll.gdi32
_k32 = ctypes.windll.kernel32

_u32.SetWindowPos.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_int,
                              ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint]
_u32.SetWindowPos.restype = ctypes.c_int
_u32.GetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int]
_u32.GetWindowLongW.restype = ctypes.c_long
_u32.GetDC.argtypes = [ctypes.c_void_p]
_u32.GetDC.restype = ctypes.c_void_p
_u32.ReleaseDC.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
_u32.ReleaseDC.restype = ctypes.c_int
_gdi32.GetPixel.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int]
_gdi32.GetPixel.restype = ctypes.c_uint
_u32.RegisterPowerSettingNotification.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint]
_u32.RegisterPowerSettingNotification.restype = ctypes.c_void_p
_u32.UnregisterPowerSettingNotification.argtypes = [ctypes.c_void_p]
_u32.UnregisterPowerSettingNotification.restype = ctypes.c_int
_k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
_k32.CreateMutexW.restype = ctypes.c_void_p
_k32.CloseHandle.argtypes = [ctypes.c_void_p]
_k32.CloseHandle.restype = ctypes.c_int

_u32.GetTopWindow.argtypes = [ctypes.c_void_p]
_u32.GetTopWindow.restype = ctypes.c_void_p
_u32.GetWindow.argtypes = [ctypes.c_void_p, ctypes.c_uint]
_u32.GetWindow.restype = ctypes.c_void_p

HWND_TOPMOST = ctypes.c_void_p(-1)
HWND_NOTOPMOST = ctypes.c_void_p(-2)
GW_HWNDNEXT = 2
GWL_EXSTYLE = -20
WS_EX_TOPMOST = 0x00000008
WS_EX_TRANSPARENT = 0x00000020
_u32.SetWindowLongW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_long]
_u32.SetWindowLongW.restype = ctypes.c_long
# NOSIZE|NOMOVE|NOACTIVATE|NOOWNERZORDER — фокус и активацию не трогаем
SWP_TOPMOST_FLAGS = 0x0001 | 0x0002 | 0x0010 | 0x0020


def _win_is_topmost(hwnd):
    """Фактический признак «поверх всех» — по стилю окна, а не по надежде."""
    return bool(_u32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE) & WS_EX_TOPMOST)


def _win_set_click_through(hwnd, on):
    """Вкл/выкл «сквозную» для мыши прозрачность окна (WS_EX_TRANSPARENT).

    Нужна, пока открыт модальный диалог: оверлей остаётся видимым (рисунки не
    пропадают), но клики проходят сквозь него к диалогу и к другим окнам.
    Флаг ставится только при необходимости — лишних SetWindowLongW нет.
    """
    style = _u32.GetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE)
    flag_on = bool(style & WS_EX_TRANSPARENT)
    if on and not flag_on:
        return _u32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, style | WS_EX_TRANSPARENT)
    if not on and flag_on:
        return _u32.SetWindowLongW(ctypes.c_void_p(hwnd), GWL_EXSTYLE, style & ~WS_EX_TRANSPARENT)
    return style


def _z_index(hwnd):
    """Позиция окна в z-order (0 = самое верхнее). Нужна, чтобы понимать, кто
    кого перекрывает: у двух topmost-окон флаг одинаковый, а порядок разный."""
    h = _u32.GetTopWindow(None)
    i = 0
    while h and i < 4000:
        if int(h) == int(hwnd):
            return i
        h = _u32.GetWindow(h, GW_HWNDNEXT)
        i += 1
    return -1


def _win_set_topmost(hwnd, toggle=False):
    """Вернуть окно в topmost. toggle=True — снять и поставить заново.

    Повторный SetWindowPos(HWND_TOPMOST) НЕ поднимает окно, если флаг уже стоит,
    но DWM (после гашения экрана, смены мониторов) опустил его НИЖЕ других
    topmost-окон. Снять+поставить поднимает окно на верх диапазона.
    """
    h = ctypes.c_void_p(hwnd)
    if toggle:
        _u32.SetWindowPos(h, HWND_NOTOPMOST, 0, 0, 0, 0, SWP_TOPMOST_FLAGS)
    return _u32.SetWindowPos(h, HWND_TOPMOST, 0, 0, 0, 0, SWP_TOPMOST_FLAGS)


def _register_power_notifications(hwnd):
    """Подписка на события питания для окна. PowrProf.PowerSettingRegisterNotification
    на этой машине отдаёт 87 (ERROR_INVALID_PARAMETER) — работает user32-вариант."""
    handles = []
    for guid in (GUID_MONITOR_POWER_ON, GUID_CONSOLE_DISPLAY_STATE):
        try:
            h = _u32.RegisterPowerSettingNotification(
                ctypes.c_void_p(hwnd), ctypes.byref(guid), DEVICE_NOTIFY_WINDOW_HANDLE)
        except Exception:
            h = None
        if h:
            handles.append(h)
    return handles


def _unregister_power_notifications(handles):
    for h in handles or []:
        try:
            _u32.UnregisterPowerSettingNotification(ctypes.c_void_p(h))
        except Exception:
            pass


# --- Функция для создания плоских иконок (без 3D) ---
def get_flat_svg_icon(svg_path, color="white"):
    colored_svg = svg_path.replace('fill="white"', f'fill="{color}"').replace('stroke="white"', f'stroke="{color}"')
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    pixmap.loadFromData(bytearray(colored_svg, encoding='utf-8'), "SVG")
    return QIcon(pixmap)


# --- Функция для создания векторных иконок с эффектом 3D и глянцем ---
def get_svg_icon(svg_path, color="white"):
    qcolor = QColor(color)
    if not qcolor.isValid():
        qcolor = QColor("white")

    # 1. Создаем плоскую иконку (маску)
    flat_svg = svg_path.replace('fill="white"', 'fill="black"').replace('stroke="white"', 'stroke="black"')
    temp_pixmap = QPixmap()
    temp_pixmap.loadFromData(bytearray(flat_svg, encoding='utf-8'), "SVG")
    temp_pixmap = temp_pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    # 2. Создаем финальный пиксмэп
    final_pixmap = QPixmap(64, 64)
    final_pixmap.fill(Qt.transparent)

    p = QPainter(final_pixmap)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)

    # 3. Рисуем 3D градиент
    gradient = QLinearGradient(0, 0, 0, 64)
    gradient.setColorAt(0.0, qcolor.lighter(180))
    gradient.setColorAt(0.5, qcolor)
    gradient.setColorAt(1.0, qcolor.darker(300))
    p.fillRect(final_pixmap.rect(), gradient)

    # 4. Обрезаем градиент строго по форме иконки
    p.setCompositionMode(QPainter.CompositionMode_DestinationIn)
    x = (64 - temp_pixmap.width()) // 2
    y = (64 - temp_pixmap.height()) // 2
    p.drawPixmap(x, y, temp_pixmap)

    # 5. Добавляем стеклянный блик сверху
    p.setCompositionMode(QPainter.CompositionMode_SourceAtop)
    glossy_gradient = QLinearGradient(0, 0, 0, 64)
    glossy_gradient.setColorAt(0.0, QColor(255, 255, 255, 110))
    glossy_gradient.setColorAt(0.4, QColor(255, 255, 255, 0))
    p.fillRect(final_pixmap.rect(), glossy_gradient)

    p.end()

    return QIcon(final_pixmap)


# --- SVG иконки ---
ICON_CURSOR = '<svg viewBox="0 0 24 24" fill="white"><path d="M5.5 3.5L19 12L13 13.5L11 19.5L5.5 3.5Z"/></svg>'
ICON_PEN = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20L8 16M8 16L16 8L20 12L12 20L4 20Z M14 6L16 4L20 8L18 10"/></svg>'
ICON_SHAPES = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><circle cx="17.5" cy="6.5" r="3.5"/><path d="M7 15L11 21H3L7 15Z"/><path d="M14 21L21 14"/></svg>'

ICON_SHAPE_LINE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="19" x2="19" y2="5"/></svg>'
ICON_SHAPE_RECT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="6" width="16" height="12" rx="1"/></svg>'
ICON_SHAPE_ELLIPSE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="8"/></svg>'
ICON_SHAPE_ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="19" x2="19" y2="5"/><polyline points="11,5 19,5 19,13"/></svg>'

ICON_TEXT = '<svg viewBox="0 0 24 24" fill="white"><path d="M5 4H19V8H17V6H14V18H16V20H8V18H10V6H7V8H5V4Z"/></svg>'
ICON_ERASER = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20H8.5a2.5 2.5 0 0 1-1.77-.73l-4.5-4.5a2.5 2.5 0 0 1 0-3.54l9.5-9.5a2.5 2.5 0 0 1 3.54 0l5.5 5.5a2.5 2.5 0 0 1 0 3.54L11.5 20"/><path d="M9 11l4 4"/></svg>'
ICON_COLOR = '<svg viewBox="0 0 24 24" fill="white"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c1 0 2-.8 2-2 0-.5-.2-1-.6-1.4-.3-.4-.4-.8-.4-1.1 0-1 .8-1.5 1.5-1.5H17c2.8 0 5-2.2 5-5 0-4.4-4.5-8-10-8zm-5 9c-.8 0-1.5-.7-1.5-1.5S6.2 8 7 8s1.5.7 1.5 1.5S7.8 11 7 11zm3-4c-.8 0-1.5-.7-1.5-1.5S9.2 4 10 4s1.5.7 1.5 1.5S10.8 7 10 7zm4 0c-.8 0-1.5-.7-1.5-1.5S13.2 4 14 4s1.5.7 1.5 1.5S14.8 7 14 7zm3 4c-.8 0-1.5-.7-1.5-1.5S16.2 8 17 8s1.5.7 1.5 1.5S17.8 11 17 11z"/></svg>'
ICON_IMAGE = '<svg viewBox="0 0 24 24" fill="white"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>'
ICON_SELECT = '<svg viewBox="0 0 24 24" fill="white"><path d="M12 2L8 6h3v3h2V6h3l-4-4zm0 20l4-4h-3v-3h-2v3H8l4 4zM2 12l4 4v-3h3v-2H6V8l-4 4zm20 0l-4-4v3h-3v2h3v3l4-4z"/></svg>'
ICON_SCREENSHOT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>'
ICON_AI = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M4 21 L9 3 L14 21"/><path d="M6 15 H12"/><path d="M19 3 V21"/></svg>'
ICON_UNDO = '<svg viewBox="0 0 24 24" fill="white"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>'
ICON_HIDE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
ICON_SHOW = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
ICON_CLEAR = '<svg viewBox="0 0 24 24" fill="white"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>'
ICON_EXIT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/></svg>'
ICON_TOGGLE_TEXT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h10"/></svg>'
ICON_COLLAPSE = '<svg viewBox="0 0 24 24" fill="white"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0S9.6.84 9.18 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg>'
ICON_RUBLE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4v16"/><path d="M8 4h6a4 4 0 0 1 0 8H8"/><path d="M5 12h9"/><path d="M5 16h9"/></svg>'
ICON_DOLLAR = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'
ICON_YUAN = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3l6 9 6-9"/><path d="M12 12v9"/><path d="M8 16h8"/><path d="M8 19h8"/></svg>'
ICON_EURO = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M18 5a7.5 7.5 0 1 0 0 14"/><path d="M4 10h9M4 14h9"/></svg>'
ICON_RIAL = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 4v12c0 2 1.5 3 3.5 3h9M6 9h12M10 4v5"/></svg>'
ICON_RUPEE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3h12M6 8h12M9 3c4 0 6 1.5 6 5s-2 5-6 5l7 8"/></svg>'
ICON_YEN = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M6 3l6 9 6-9M12 12v9M8 15h8M8 18h8"/></svg>'
ICON_WON = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 4l3 16 3-12 3 12 3-16M3 10h18M3 14h18"/></svg>'
ICON_LASER = '<svg viewBox="0 0 24 24" fill="#FF0000" stroke="white" stroke-width="1.5"><circle cx="12" cy="12" r="7" /></svg>'

# --- Иконки языков (SVG с увеличенным текстом) ---
LANG_ICONS_SVG = {
    "EN": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">EN</text></svg>',
    "RU": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">РУ</text></svg>',
    "ZH": '<svg viewBox="0 0 24 24"><text x="12" y="20" font-family="Arial" font-size="22" font-weight="bold" fill="white" text-anchor="middle">中</text></svg>',
    "ES": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">ES</text></svg>',
    "PT": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">PT</text></svg>',
    "FR": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">FR</text></svg>',
    "DE": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">DE</text></svg>',
    "IT": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">IT</text></svg>',
    "AR": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">AR</text></svg>',
    "HI": '<svg viewBox="0 0 24 24"><text x="12" y="19" font-family="Arial" font-size="18" font-weight="bold" fill="white" text-anchor="middle">HI</text></svg>',
    "JA": '<svg viewBox="0 0 24 24"><text x="12" y="20" font-family="Arial" font-size="22" font-weight="bold" fill="white" text-anchor="middle">日</text></svg>',
    "KO": '<svg viewBox="0 0 24 24"><text x="12" y="20" font-family="Arial" font-size="22" font-weight="bold" fill="white" text-anchor="middle">한</text></svg>'
}


# ============================================================
# Excalidraw-style rendering helpers (rough hand-drawn look)
# ============================================================

def _ex_rng(seed):
    return random.Random(int(seed) & 0x7FFFFFFF)


def _ex_smooth_pts(pts, passes=2):
    """EMA-сглаживание центральной линии (без лага: ядро симметричное)."""
    pts = [QPointF(p) for p in pts]
    a = 0.55
    for _ in range(passes):
        n = len(pts)
        if n < 3:
            break
        out = [pts[0]]
        for i in range(1, n - 1):
            out.append(QPointF(
                pts[i - 1].x() * (1 - a) / 2 + pts[i].x() * a + pts[i + 1].x() * (1 - a) / 2,
                pts[i - 1].y() * (1 - a) / 2 + pts[i].y() * a + pts[i + 1].y() * (1 - a) / 2))
        out.append(pts[-1])
        pts = out
    return pts


def _ex_resample(pts, step=2.5):
    """Равномерная выборка по длине дуги — стабильная ширина вдоль штриха."""
    if len(pts) < 2:
        return list(pts)
    out = [pts[0]]
    prev = pts[0]
    carry = 0.0
    for i in range(1, len(pts)):
        cur = pts[i]
        seg = math.hypot(cur.x() - prev.x(), cur.y() - prev.y())
        if seg <= 1e-9:
            continue
        d = carry
        while d < seg:
            t = d / seg
            out.append(QPointF(prev.x() + (cur.x() - prev.x()) * t,
                               prev.y() + (cur.y() - prev.y()) * t))
            d += step
        carry = d - seg
        prev = cur
    out.append(pts[-1])
    return out


def _ex_signed_area(raw_pts):
    area = 0.0
    cnt = len(raw_pts)
    for i in range(cnt):
        x1, y1 = raw_pts[i].x(), raw_pts[i].y()
        x2, y2 = raw_pts[(i + 1) % cnt].x(), raw_pts[(i + 1) % cnt].y()
        area += x1 * y2 - x2 * y1
    return area


def _ex_add_quad(path, quad_pts):
    """Добавляет четырёхугольник с фиксированным обходом (нет вычитания в WindingFill)."""
    if _ex_signed_area(quad_pts) < 0:
        quad_pts = [quad_pts[3], quad_pts[2], quad_pts[1], quad_pts[0]]
    path.addPolygon(QPolygonF(quad_pts))
    path.closeSubpath()


def _ex_add_circle(path, center, r):
    """Круг как 14-угольник с тем же обходом, что и quads."""
    ring = [QPointF(center.x() + r * math.cos(2 * math.pi * k / 14.0),
                    center.y() + r * math.sin(2 * math.pi * k / 14.0)) for k in range(14)]
    if _ex_signed_area(ring) < 0:
        ring.reverse()
    path.addPolygon(QPolygonF(ring))
    path.closeSubpath()


def _ex_pen_stroke_path(points, width, final=True):
    """Контур штриха ПОСТОЯННОЙ ширины — концы не тоньше середины (тейпер убран).

    Строится как набор выпуклых четырёхугольников + круги-наконечники,
    объединённых через WindingFill — самопересечения корректно union-ятся.
    """
    # live и финал рендерятся ИДЕНТИЧНО — штрих не меняется после отпускания кнопки
    pts = _ex_resample(_ex_smooth_pts(points, 2), 2.5)
    n = len(pts)
    path = QPainterPath()
    if n == 0:
        return path
    if n == 1:
        _ex_add_circle(path, pts[0], max(0.8, width * 0.55))
        return path

    arc = [0.0]
    for i in range(1, n):
        d = math.hypot(pts[i].x() - pts[i - 1].x(), pts[i].y() - pts[i - 1].y())
        arc.append(arc[-1] + max(d, 0.0))
    total = arc[-1]
    if total < 1.0:
        _ex_add_circle(path, pts[-1], max(0.8, width * 0.55))
        return path

    # ширина ПОСТОЯННАЯ по всей длине, включая концы (без тейпера)
    hw = [width * 0.5] * n

    path.setFillRule(Qt.WindingFill)
    for i in range(n - 1):
        if i == 0:
            dx = pts[1].x() - pts[0].x()
            dy = pts[1].y() - pts[0].y()
        elif i == n - 2:
            dx = pts[-1].x() - pts[-2].x()
            dy = pts[-1].y() - pts[-2].y()
        else:
            dx = pts[i + 1].x() - pts[i - 1].x()
            dy = pts[i + 1].y() - pts[i - 1].y()
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        p, q = pts[i], pts[i + 1]
        w0, w1 = hw[i], hw[i + 1]
        if i == 0:
            pv = pts[0]
        else:
            pv = pts[i - 1]
        if i == n - 2:
            nv = pts[-1]
        else:
            nv = pts[i + 2]
        e1x, e1y = p.x() - pv.x(), p.y() - pv.y()
        e2x, e2y = nv.x() - q.x(), nv.y() - q.y()
        l1 = math.hypot(e1x, e1y) or 1.0
        l2 = math.hypot(e2x, e2y) or 1.0
        cross_i = (e1x * e2y - e1y * e2x) / (l1 * l2)
        _ex_add_quad(path, [
            QPointF(p.x() + nx * w0, p.y() + ny * w0),
            QPointF(q.x() + nx * w1, q.y() + ny * w1),
            QPointF(q.x() - nx * w1, q.y() - ny * w1),
            QPointF(p.x() - nx * w0, p.y() - ny * w0),
        ])
        # уплотнитель только на РЕЗКОМ угле (порог высокий — дрожь руки не даёт «бисер»)
        r = max(w0, w1) * 0.78
        if r > 0.6 and abs(cross_i) > 0.30:
            _ex_add_circle(path, q, r)
    _ex_add_circle(path, pts[0], hw[0])
    _ex_add_circle(path, pts[-1], hw[-1])
    return path


def _ex_centerline_path(points):
    """Гладкая центральная линия (для hit-test и ластика) — quad через середины."""
    pts = _ex_smooth_pts(points, 1)
    n = len(pts)
    path = QPainterPath()
    if n == 0:
        return path
    if n == 1:
        path.addEllipse(pts[0], 1.0, 1.0)
        return path
    path.moveTo(pts[0])
    for i in range(1, n - 1):
        mid = QPointF((pts[i].x() + pts[i + 1].x()) / 2.0,
                      (pts[i].y() + pts[i + 1].y()) / 2.0)
        path.quadTo(pts[i], mid)
    path.lineTo(pts[-1])
    return path


def _ex_pen_stroke_path_cached(item):
    """Готовый контур штриха кэшируется в item['stroke_path'].

    Точки пера после отпускания кнопки не меняются, а v2.5 пересобирала контур
    (тысячи quad-ов) на КАЖДОЙ перерисовке — при rebuild_canvas после undo/redo
    и удаления это заметные лаги. Живой штрих не кэшируется: точки ещё растут.
    """
    path = item.get('stroke_path')
    if path is None:
        path = _ex_pen_stroke_path(item.get('points') or [], item['width'], final=True)
        item['stroke_path'] = path
    return path


def _ex_draw_pen_item(painter, item):
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    pts = item.get('points') or []
    if len(pts) < 2:
        if 'path' in item:
            pen = QPen(item['color'], item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(item['path'])
        return
    painter.setPen(Qt.NoPen)
    painter.setBrush(item['color'])
    if item.get('live'):
        painter.drawPath(_ex_pen_stroke_path(pts, item['width'], final=False))
    else:
        painter.drawPath(_ex_pen_stroke_path_cached(item))


def _ex_rough_line(p0, p1, rng, amp=1.3, bow=None):
    """Слегка волнистая линия: кубическая Безье с дрожащими контрольными точками."""
    path = QPainterPath()
    sx = p0.x() + rng.uniform(-amp, amp)
    sy = p0.y() + rng.uniform(-amp, amp)
    ex = p1.x() + rng.uniform(-amp, amp)
    ey = p1.y() + rng.uniform(-amp, amp)
    path.moveTo(sx, sy)
    dx, dy = p1.x() - p0.x(), p1.y() - p0.y()
    L = math.hypot(dx, dy)
    if L < 12:
        path.lineTo(ex, ey)
        return path
    if bow is None:
        bow = max(1.0, L * 0.015)
    nx, ny = -dy / L, dx / L
    c1 = QPointF(sx + dx * 0.33 + nx * rng.uniform(-bow, bow),
                 sy + dy * 0.33 + ny * rng.uniform(-bow, bow))
    c2 = QPointF(sx + dx * 0.66 + nx * rng.uniform(-bow, bow),
                 sy + dy * 0.66 + ny * rng.uniform(-bow, bow))
    path.cubicTo(c1, c2, QPointF(ex, ey))
    return path


def _ex_rough_rect_path(tl, br, rng, amp=1.8):
    corners = []
    for (x, y) in ((tl.x(), tl.y()), (br.x(), tl.y()), (br.x(), br.y()), (tl.x(), br.y())):
        corners.append(QPointF(x + rng.uniform(-amp, amp), y + rng.uniform(-amp, amp)))
    path = QPainterPath()
    for i in range(4):
        path.addPath(_ex_rough_line(corners[i], corners[(i + 1) % 4], rng, amp=amp * 0.7))
    return path


def _ex_rough_ellipse_path(p0, p1, rng):
    cx = (p0.x() + p1.x()) / 2.0
    cy = (p0.y() + p1.y()) / 2.0
    rx = abs(p1.x() - p0.x()) / 2.0
    ry = abs(p1.y() - p0.y()) / 2.0
    path = QPainterPath()
    if rx < 2.0 or ry < 2.0:
        path.addEllipse(QPointF(cx, cy), max(rx, 1.0), max(ry, 1.0))
        return path
    start = rng.uniform(0, 2 * math.pi)
    overrun = rng.uniform(0.05, 0.15)
    steps = 22
    rj1 = rng.uniform(-0.03, 0.03)
    rj2 = rng.uniform(-0.02, 0.02)
    rot1 = rng.uniform(0, 2 * math.pi)
    pts = []
    for i in range(steps + 2):
        t = start + (2 * math.pi + overrun) * i / steps
        wob = 1.0 + rj1 * math.sin(2 * t + rot1) + rj2 * math.sin(3 * t)
        pts.append(QPointF(cx + math.cos(t) * rx * wob, cy + math.sin(t) * ry * wob))
    path.moveTo((pts[0].x() + pts[1].x()) / 2.0, (pts[0].y() + pts[1].y()) / 2.0)
    for i in range(1, len(pts)):
        cur = pts[i]
        nxt = pts[(i + 1) % len(pts)]
        path.quadTo(cur, QPointF((cur.x() + nxt.x()) / 2.0, (cur.y() + nxt.y()) / 2.0))
    path.closeSubpath()
    return path


def _ex_draw_rough_shape(painter, item):
    """Рукописная фигура: два прохода с разными seed (стиль rough.js)."""
    st = item.get('shape_type')
    color = item['color']
    w = item['width']
    p0 = item.get('p0')
    p1 = item.get('p1')
    painter.setBrush(Qt.NoBrush)
    painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
    pen = QPen(color, w, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
    painter.setPen(pen)
    if p0 is None or p1 is None:
        painter.drawPath(item['path'])
        return
    seed = item.get('seed', 1)

    def _shift_pt(p, k):
        if k == 0:
            return p
        r = _ex_rng(seed + 7717)
        return QPointF(p.x() + r.uniform(-1.6, 1.6), p.y() + r.uniform(-1.6, 1.6))

    if st == 'line':
        for k in range(1):
            painter.drawPath(_ex_rough_line(_shift_pt(p0, k), _shift_pt(p1, k),
                                            _ex_rng(seed + k * 7919),
                                            amp=1.3 if k == 0 else 2.0))
    elif st == 'arrow':
        for k in range(1):
            painter.drawPath(_ex_rough_line(_shift_pt(p0, k), _shift_pt(p1, k),
                                            _ex_rng(seed + k * 7919),
                                            amp=1.3 if k == 0 else 2.0))
        ang = math.atan2(p1.y() - p0.y(), p1.x() - p0.x())
        size = max(11.0, w * 4.0)
        for k in range(1):
            rng = _ex_rng(seed + 104729 + k * 7919)
            spread = math.pi / 7 + rng.uniform(-0.05, 0.05)
            sz = size * (1.0 + rng.uniform(-0.08, 0.08))
            a1 = ang + math.pi - spread
            a2 = ang + math.pi + spread
            hpath = QPainterPath()
            hpath.moveTo(p1.x() + math.cos(a1) * sz + rng.uniform(-1.0, 1.0),
                         p1.y() + math.sin(a1) * sz + rng.uniform(-1.0, 1.0))
            hpath.lineTo(p1.x() + rng.uniform(-0.8, 0.8), p1.y() + rng.uniform(-0.8, 0.8))
            hpath.lineTo(p1.x() + math.cos(a2) * sz + rng.uniform(-1.0, 1.0),
                         p1.y() + math.sin(a2) * sz + rng.uniform(-1.0, 1.0))
            painter.drawPath(hpath)
    elif st == 'rect':
        rect = QRectF(p0, p1).normalized()
        for k in range(1):
            s0 = _shift_pt(rect.topLeft(), k)
            s1 = _shift_pt(rect.bottomRight(), k)
            painter.drawPath(_ex_rough_rect_path(s0, s1, _ex_rng(seed + k * 7919),
                                                 amp=1.8 if k == 0 else 2.6))
    elif st == 'ellipse':
        for k in range(1):
            if k == 0:
                e0, e1 = p0, p1
            else:
                r = _ex_rng(seed + 31337)
                e0 = QPointF(p0.x() + r.uniform(-1.8, 1.8), p0.y() + r.uniform(-1.8, 1.8))
                e1 = QPointF(p1.x() + r.uniform(-1.8, 1.8), p1.y() + r.uniform(-1.8, 1.8))
            painter.drawPath(_ex_rough_ellipse_path(e0, e1, _ex_rng(seed + k * 7919)))
    else:
        painter.drawPath(item['path'])


class OverlayWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        self.tool = "cursor"
        self.laser_mode = False

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())
        self.show()
        self.laser_mode = False
        self.left_color = QColor(255, 0, 0)
        self.right_color = QColor(0, 120, 215)
        self.current_color = self.left_color

        self.pen_width = 3
        self.eraser_width = 20
        self.text_font_size = 24
        self.shape_type = "line"

        self.canvas = QPixmap(self.size())
        self.canvas.fill(Qt.transparent)
        self.last_pos = None

        self.drawings = []
        self.current_item = None
        self.is_hidden = False

        self.active_folder_item = None
        self.folder_files = []
        self.folder_index = -1
        self.folder_remove_bg = False
        self.folder_pixmaps = {}

        self.moving_image = None
        self.resizing_image = None
        self.resizing_handle = None
        self.move_offset = QPoint(0, 0)
        self.resize_start_pos = QPoint(0, 0)
        self.resize_start_points = []
        self.resize_button = Qt.NoButton
        self.moving_text = None
        self.transforming_text = None
        self.text_transform_start = {}
        self.shape_start_pos = None
        self.shape_end_pos = None
        self.screenshot_start_pos = None
        self.screenshot_end_pos = None
        self.is_capturing = False
        self.text_input = None
        self.text_color = None
        self.screenshot_open_file = True

        self.suppress_select_switch = False

        self.ai_start_pos = None
        self.ai_end_pos = None
        self.ai_bg_color = QColor(255, 255, 255)
        self.ai_is_lasso = False
        self.ai_lasso_path = None

        self.undo_stack = []
        self.redo_stack = []
        self.update_cursor()

    def closeEvent(self, event):
        if not self.main_window.is_closing:
            event.ignore()
        else:
            event.accept()

    def _clone_drawings(self):
        """Снапшот рисунков для undo/redo.

        pixmap НЕ копируется: QPixmap разделяемый (copy-on-write), и in-place
        его никто не меняет (код только ПРИСВАИВАЕТ новый pixmap). Глубокое
        .copy() у v2.5 на каждой вставленной картинке 1500x1500 — это ~9 МБ
        копирования на каждый клик (save_state вызывается в mousePress).
        """
        out = []
        for d in self.drawings:
            nd = d.copy()
            if 'path' in nd: nd['path'] = QPainterPath(nd['path'])
            if 'points' in nd: nd['points'] = [QPointF(p) for p in nd['points']]
            out.append(nd)
        return out

    def save_state(self):
        if len(self.undo_stack) >= 20:
            self.undo_stack.pop(0)
        self.undo_stack.append({'drawings': self._clone_drawings()})
        self.redo_stack.clear()

    def undo(self):
        self.commit_text()
        if self.undo_stack:
            self.redo_stack.append({'drawings': self._clone_drawings()})

            state = self.undo_stack.pop()
            self.drawings = state['drawings']
            self.rebuild_canvas()
            self.deselect_all_images()
            self.active_folder_item = None
            self.update()

    def redo(self):
        if self.redo_stack:
            self.undo_stack.append({'drawings': self._clone_drawings()})

            state = self.redo_stack.pop()
            self.drawings = state['drawings']
            self.rebuild_canvas()
            self.deselect_all_images()
            self.active_folder_item = None
            self.update()

    def delete_selected_item(self):
        if self.tool != "select": return
        for item in reversed(self.drawings):
            if item.get('selected', False) or item.get('show_handles', False):
                self.save_state()
                self.drawings.remove(item)
                self.rebuild_canvas()
                self.deselect_all_images()
                self.update()
                break

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0084:
                pt = QPoint(msg.pt.x, msg.pt.y)
                if self.main_window.geometry().contains(pt):
                    return True, -1
                if self.tool == "cursor" and not self.laser_mode:
                    return True, -1
                return True, 1
            elif msg.message in (0x007E, 0x0218, 0x02B1, 0x031A):
                # WM_DISPLAYCHANGE (смена конфигурации мониторов) и WM_POWERBROADCAST
                # (сон/пробуждение; вкл/выкл монитора — после подписки
                # PowerSettingRegisterNotification). DWM после этого перестраивает
                # z-order, поэтому нужен усиленный тоггл, а не повторный TOPMOST.
                self.main_window.restore_topmost_aggressive()
        return super().nativeEvent(eventType, message)

    def set_tool(self, tool):
        if self.tool == "text" and tool != "text":
            self.commit_text()

        if self.is_hidden and tool in ("pen", "eraser", "shape", "text", "select", "ai"):
            self.is_hidden = False
            self.main_window.update_hide_button_state()

        if self.active_folder_item and tool not in ("select", "cursor"):
            self.active_folder_item = None
            self.folder_files = []
            self.folder_index = -1
            self.folder_pixmaps = {}

        self.tool = tool
        self.update_cursor()
        self.update()

    def update_cursor(self):
        if self.tool == "eraser":
            self.update_eraser_cursor()
        elif self.tool == "ai":
            self.update_ai_cursor()
        elif self.laser_mode:
            self.update_laser_cursor()
        elif self.tool == "cursor":
            self.deselect_all_images()
            self.unsetCursor()
        elif self.tool == "text":
            self.setCursor(Qt.IBeamCursor)
        else:
            self.update_crosshair_cursor()

    def _draw_crosshair(self, painter):
        pen_black = QPen(Qt.black, 3)
        pen_black.setCapStyle(Qt.RoundCap)
        pen_white = QPen(Qt.white, 1.5)
        pen_white.setCapStyle(Qt.RoundCap)

        painter.setPen(pen_black)
        painter.drawLine(QPointF(15, 0), QPointF(15, 12))
        painter.drawLine(QPointF(15, 18), QPointF(15, 30))
        painter.drawLine(QPointF(0, 15), QPointF(12, 15))
        painter.drawLine(QPointF(18, 15), QPointF(30, 15))

        painter.setPen(pen_white)
        painter.drawLine(QPointF(15, 0), QPointF(15, 12))
        painter.drawLine(QPointF(15, 18), QPointF(15, 30))
        painter.drawLine(QPointF(0, 15), QPointF(12, 15))
        painter.drawLine(QPointF(18, 15), QPointF(30, 15))

    def update_crosshair_cursor(self):
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        self._draw_crosshair(painter)
        painter.end()
        self.setCursor(QCursor(pixmap, 15, 15))

    def update_ai_cursor(self):
        size = 32
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        font = QFont("Arial", 8, QFont.Bold)
        painter.setFont(font)
        text = "ИИ" if self.main_window.lang == "RU" else "AI"

        self._draw_crosshair(painter)

        path = QPainterPath()
        path.addText(QPointF(16, 24), font, text)
        painter.setPen(QPen(Qt.black, 3, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)

        painter.setPen(QPen(Qt.white, 1))
        painter.setBrush(Qt.white)
        painter.drawPath(path)

        painter.end()
        self.setCursor(QCursor(pixmap, 15, 15))

    def update_laser_cursor(self):
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(size / 2.0, size / 2.0)
        for i in range(4, 0, -1):
            painter.setBrush(QColor(255, 0, 0, 15))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(center, i * 4, i * 4)
        painter.setBrush(QColor(255, 30, 30))
        painter.setPen(QPen(QColor(120, 0, 0), 1))
        painter.drawEllipse(center, 5, 5)
        painter.end()
        self.setCursor(QCursor(pixmap, int(size / 2), int(size / 2)))

    def update_eraser_cursor(self):
        size = self.eraser_width
        if size < 16: size = 16
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        center = QPointF(size / 2.0, size / 2.0)
        radius = size / 2.0 - 1.5
        pen_black = QPen(Qt.black, 2.5)
        pen_black.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_black)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(center, radius, radius)
        pen_white = QPen(Qt.white, 1.5)
        pen_white.setStyle(Qt.CustomDashLine)
        pen_white.setDashPattern([4, 4])
        pen_white.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_white)
        painter.drawEllipse(center, radius, radius)
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(Qt.white)
        painter.drawEllipse(center, 2, 2)
        painter.end()
        self.setCursor(QCursor(pixmap, int(size / 2), int(size / 2)))

    def deselect_all_images(self):
        for item in self.drawings:
            if item['type'] == 'image':
                item['selected'] = False
            elif item['type'] == 'text':
                item['show_handles'] = False
                item['selected'] = False
        self.update()

    def get_handle_rect(self, pt):
        return QRectF(pt.x() - 5, pt.y() - 5, 10, 10)

    def get_text_corners(self, item):
        font_family = item.get('font_family', 'Arial')
        font = QFont(font_family)
        font.setPixelSize(item['font_size'])
        font.setBold(True)
        fm = QFontMetrics(font)
        rect = fm.boundingRect(item['text'])

        w = rect.width() / 2.0
        h = rect.height() / 2.0

        local_points = [
            QPointF(-w, -h),
            QPointF(w, -h),
            QPointF(w, h),
            QPointF(-w, h)
        ]

        transform = QTransform()
        transform.translate(item['pos'].x(), item['pos'].y())
        transform.rotate(item.get('rotation', 0))

        return [transform.map(p) for p in local_points]

    def draw_image_item(self, painter, item):
        try:
            pixmap = item['pixmap']
            pts = item['points']
            if len(pts) < 4 or pixmap.isNull(): return
            tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]
            w = max(pixmap.width(), 1)
            h = max(pixmap.height(), 1)
            vx = tr - tl
            vy = bl - tl
            if w == 0 or h == 0: return
            m11 = vx.x() / w
            m12 = vx.y() / w
            m21 = vy.x() / h
            m22 = vy.y() / h
            if abs(m11 * m22 - m12 * m21) < 0.0001: return
            t = QTransform(m11, m12, m21, m22, tl.x(), tl.y())
            painter.save()
            painter.setTransform(t, True)
            painter.drawPixmap(0, 0, pixmap)
            painter.restore()
        except Exception:
            pass

    def get_pixmap_coords(self, item, screen_pos):
        pts = item['points']
        if len(pts) < 4: return None
        tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]
        w = max(item['pixmap'].width(), 1)
        h = max(item['pixmap'].height(), 1)

        vx = tr - tl
        vy = bl - tl
        m11 = vx.x() / w
        m12 = vx.y() / w
        m21 = vy.x() / h
        m22 = vy.y() / h

        t = QTransform(m11, m12, m21, m22, tl.x(), tl.y())
        inv, ok = t.inverted()
        if ok:
            p = inv.map(screen_pos)
            return QPoint(int(p.x()), int(p.y()))
        return None

    def get_shape_path(self, shape_type, start, end, pen_width):
        path = QPainterPath()
        if shape_type == "line":
            path.moveTo(start)
            path.lineTo(end)
        elif shape_type == "rect":
            path.addRect(QRectF(start, end).normalized())
        elif shape_type == "ellipse":
            path.addEllipse(QRectF(start, end).normalized())
        elif shape_type == "arrow":
            path.moveTo(start)
            path.lineTo(end)
            angle = math.atan2(end.y() - start.y(), end.x() - start.x())
            arrow_size = max(11, pen_width * 4)
            p1 = QPointF(end.x() - arrow_size * math.cos(angle - math.pi / 7),
                         end.y() - arrow_size * math.sin(angle - math.pi / 7))
            p2 = QPointF(end.x() - arrow_size * math.cos(angle + math.pi / 7),
                         end.y() - arrow_size * math.sin(angle + math.pi / 7))
            path.moveTo(p1)
            path.lineTo(end)
            path.lineTo(p2)
        return path

    def draw_item_on_painter(self, painter, item):
        if item['type'] == 'pen':
            _ex_draw_pen_item(painter, item)
        elif item['type'] == 'shape':
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            if item.get('fill', False) or item.get('is_ai_bg', False):
                pen = QPen(item['color'], item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(item['color'])
                painter.drawPath(item['path'])
            else:
                _ex_draw_rough_shape(painter, item)
        elif item['type'] == 'eraser':
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.white, item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(item['path'])
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        elif item['type'] == 'text':
            font_family = item.get('font_family', 'Arial')
            font = QFont(font_family)
            font.setPixelSize(item['font_size'])
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(item['color'])
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)

            fm = QFontMetrics(font)
            rect = fm.boundingRect(item['text'])

            painter.save()
            painter.translate(item['pos'])
            painter.rotate(item.get('rotation', 0))

            draw_rect = QRectF(-rect.width() / 2.0, -rect.height() / 2.0, rect.width(), rect.height())
            painter.drawText(draw_rect, Qt.AlignCenter, item['text'])
            painter.restore()

    def rebuild_canvas(self):
        self.canvas.fill(Qt.transparent)
        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        for item in self.drawings:
            if item['type'] == 'image': continue
            if item.get('layer') in ('front', 'back'): continue
            self.draw_item_on_painter(p, item)
        p.end()

    def render_drawings(self, painter, is_capturing=False):
        # 1. Элементы на ЗАДНЕМ плане (включая фон ИИ)
        for item in self.drawings:
            if item.get('layer', 'front') == 'back':
                if item['type'] == 'image':
                    self.draw_image_item(painter, item)
                elif item['type'] in ('text', 'shape'):
                    self.draw_item_on_painter(painter, item)

        # 2. Canvas (Средний слой: ручка, ластик, фигуры)
        painter.drawPixmap(0, 0, self.canvas)

        # Текущий рисуемый элемент
        if self.current_item:
            self.draw_item_on_painter(painter, self.current_item)

        # Отрисовка картинок на СРЕДНЕМ плане
        for item in self.drawings:
            if item.get('layer') == 'middle' and item['type'] == 'image':
                self.draw_image_item(painter, item)

        # 3. Элементы на ПЕРЕДНЕМ плане
        for item in self.drawings:
            if item.get('layer', 'front') == 'front':
                if item['type'] == 'image':
                    self.draw_image_item(painter, item)
                elif item['type'] == 'text':
                    self.draw_item_on_painter(painter, item)

    def hit_test_item(self, item, pos):
        if item['type'] in ('pen', 'shape'):
            stroker = QPainterPathStroker()
            stroker.setWidth(item['width'] + 6)
            hit_path = stroker.createStroke(item['path'])
            if hit_path.contains(pos): return True
            if item['path'].contains(pos): return True
        elif item['type'] == 'text':
            font_family = item.get('font_family', 'Arial')
            font = QFont(font_family)
            font.setPixelSize(item['font_size'])
            font.setBold(True)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(item['text'])
            center = item['pos']
            rotation = item.get('rotation', 0)
            dx = pos.x() - center.x()
            dy = pos.y() - center.y()
            angle = math.radians(-rotation)
            local_x = dx * math.cos(angle) - dy * math.sin(angle)
            local_y = dx * math.sin(angle) + dy * math.cos(angle)
            local_rect = QRectF(-rect.width() / 2.0, -rect.height() / 2.0, rect.width(), rect.height())
            if local_rect.contains(local_x, local_y): return True
        elif item['type'] == 'image':
            if len(item.get('points', [])) >= 4:
                poly = QPolygonF(item['points'])
                if poly.containsPoint(pos, Qt.OddEvenFill):
                    return True
        return False

    def show_text_font_menu(self, item, pos):
        menu = QMenu(self)
        menu.setStyleSheet(self.main_window.styleSheet())
        tr = self.main_window.translations[self.main_window.lang]

        font_submenu = menu.addMenu(tr["font"])
        current_font = item.get('font_family', 'Arial')

        db = QFontDatabase()
        for family in db.families():
            act = QAction(family, font_submenu)
            act.setCheckable(True)
            act.setChecked(family == current_font)
            act.triggered.connect(lambda checked, f=family, it=item: self.change_text_font(it, f))
            font_submenu.addAction(act)

        menu.exec_(self.mapToGlobal(pos))

    def change_text_font(self, item, font_family):
        self.save_state()
        item['font_family'] = font_family
        self.rebuild_canvas()
        self.update()

    def get_pixel_color(self, global_pos):
        try:
            hdc = _u32.GetDC(None)
            r_sum, g_sum, b_sum = 0, 0, 0
            count = 0
            for x in range(global_pos.x() - 1, global_pos.x() + 2):
                for y in range(global_pos.y() - 1, global_pos.y() + 2):
                    color_ref = _gdi32.GetPixel(hdc, x, y)
                    if color_ref != 0xFFFFFFFF:
                        r_sum += color_ref & 0xFF
                        g_sum += (color_ref >> 8) & 0xFF
                        b_sum += (color_ref >> 16) & 0xFF
                        count += 1
            _u32.ReleaseDC(None, hdc)
            if count > 0:
                return QColor(r_sum // count, g_sum // count, b_sum // count, 255)
        except Exception:
            pass
        return QColor(Qt.white)

    def grab_screen_rect(self, global_rect):
        try:
            screen = QApplication.screenAt(global_rect.center())
            if not screen: screen = QApplication.primaryScreen()
        except:
            screen = QApplication.primaryScreen()

        geo = screen.geometry()
        sx = global_rect.x() - geo.x()
        sy = global_rect.y() - geo.y()
        return screen.grabWindow(0, sx, sy, global_rect.width(), global_rect.height())

    def capture_composite(self, rect):
        global_top_left = self.mapToGlobal(rect.topLeft())
        global_bottom_right = self.mapToGlobal(rect.bottomRight())
        global_rect = QRect(global_top_left, global_bottom_right).normalized()

        self.is_capturing = True
        self.hide()
        QApplication.processEvents()

        desktop_pixmap = self.grab_screen_rect(global_rect)

        overlay_pixmap = QPixmap(rect.size())
        overlay_pixmap.fill(Qt.transparent)
        ov = QPainter(overlay_pixmap)
        ov.setRenderHint(QPainter.Antialiasing)
        ov.setRenderHint(QPainter.SmoothPixmapTransform)
        ov.translate(-rect.topLeft())
        self.render_drawings(ov, is_capturing=True)
        ov.end()

        self.show()
        self.main_window.force_topmost_all()
        QApplication.processEvents()
        self.is_capturing = False

        p = QPainter(desktop_pixmap)
        p.drawPixmap(0, 0, overlay_pixmap)
        p.end()

        return desktop_pixmap

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if (self.tool != "cursor" or self.laser_mode) and not self.is_capturing:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))
        if not self.is_hidden:
            self.render_drawings(painter)
            if self.tool != "screenshot" and not self.is_capturing:
                for item in self.drawings:
                    if item['type'] == 'image' and item.get('selected', False):
                        pts = item['points']
                        if len(pts) >= 4:
                            poly_pts = [pts[0], pts[1], pts[2], pts[3], pts[0]]
                            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
                            painter.drawPolyline(QPolygonF(poly_pts))
                            for i, corner in enumerate(['TL', 'TR', 'BR', 'BL']):
                                handle = self.get_handle_rect(item['points'][i])
                                if corner == 'TR':
                                    painter.setBrush(QColor(255, 165, 0))
                                    painter.setPen(QPen(Qt.white, 1))
                                    painter.drawRect(handle)
                                else:
                                    painter.setBrush(QColor(0, 120, 215))
                                    painter.setPen(QPen(Qt.white, 1))
                                    painter.drawRect(handle)
                for item in self.drawings:
                    if item['type'] == 'text' and item.get('show_handles', False):
                        corners = self.get_text_corners(item)
                        if len(corners) == 4:
                            painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
                            painter.setBrush(Qt.NoBrush)
                            painter.drawPolygon(QPolygonF(corners))
                            for i, pt in enumerate(corners):
                                handle = self.get_handle_rect(pt)
                                painter.setBrush(QColor(0, 120, 215))
                                painter.setPen(QPen(Qt.white, 1))
                                painter.drawRect(handle)
            if self.tool == "screenshot" and self.screenshot_start_pos is not None and not self.is_capturing:
                rect = QRect(self.screenshot_start_pos, self.screenshot_end_pos).normalized()
                mask_color = QColor(0, 0, 0, 150)
                painter.fillRect(QRect(0, 0, self.width(), rect.y()), mask_color)
                painter.fillRect(QRect(0, rect.bottom() + 1, self.width(), self.height() - rect.bottom() - 1),
                                 mask_color)
                painter.fillRect(QRect(0, rect.y(), rect.x(), rect.height()), mask_color)
                painter.fillRect(QRect(rect.right() + 1, rect.y(), self.width() - rect.right() - 1, rect.height()),
                                 mask_color)
                painter.setPen(QPen(QColor(0, 120, 215), 2))
                painter.drawRect(rect)
            elif self.tool == "ai" and not self.is_capturing:
                if self.ai_is_lasso and self.ai_lasso_path is not None:
                    painter.setPen(QPen(QColor(0, 120, 215), 2))
                    painter.setBrush(QColor(0, 120, 215, 50))
                    painter.drawPath(self.ai_lasso_path)
                elif self.ai_start_pos is not None:
                    rect = QRect(self.ai_start_pos, self.ai_end_pos).normalized()
                    mask_color = QColor(0, 0, 0, 150)
                    painter.fillRect(QRect(0, 0, self.width(), rect.y()), mask_color)
                    painter.fillRect(QRect(0, rect.bottom() + 1, self.width(), self.height() - rect.bottom() - 1),
                                     mask_color)
                    painter.fillRect(QRect(0, rect.y(), rect.x(), rect.height()), mask_color)
                    painter.fillRect(QRect(rect.right() + 1, rect.y(), self.width() - rect.right() - 1, rect.height()),
                                     mask_color)
                    painter.setPen(QPen(QColor(0, 120, 215), 2))
                    painter.drawRect(rect)

    def mousePressEvent(self, event):
        if self.is_capturing: return

        if event.button() not in (Qt.LeftButton, Qt.RightButton): return
        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.commit_text()
            self.main_window.set_normal_cursor()
            self.last_pos = None
            self.current_item = None
            self.moving_image = None
            self.resizing_image = None
            self.moving_text = None
            self.transforming_text = None
            self.screenshot_start_pos = None
            self.ai_start_pos = None
            self.ai_lasso_path = None
            self.ai_is_lasso = False
            return

        if event.button() == Qt.LeftButton:
            self.current_color = self.left_color
        elif event.button() == Qt.RightButton:
            self.current_color = self.right_color

        if self.is_hidden and self.tool != "screenshot": return

        if self.tool in ("pen", "eraser"):
            if self.tool == "eraser" and event.button() == Qt.RightButton:
                for item in reversed(self.drawings):
                    if self.hit_test_item(item, event.pos()):
                        self.save_state()
                        self.drawings.remove(item)
                        self.rebuild_canvas()
                        self.update()
                        return
                return

            self.save_state()
            self.deselect_all_images()

            item_type = self.tool
            width = self.eraser_width if self.tool == "eraser" else self.pen_width
            path = QPainterPath()
            path.moveTo(event.pos())
            self.current_item = {'type': item_type, 'color': self.current_color, 'width': width, 'path': path,
                                 'layer': 'middle'}
            if item_type == 'pen':
                # Excalidraw-перо: сырые точки, рендер с переменной толщиной
                self.current_item['points'] = [QPointF(event.pos())]
                self.current_item['seed'] = random.randrange(1 << 30)
                self.current_item['live'] = True
            else:
                p = QPainter(self.canvas)
                p.setRenderHint(QPainter.Antialiasing)
                self.draw_item_on_painter(p, self.current_item)
                p.end()
            self.update()

        elif self.tool == "shape":
            self.save_state()
            self.deselect_all_images()
            self.shape_start_pos = event.pos()
            self.shape_end_pos = event.pos()
            path = self.get_shape_path(self.shape_type, self.shape_start_pos, self.shape_end_pos, self.pen_width)
            self.current_item = {'type': 'shape', 'shape_type': self.shape_type, 'color': self.current_color,
                                 'width': self.pen_width, 'path': path, 'layer': 'middle',
                                 'p0': QPointF(self.shape_start_pos), 'p1': QPointF(self.shape_end_pos),
                                 'seed': random.randrange(1 << 30)}
            self.update()

        elif self.tool == "screenshot":
            self.screenshot_start_pos = event.pos()
            self.screenshot_end_pos = event.pos()
            self.update()

        elif self.tool == "ai":
            self.ai_is_lasso = (event.button() == Qt.RightButton)
            global_pos = self.mapToGlobal(event.pos())
            self.ai_bg_color = self.get_pixel_color(global_pos)

            if self.ai_is_lasso:
                self.ai_lasso_path = QPainterPath()
                self.ai_lasso_path.moveTo(event.pos())
            else:
                self.ai_start_pos = event.pos()
                self.ai_end_pos = event.pos()
            self.update()

        elif self.tool == "text":
            if event.button() in (Qt.LeftButton, Qt.RightButton):
                self.suppress_select_switch = True
                self.commit_text()
                self.suppress_select_switch = False

                if self.tool != "text": return

                self.save_state()
                self.deselect_all_images()
                self.text_color = self.current_color
                self.text_input = QLineEdit(self)
                self.text_input.setStyleSheet(
                    f"QLineEdit {{ background: rgba(255, 255, 255, 180); border: 1px dashed gray; color: {self.text_color.name()}; font-size: {self.text_font_size}px; font-family: '{self.main_window.active_text_font_family}'; padding: 2px; }}")
                self.text_input.adjustSize()
                h = self.text_input.height()
                self.text_input.move(event.pos().x(), event.pos().y() - h // 2)
                self.text_input.show()
                self.text_input.setFocus()
                self.text_input.editingFinished.connect(self.commit_text)

        elif self.tool == "select":
            for item in reversed(self.drawings):
                if item['type'] == 'text' and item.get('show_handles', False):
                    corners = self.get_text_corners(item)
                    for i, pt in enumerate(corners):
                        if self.get_handle_rect(pt).contains(event.pos()):
                            self.save_state()
                            self.transforming_text = item
                            self.text_transform_start = {
                                'mouse': event.pos(),
                                'rotation': item.get('rotation', 0),
                                'font_size': item['font_size']
                            }
                            return

            for item in reversed(self.drawings):
                if item['type'] == 'text':
                    if self.hit_test_item(item, event.pos()):
                        if event.button() == Qt.RightButton:
                            menu = QMenu(self)
                            menu.setStyleSheet(self.main_window.styleSheet())
                            tr = self.main_window.translations[self.main_window.lang]
                            delete_action = menu.addAction(tr["delete"])
                            rotate_action = menu.addAction(tr["rotate"])

                            menu.addSeparator()
                            font_action = menu.addAction(tr["font"])
                            change_color_action = menu.addAction(tr["color"])

                            menu.addSeparator()
                            front_action = menu.addAction(tr["front"])
                            middle_action = menu.addAction(tr["middle"])
                            back_action = menu.addAction(tr["back"])

                            action = menu.exec_(self.mapToGlobal(event.pos()))
                            if action == delete_action:
                                self.save_state()
                                self.drawings.remove(item)
                                self.rebuild_canvas()
                                self.update()
                            elif action == rotate_action:
                                self.deselect_all_images()
                                item['show_handles'] = True
                                self.update()
                            elif action == font_action:
                                self.main_window.choose_text_font(item)
                            elif action == change_color_action:
                                self.main_window.choose_text_color_for_item(item)
                            elif action == front_action:
                                self.save_state()
                                item['layer'] = 'front'
                                self.rebuild_canvas()
                                self.update()
                            elif action == middle_action:
                                self.save_state()
                                item['layer'] = 'middle'
                                self.rebuild_canvas()
                                self.update()
                            elif action == back_action:
                                self.save_state()
                                item['layer'] = 'back'
                                self.rebuild_canvas()
                                self.update()
                            return
                        elif event.button() == Qt.LeftButton:
                            self.save_state()
                            if event.modifiers() & Qt.ControlModifier:
                                new_item = item.copy()
                                new_item['pos'] = QPointF(item['pos'].x() + 20, item['pos'].y() + 20)
                                self.drawings.append(new_item)
                                self.deselect_all_images()
                                new_item['selected'] = True
                                self.moving_text = new_item
                                self.move_offset = event.pos() - new_item['pos']
                            else:
                                self.deselect_all_images()
                                item['selected'] = True
                                self.moving_text = item
                                self.move_offset = event.pos() - item['pos']
                            self.update()
                            return

            if event.button() in (Qt.LeftButton, Qt.RightButton):
                for item in reversed(self.drawings):
                    if item['type'] == 'image' and item.get('selected', False):
                        for i, corner_name in enumerate(['TL', 'TR', 'BR', 'BL']):
                            if self.get_handle_rect(item['points'][i]).contains(event.pos()):
                                self.save_state()
                                self.resizing_image = item
                                self.resizing_handle = corner_name
                                self.resize_start_pos = event.pos()
                                self.resize_start_points = [QPointF(p) for p in item['points']]
                                self.resize_button = event.button()
                                return

            for item in reversed(self.drawings):
                if item['type'] == 'image' and len(item['points']) >= 4:
                    poly = QPolygonF(item['points'])
                    if poly.containsPoint(event.pos(), Qt.OddEvenFill):
                        if event.button() == Qt.LeftButton:
                            self.save_state()
                            if event.modifiers() & Qt.ControlModifier:
                                new_item = item.copy()
                                new_item['pixmap'] = item['pixmap'].copy()
                                shift = QPointF(20, 20)
                                new_item['points'] = [p + shift for p in item['points']]
                                self.drawings.append(new_item)
                                self.deselect_all_images()
                                new_item['selected'] = True
                                self.moving_image = new_item
                                self.move_offset = event.pos() - new_item['points'][0]
                            else:
                                self.deselect_all_images()
                                item['selected'] = True
                                self.moving_image = item
                                if self.active_folder_item != item:
                                    self.active_folder_item = None
                                    self.folder_files = []
                                    self.folder_index = -1
                                self.move_offset = event.pos() - item['points'][0]
                            self.update()
                            return
                        elif event.button() == Qt.RightButton:
                            self.deselect_all_images()
                            item['selected'] = True
                            if self.active_folder_item != item:
                                self.active_folder_item = None
                                self.folder_files = []
                                self.folder_index = -1
                            self.update()
                            menu = QMenu(self)
                            menu.setStyleSheet(self.main_window.styleSheet())
                            tr = self.main_window.translations[self.main_window.lang]
                            delete_action = menu.addAction(tr["delete"])
                            menu.addSeparator()
                            front_action = menu.addAction(tr["front"])
                            middle_action = menu.addAction(tr["middle"])
                            back_action = menu.addAction(tr["back"])
                            menu.addSeparator()
                            remove_bg_action = menu.addAction(tr["remove_bg"])
                            remove_clicked_color_action = menu.addAction(tr["remove_clicked_color"])
                            save_as_action = menu.addAction(tr["save_as"])
                            action = menu.exec_(self.mapToGlobal(event.pos()))
                            if action == delete_action:
                                self.save_state()
                                self.drawings.remove(item)
                                self.update()
                            elif action == front_action:
                                self.save_state()
                                item['layer'] = 'front'
                                self.update()
                            elif action == middle_action:
                                self.save_state()
                                item['layer'] = 'middle'
                                self.update()
                            elif action == back_action:
                                self.save_state()
                                item['layer'] = 'back'
                                self.update()
                            elif action == remove_bg_action:
                                self.save_state()
                                processed_pixmap = self.main_window.remove_chart_background(item['pixmap'],
                                                                                            threshold=20)
                                if not processed_pixmap.isNull():
                                    item['pixmap'] = processed_pixmap
                                    if item == self.active_folder_item:
                                        self.folder_pixmaps[self.folder_index] = processed_pixmap
                                    self.update()
                            elif action == remove_clicked_color_action:
                                local_pos = self.get_pixmap_coords(item, event.pos())
                                if local_pos:
                                    self.save_state()
                                    processed_pixmap = self.main_window.remove_color_at_pos(item['pixmap'], local_pos,
                                                                                            threshold=20)
                                    if not processed_pixmap.isNull():
                                        item['pixmap'] = processed_pixmap
                                        if item == self.active_folder_item:
                                            self.folder_pixmaps[self.folder_index] = processed_pixmap
                                        self.update()
                            elif action == save_as_action:
                                self.main_window.save_image_as(item['pixmap'])
                            return

            if event.button() == Qt.LeftButton:
                if self.active_folder_item:
                    self.active_folder_item = None
                    self.folder_files = []
                    self.folder_index = -1
                    self.folder_pixmaps = {}
                self.deselect_all_images()

    def commit_text(self):
        if not self.text_input: return
        try:
            self.text_input.editingFinished.disconnect()
        except TypeError:
            pass
        text = self.text_input.text()
        if text:
            self.save_state()
            pos = self.text_input.pos()

            font = QFont(self.main_window.active_text_font_family)
            font.setPixelSize(self.text_font_size)
            font.setBold(True)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(text)
            center = QPointF(pos.x() + rect.width() / 2.0, pos.y() + rect.height() / 2.0)

            item = {
                'type': 'text',
                'color': self.text_color,
                'font_size': self.text_font_size,
                'pos': center,
                'text': text,
                'font_family': self.main_window.active_text_font_family,
                'rotation': 0,
                'show_handles': False,
                'selected': False
            }

            self.drawings.append(item)
            self.rebuild_canvas()

            if not getattr(self, 'suppress_select_switch', False):
                self.tool = "select"
                self.deselect_all_images()
                item['selected'] = True
                self.update_cursor()
                self.update()
        self.text_input.deleteLater()
        self.text_input = None
        self.text_color = None

    def mouseMoveEvent(self, event):
        if self.is_capturing: return

        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.last_pos = None
            self.current_item = None
            self.moving_image = None
            self.resizing_image = None
            self.moving_text = None
            self.transforming_text = None
            self.screenshot_start_pos = None
            self.ai_start_pos = None
            self.ai_lasso_path = None
            self.ai_is_lasso = False
            return

        if not (event.buttons() & (Qt.LeftButton | Qt.RightButton)): return
        if self.is_hidden and self.tool != "screenshot": return

        if self.current_item:
            if self.current_item['type'] == 'eraser':
                self.current_item['path'].lineTo(event.pos())
                p = QPainter(self.canvas)
                p.setRenderHint(QPainter.Antialiasing)
                self.draw_item_on_painter(p, self.current_item)
                p.end()
                padding = self.current_item['width'] + 10
                rect = QRect(self.last_pos if self.last_pos else event.pos(), event.pos()).normalized()
                self.update(rect.adjusted(-padding, -padding, padding, padding))
                self.last_pos = event.pos()
            elif self.current_item['type'] == 'pen':
                pts = self.current_item.setdefault('points', [])
                pt = QPointF(event.pos())
                if not pts or math.hypot(pt.x() - pts[-1].x(), pt.y() - pts[-1].y()) >= 1.2:
                    pts.append(pt)
                    padding = int(self.current_item['width'] * 2 + 14)
                    rect = QRect(self.last_pos if self.last_pos else event.pos(), event.pos()).normalized()
                    self.update(rect.adjusted(-padding, -padding, padding, padding))
                self.last_pos = event.pos()
            elif self.current_item['type'] == 'shape':
                self.shape_end_pos = event.pos()
                self.current_item['path'] = self.get_shape_path(self.current_item['shape_type'], self.shape_start_pos,
                                                                self.shape_end_pos, self.pen_width)
                self.current_item['p1'] = QPointF(event.pos())
                self.update()
        elif self.screenshot_start_pos is not None:
            self.screenshot_end_pos = event.pos()
            self.update()
        elif self.tool == "ai" and self.ai_is_lasso and self.ai_lasso_path is not None:
            self.ai_lasso_path.lineTo(event.pos())
            self.update()
        elif self.ai_start_pos is not None:
            self.ai_end_pos = event.pos()
            self.update()

        elif self.transforming_text:
            if not (event.buttons() & Qt.LeftButton): return
            item = self.transforming_text
            center = item['pos']
            start_mouse = self.text_transform_start['mouse']

            start_vec = start_mouse - center
            curr_vec = event.pos() - center

            start_dist = math.hypot(start_vec.x(), start_vec.y())
            curr_dist = math.hypot(curr_vec.x(), curr_vec.y())

            if start_dist < 1.0: return

            start_angle = math.degrees(math.atan2(start_vec.y(), start_vec.x()))
            curr_angle = math.degrees(math.atan2(curr_vec.y(), curr_vec.x()))

            delta_angle = curr_angle - start_angle
            item['rotation'] = self.text_transform_start['rotation'] + (delta_angle * 0.5)

            scale = curr_dist / start_dist
            sensitive_scale = 1.0 + (scale - 1.0) * 0.5
            new_size = int(self.text_transform_start['font_size'] * sensitive_scale)
            item['font_size'] = max(4, new_size)

            self.rebuild_canvas()
            self.update()

        elif self.moving_text:
            if not (event.buttons() & Qt.LeftButton): return
            new_pos = event.pos() - self.move_offset
            self.moving_text['pos'] = new_pos
            self.rebuild_canvas()
            self.update()

        elif self.moving_image:
            if not (event.buttons() & Qt.LeftButton): return
            new_tl = event.pos() - self.move_offset
            shift = new_tl - self.moving_image['points'][0]
            self.moving_image['points'] = [p + shift for p in self.moving_image['points']]
            self.update()

        elif self.resizing_image:
            if not (event.buttons() & (Qt.LeftButton | Qt.RightButton)): return
            delta = event.pos() - self.resize_start_pos
            item = self.resizing_image
            pts = self.resize_start_points
            if len(pts) < 4: return
            tl, tr, br, bl = pts[0], pts[1], pts[2], pts[3]
            try:
                if self.resize_button == Qt.LeftButton and self.resizing_handle == 'TR':
                    vx = tr.x() - tl.x()
                    vy = tr.y() - tl.y()
                    start_w = math.hypot(vx, vy)
                    if start_w == 0: start_w = 1.0
                    proj = (delta.x() * vx + delta.y() * vy) / start_w
                    new_w = start_w + proj
                    if new_w < 20: new_w = 20
                    scale = new_w / start_w
                    new_tr = QPointF(tl.x() + vx * scale, tl.y() + vy * scale)
                    new_bl = QPointF(tl.x() + (bl.x() - tl.x()) * scale, tl.y() + (bl.y() - tl.y()) * scale)
                    new_br = QPointF(new_tr.x() + (new_bl.x() - tl.x()), new_tr.y() + (new_bl.y() - tl.y()))
                    item['points'] = [tl, new_tr, new_br, new_bl]
                elif self.resize_button == Qt.RightButton:
                    new_tl = QPointF(tl.x() + delta.x(), tl.y() + delta.y())
                    new_tr = QPointF(tr.x() + delta.x(), tr.y() + delta.y())
                    new_br = QPointF(br.x() + delta.x(), br.y() + delta.y())
                    new_bl = QPointF(bl.x() + delta.x(), bl.y() + delta.y())
                    if self.resizing_handle == 'TR':
                        item['points'] = [tl, new_tr, new_br, bl]
                    elif self.resizing_handle == 'BR':
                        item['points'] = [tl, tr, new_br, new_bl]
                    elif self.resizing_handle == 'BL':
                        item['points'] = [tl, tr, new_br, new_bl]
                    elif self.resizing_handle == 'TL':
                        item['points'] = [new_tl, tr, br, new_bl]
                else:
                    if self.resizing_handle == 'BR':
                        new_br = QPointF(br.x() + delta.x(), br.y() + delta.y())
                        item['points'] = [tl, QPointF(new_br.x(), tl.y()), new_br, QPointF(tl.x(), new_br.y())]
                    elif self.resizing_handle == 'TL':
                        new_tl = QPointF(tl.x() + delta.x(), tl.y() + delta.y())
                        item['points'] = [new_tl, QPointF(br.x(), new_tl.y()), br, QPointF(new_tl.x(), br.y())]
                    elif self.resizing_handle == 'BL':
                        new_bl = QPointF(bl.x() + delta.x(), bl.y() + delta.y())
                        item['points'] = [QPointF(new_bl.x(), tr.y()), tr, QPointF(tr.x(), new_bl.y()), new_bl]
                    elif self.resizing_handle == 'TR':
                        new_tr = QPointF(tr.x() + delta.x(), tr.y() + delta.y())
                        item['points'] = [QPointF(bl.x(), new_tr.y()), new_tr, QPointF(new_tr.x(), bl.y()), bl]
                self.update()
            except Exception:
                pass

    def mouseReleaseEvent(self, event):
        if self.is_capturing: return

        if event.button() not in (Qt.LeftButton, Qt.RightButton): return

        if self.tool == "screenshot" and self.screenshot_start_pos is not None:
            rect = QRect(self.screenshot_start_pos, self.screenshot_end_pos).normalized()
            self.screenshot_start_pos = None
            self.screenshot_end_pos = None
            if rect.width() > 5 and rect.height() > 5:
                screenshot_pixmap = self.capture_composite(rect)

                if not screenshot_pixmap.isNull():
                    QApplication.clipboard().setPixmap(screenshot_pixmap)
                    if event.button() == Qt.LeftButton:
                        try:
                            temp_dir = tempfile.gettempdir()
                            filename = f"paste_pen_{int(time.time())}.png"
                            file_path = os.path.join(temp_dir, filename)
                            screenshot_pixmap.save(file_path, "PNG")
                            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                        except Exception:
                            pass
            self.update()
            self.set_tool("cursor")
            return

        if self.tool == "ai" and (self.ai_start_pos is not None or self.ai_lasso_path is not None):
            if self.ai_is_lasso and self.ai_lasso_path is not None:
                self.ai_lasso_path.closeSubpath()
                rect = self.ai_lasso_path.boundingRect().toRect().normalized()
                if rect.width() > 5 and rect.height() > 5:
                    screenshot_pixmap = self.capture_composite(rect)

                    if not screenshot_pixmap.isNull():
                        masked_pixmap = QPixmap(screenshot_pixmap.size())
                        masked_pixmap.fill(Qt.transparent)
                        local_path = QTransform().fromTranslate(-rect.x(), -rect.y()).map(self.ai_lasso_path)
                        p = QPainter(masked_pixmap)
                        p.setRenderHint(QPainter.Antialiasing)
                        p.setClipPath(local_path)
                        p.drawPixmap(0, 0, screenshot_pixmap)
                        p.end()

                        self.save_state()
                        self.deselect_all_images()
                        bg_item = {
                            'type': 'shape',
                            'shape_type': 'custom',
                            'color': QColor(self.ai_bg_color),
                            'width': 1,
                            'path': QPainterPath(self.ai_lasso_path),
                            'layer': 'back',
                            'fill': True,
                            'is_ai_bg': True
                        }
                        self.drawings.append(bg_item)
                        points = [
                            QPointF(rect.x(), rect.y()),
                            QPointF(rect.x() + rect.width(), rect.y()),
                            QPointF(rect.x() + rect.width(), rect.y() + rect.height()),
                            QPointF(rect.x(), rect.y() + rect.height())
                        ]
                        img_item = {
                            'type': 'image',
                            'pixmap': masked_pixmap,
                            'points': points,
                            'selected': True,
                            'layer': 'back'
                        }
                        self.drawings.append(img_item)
                        self.rebuild_canvas()
            else:
                rect = QRect(self.ai_start_pos, self.ai_end_pos).normalized()
                if rect.width() > 5 and rect.height() > 5:
                    screenshot_pixmap = self.capture_composite(rect)

                    if not screenshot_pixmap.isNull():
                        self.save_state()
                        self.deselect_all_images()
                        bg_rect_path = QPainterPath()
                        bg_rect_path.addRect(QRectF(rect.topLeft(), rect.bottomRight()))
                        bg_item = {
                            'type': 'shape',
                            'shape_type': 'rect',
                            'color': QColor(self.ai_bg_color),
                            'width': 1,
                            'path': bg_rect_path,
                            'layer': 'back',
                            'fill': True,
                            'is_ai_bg': True
                        }
                        self.drawings.append(bg_item)
                        points = [
                            QPointF(rect.x(), rect.y()),
                            QPointF(rect.x() + rect.width(), rect.y()),
                            QPointF(rect.x() + rect.width(), rect.y() + rect.height()),
                            QPointF(rect.x(), rect.y() + rect.height())
                        ]
                        img_item = {
                            'type': 'image',
                            'pixmap': screenshot_pixmap,
                            'points': points,
                            'selected': True,
                            'layer': 'back'
                        }
                        self.drawings.append(img_item)
                        self.rebuild_canvas()

            self.ai_start_pos = None
            self.ai_end_pos = None
            self.ai_lasso_path = None
            self.ai_is_lasso = False
            self.ai_bg_color = QColor(255, 255, 255)
            self.set_tool("select")
            return

        if self.current_item:
            if self.current_item['type'] == 'shape' and self.shape_start_pos == self.shape_end_pos:
                self.current_item = None
                self.update()
                return
            self.drawings.append(self.current_item)
            if self.current_item['type'] in ('shape', 'pen'):
                if self.current_item['type'] == 'pen':
                    self.current_item['live'] = False
                    if self.current_item.get('points'):
                        self.current_item['path'] = _ex_centerline_path(self.current_item['points'])
                p = QPainter(self.canvas)
                p.setRenderHint(QPainter.Antialiasing)
                self.draw_item_on_painter(p, self.current_item)
                p.end()
            self.current_item = None
            self.last_pos = None
            self.update()
        self.moving_image = None
        self.resizing_image = None
        self.moving_text = None
        self.transforming_text = None

    def wheelEvent(self, event):
        if self.tool == "select":
            target_item = None
            for item in reversed(self.drawings):
                if item.get('selected', False):
                    target_item = item
                    break

            if self.active_folder_item and (event.modifiers() & Qt.ShiftModifier):
                delta = event.angleDelta().y()
                if delta > 0:
                    self.folder_index = (self.folder_index - 1) % len(self.folder_files)
                else:
                    self.folder_index = (self.folder_index + 1) % len(self.folder_files)

                if self.folder_index in self.folder_pixmaps:
                    new_pixmap = self.folder_pixmaps[self.folder_index]
                else:
                    file_path = self.folder_files[self.folder_index]
                    new_pixmap = QPixmap(file_path)
                    if not new_pixmap.isNull():
                        if self.folder_remove_bg:
                            new_pixmap = self.main_window.remove_chart_background(new_pixmap, threshold=20)

                        if new_pixmap.width() > 1500 or new_pixmap.height() > 1500:
                            new_pixmap = new_pixmap.scaled(1500, 1500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    self.folder_pixmaps[self.folder_index] = new_pixmap

                if not new_pixmap.isNull():
                    old_tl = self.active_folder_item['points'][0]
                    w = new_pixmap.width()
                    h = new_pixmap.height()

                    self.active_folder_item['points'] = [
                        QPointF(old_tl.x(), old_tl.y()),
                        QPointF(old_tl.x() + w, old_tl.y()),
                        QPointF(old_tl.x() + w, old_tl.y() + h),
                        QPointF(old_tl.x(), old_tl.y() + h)
                    ]
                    self.active_folder_item['pixmap'] = new_pixmap
                    self.update()
                event.accept()
                return

            if target_item:
                self.save_state()
                delta = event.angleDelta().y()
                is_ctrl = event.modifiers() & Qt.ControlModifier

                if is_ctrl:
                    scale_factor = 1.05 if delta > 0 else 0.95
                    if target_item['type'] == 'image':
                        p0, p1 = target_item['points'][0], target_item['points'][1]
                        w = math.hypot(p1.x() - p0.x(), p1.y() - p0.y())
                        if w * scale_factor < 5 and scale_factor < 1.0:
                            event.accept()
                            return

                        center = QPointF(
                            sum(p.x() for p in target_item['points']) / 4.0,
                            sum(p.y() for p in target_item['points']) / 4.0
                        )
                        new_points = []
                        for p in target_item['points']:
                            dx = p.x() - center.x()
                            dy = p.y() - center.y()
                            new_points.append(QPointF(center.x() + dx * scale_factor, center.y() + dy * scale_factor))
                        target_item['points'] = new_points
                    elif target_item['type'] == 'text':
                        new_size = max(4, int(target_item['font_size'] * scale_factor))
                        if delta > 0 and new_size <= target_item['font_size']:
                            new_size = target_item['font_size'] + 1
                        target_item['font_size'] = new_size
                else:
                    angle_deg = 2.5 if delta < 0 else -2.5
                    angle_rad = math.radians(angle_deg)
                    cos_a = math.cos(angle_rad)
                    sin_a = math.sin(angle_rad)

                    if target_item['type'] == 'image':
                        center = QPointF(
                            sum(p.x() for p in target_item['points']) / 4.0,
                            sum(p.y() for p in target_item['points']) / 4.0
                        )
                        new_points = []
                        for p in target_item['points']:
                            dx = p.x() - center.x()
                            dy = p.y() - center.y()
                            new_x = center.x() + (dx * cos_a - dy * sin_a)
                            new_y = center.y() + (dx * sin_a + dy * cos_a)
                            new_points.append(QPointF(new_x, new_y))
                        target_item['points'] = new_points
                    elif target_item['type'] == 'text':
                        target_item['rotation'] = target_item.get('rotation', 0) + angle_deg

                self.rebuild_canvas()
                self.update()
                event.accept()
                return

        super().wheelEvent(event)

    def insert_pixmap(self, pixmap):
        if pixmap.isNull(): return
        if pixmap.width() > 1500 or pixmap.height() > 1500:
            pixmap = pixmap.scaled(1500, 1500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        x = self.width() // 2 - pixmap.width() // 2
        y = self.height() // 2 - pixmap.height() // 2
        w = pixmap.width()
        h = pixmap.height()
        points = [QPointF(x, y), QPointF(x + w, y), QPointF(x + w, y + h), QPointF(x, y + h)]
        self.save_state()
        self.deselect_all_images()
        self.drawings.append({'type': 'image', 'pixmap': pixmap, 'points': points, 'selected': True, 'layer': 'back'})
        self.set_tool("select")
        self.update()

    def load_folder(self, folder_path, remove_bg=False):
        valid_ext = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
        files = []
        try:
            for f in sorted(os.listdir(folder_path)):
                if os.path.splitext(f)[1].lower() in valid_ext:
                    files.append(os.path.join(folder_path, f))
        except Exception:
            return False
        if not files:
            return False

        self.folder_files = files
        self.folder_index = 0
        self.folder_remove_bg = remove_bg
        self.folder_pixmaps = {}

        pixmap = QPixmap(files[0])
        if pixmap.isNull(): return False

        if self.folder_remove_bg:
            pixmap = self.main_window.remove_chart_background(pixmap, threshold=20)

        if pixmap.width() > 1500 or pixmap.height() > 1500:
            pixmap = pixmap.scaled(1500, 1500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        self.folder_pixmaps[0] = pixmap

        x = self.width() // 2 - pixmap.width() // 2
        y = self.height() // 2 - pixmap.height() // 2
        w = pixmap.width()
        h = pixmap.height()
        points = [QPointF(x, y), QPointF(x + w, y), QPointF(x + w, y + h), QPointF(x, y + h)]

        self.save_state()
        self.deselect_all_images()
        self.drawings.append({'type': 'image', 'pixmap': pixmap, 'points': points, 'selected': True, 'layer': 'back'})
        self.active_folder_item = self.drawings[-1]

        self.tool = "select"
        self.update_cursor()
        self.update()
        return True

    def clear_all(self):
        self.commit_text()
        self.save_state()
        self.canvas.fill(Qt.transparent)
        self.drawings = []
        self.active_folder_item = None
        self.folder_files = []
        self.folder_index = -1
        self.folder_pixmaps = {}
        self.update()

    def toggle_hide(self):
        self.is_hidden = not self.is_hidden
        self.update()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Paste Pen")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.overlay = OverlayWidget(self)
        self.is_closing = False
        self.drag_pos = None
        self.is_collapsed = False
        self.icons_only = False
        self.anim = None
        self.fixed_width = 150

        self.tray_icon = QSystemTrayIcon(self)
        tray_pixmap = QPixmap(32, 32)
        tray_pixmap.fill(Qt.transparent)
        painter = QPainter(tray_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QColor("#1e1e1e"))
        painter.setPen(QPen(QColor("#DAA520"), 2))
        painter.drawRoundedRect(2, 2, 28, 28, 6, 6)
        painter.setPen(QColor("#DAA520"))
        painter.setFont(QFont("Segoe UI", 14, QFont.Bold))
        painter.drawText(tray_pixmap.rect(), Qt.AlignCenter, "P")
        painter.end()
        self.tray_icon.setIcon(QIcon(tray_pixmap))
        self.tray_icon.setToolTip("Paste Pen")
        self.tray_icon.show()
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Показать/Скрыть панель")
        show_action.triggered.connect(self.toggle_collapse)
        exit_action = tray_menu.addAction("Выход")
        exit_action.triggered.connect(self.close_app)
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(
            lambda reason: self.toggle_collapse() if reason == QSystemTrayIcon.Trigger else None)

        self.settings = QSettings("PastePenApp", "PastePen")
        self.lang = self.settings.value("language", "EN", type=str)
        self.theme = self.settings.value("theme", "dark", type=str)
        self.icon_color = "white" if self.theme == "dark" else "#333333"

        self.shortcut_del = QShortcut("Delete", self)
        self.shortcut_del.activated.connect(self.overlay.delete_selected_item)
        self.shortcut_bsp = QShortcut("Backspace", self)
        self.shortcut_bsp.activated.connect(self.overlay.delete_selected_item)

        self.translations = {
            "RU": {
                "cursor": "Курсор", "pen": "Ручка", "shape": "Фигуры", "text": "Текст",
                "eraser": "Ластик", "color": "Цвет", "image": "Картинка", "select": "Выбор",
                "screenshot": "Скриншот", "delete": "Удалить",
                "front": "На передний план", "middle": "На средний план", "back": "На задний план",
                "undo": "Назад", "redo": "Вперёд", "hide": "Скрыть", "show": "Показать", "clear": "Очистить",
                "exit": "Выход",
                "width": "Толщина: {}", "size": "Размер: {}",
                "line": "Линия", "rect": "Прямоугольник", "ellipse": "Эллипс", "arrow": "Стрелка",
                "next_lang": "中", "current_lang": "РУ", "donate_tip": "Поддержать на Boosty",
                "cursor_tip": "ЛКМ+ПКМ - переключение на курсор из всех режимов\nПКМ - выбор лазерной указки",
                "pen_tip": "ЛКМ - режим рисования\nПКМ - выбор размера линий",
                "shape_tip": "ЛКМ - рисование фигур\nПКМ - выбор фигуры",
                "text_tip": "ЛКМ - вставка текста\nПКМ - выбор шрифта и размера",
                "eraser_tip": "ЛКМ - стирание линий, ПКМ - удаление объектов\nПКМ - выбор величины ластика",
                "image_tip": "ЛКМ - вставка из файла\nПКМ - выбор режима вставки",
                "select_tip": "ЛКМ - управление вставленным текстом и картинками\nCtrl +ЛКМ - копирование выбранного объекта\nКолёсико мыши - поворот объекта\nCtrl+колёсико мыши - увеличение/уменьшение объекта",
                "lang_tip": "ЛКМ - следующий язык\nПКМ - выбор языка",
                "theme_tip": "ЛКМ - скрыть/показать текст\nПКМ - выбор тёмной/светлой темы",
                "ai_tip": "При использовании с помощью ЛКМ - вырезает прямоугольную область\nПри использовании с помощью ПКМ - вырезает произвольную область",
                "color_tip": "ЛКМ - выбор цвета левой кнопки\nПКМ - выбор цвета правой кнопки",
                "paste_img": "Вставить из буфера", "paste_chart_img": "Вставить из буфера без фона",
                "insert_img_from_file": "Вставить из файла", "paste_img_no_bg": "Вставить из файла без фона",
                "insert_folder_wheel": "Вставить папку (Shift + колесико)",
                "insert_folder_no_bg_wheel": "Вставить папку без фона (Shift + колесико)",
                "no_img_clip": "В буфере обмена нет изображения.",
                "no_img_folder": "В выбранной папке нет изображений.",
                "theme_light": "Светлая тема", "theme_dark": "Тёмная тема",
                "normal_cursor": "Обычный курсор", "laser_cursor": "Лазерная указка",
                "laser_tip": "Курсор станет красной точкой.\n(Клики заблокированы до возврата на обычный курсор)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Сохранить как...", "remove_bg": "Убрать фон",
                "font": "Шрифт", "remove_clicked_color": "Удалить выбранный фон",
                "screenshot_tip": "При создании с помощью ЛКМ - копирование в буфер обмена и открытие файла\nПри создании с помощью ПКМ - только копирование в буфер обмена",
                "rotate": "Повернуть / Размер", "ai": "Смарт-скр."
            },
            "EN": {
                "cursor": "Cursor", "pen": "Pen", "shape": "Shapes", "text": "Text",
                "eraser": "Eraser", "color": "Color", "image": "Image", "select": "Select",
                "screenshot": "Screenshot", "delete": "Delete",
                "front": "Bring to Front", "middle": "Middle Layer", "back": "Send to Back",
                "undo": "Undo", "redo": "Redo", "hide": "Hide", "show": "Show", "clear": "Clear",
                "exit": "Exit",
                "width": "Width: {}", "size": "Size: {}",
                "line": "Line", "rect": "Rectangle", "ellipse": "Ellipse", "arrow": "Arrow",
                "next_lang": "РУ", "current_lang": "EN", "donate_tip": "Support on DonationAlerts",
                "cursor_tip": "LMB+RMB - switch to cursor from all modes\nRMB - select laser pointer",
                "pen_tip": "LMB - drawing mode\nRMB - select line size",
                "shape_tip": "LMB - draw shapes\nRMB - select shape",
                "text_tip": "LMB - insert text\nRMB - select font and size",
                "eraser_tip": "LMB - erase lines, RMB - delete objects\nRMB - select eraser size",
                "image_tip": "LMB - insert from file\nRMB - choose insertion mode",
                "select_tip": "LMB - manage inserted text and pictures\nCtrl + LMB - copy selected object\nMouse wheel - rotate object\nCtrl + mouse wheel - increase/decrease object",
                "lang_tip": "LMB - next language\nRMB - select language",
                "theme_tip": "LMB - hide/show text\nRMB - select dark/light theme",
                "ai_tip": "When using LMB - cuts out a rectangular area\nWhen using RMB - cuts out an arbitrary area",
                "color_tip": "LMB - select left button color\nRMB - select right button color",
                "paste_img": "Paste from clipboard", "paste_chart_img": "Paste from clipboard without background",
                "insert_img_from_file": "Insert from file", "paste_img_no_bg": "Insert from file without background",
                "insert_folder_wheel": "Insert folder (Shift + mouse wheel)",
                "insert_folder_no_bg_wheel": "Insert folder without background (Shift + mouse wheel)",
                "no_img_clip": "No image in clipboard.", "no_img_folder": "No images found in the selected folder.",
                "theme_light": "Light Theme", "theme_dark": "Dark Theme",
                "normal_cursor": "Normal Cursor", "laser_cursor": "Laser Pointer",
                "laser_tip": "Cursor becomes a red dot.\n(Clicks are blocked until returning to normal cursor)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Save As...", "remove_bg": "Remove background",
                "font": "Font", "remove_clicked_color": "Remove selected background",
                "screenshot_tip": "When creating with LMB - copy to clipboard and open file\nWhen creating with RMB - copy to clipboard only",
                "rotate": "Rotate / Resize", "ai": "Smart Cut"
            },
            "ZH": {
                "cursor": "光标", "pen": "画笔", "shape": "形状", "text": "文本",
                "eraser": "橡皮擦", "color": "颜色", "image": "图片", "select": "选择",
                "screenshot": "截图", "delete": "删除",
                "front": "置于顶层", "middle": "中间层", "back": "置于底层",
                "undo": "撤销", "redo": "重做", "hide": "隐藏", "show": "显示", "clear": "清除",
                "exit": "退出",
                "width": "粗细: {}", "size": "大小: {}",
                "line": "直线", "rect": "矩形", "ellipse": "椭圆", "arrow": "箭头",
                "next_lang": "ES", "current_lang": "中", "donate_tip": "在 DonationAlerts 上支持",
                "cursor_tip": "左键+右键 - 从所有模式切换到光标\n右键 - 选择激光笔",
                "pen_tip": "左键 - 绘图模式\n右键 - 选择线条大小",
                "shape_tip": "左键 - 绘制形状\n右键 - 选择形状",
                "text_tip": "左键 - 插入文本\n右键 - 选择字体和大小",
                "eraser_tip": "左键 - 擦除线条，右键 - 删除对象\n右键 - 选择橡皮擦大小",
                "image_tip": "左键 - 从文件插入\n右键 - 选择插入模式",
                "select_tip": "左键 - 管理插入的文本和图片\nCtrl + 左键 - 复制选定对象\n鼠标滚轮 - 旋转对象\nCtrl + 鼠标滚轮 - 放大/缩小对象",
                "lang_tip": "左键 - 下一个语言\n右键 - 选择语言",
                "theme_tip": "左键 - 隐藏/显示文本\n右键 - 选择深色/浅色主题",
                "ai_tip": "使用左键时 - 剪切矩形区域\n使用右键时 - 剪切任意区域",
                "color_tip": "左键 - 选择左键颜色\n右键 - 选择右键颜色",
                "paste_img": "从剪贴板粘贴", "paste_chart_img": "从剪贴板粘贴无背景",
                "insert_img_from_file": "从文件插入", "paste_img_no_bg": "从文件插入无背景图片",
                "insert_folder_wheel": "插入文件夹 (Shift + 鼠标滚轮)",
                "insert_folder_no_bg_wheel": "插入无背景文件夹 (Shift + 鼠标滚轮)",
                "no_img_clip": "剪贴板中没有图像。", "no_img_folder": "所选文件夹中没有图像。",
                "theme_light": "浅色主题", "theme_dark": "深色主题",
                "normal_cursor": "普通光标", "laser_cursor": "激光笔",
                "laser_tip": "光标变为红点。\n（在返回普通光标前点击被阻止）",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "另存为...", "remove_bg": "移除背景",
                "font": "字体", "remove_clicked_color": "删除所选背景",
                "screenshot_tip": "使用左键创建时 - 复制到剪贴板并打开文件\n使用右键创建时 - 仅复制到剪贴板",
                "rotate": "旋转 / 调整大小", "ai": "智能剪切"
            },
            "ES": {
                "cursor": "Cursor", "pen": "Lápiz", "shape": "Formas", "text": "Texto",
                "eraser": "Borrador", "color": "Color", "image": "Imagen", "select": "Seleccionar",
                "screenshot": "Captura", "delete": "Eliminar",
                "front": "Al frente", "middle": "Capa media", "back": "Al fondo",
                "undo": "Deshacer", "redo": "Rehacer", "hide": "Ocultar", "show": "Mostrar", "clear": "Limpiar",
                "exit": "Salir",
                "width": "Grosor: {}", "size": "Tamaño: {}",
                "line": "Línea", "rect": "Rectángulo", "ellipse": "Elipse", "arrow": "Flecha",
                "next_lang": "PT", "current_lang": "ES", "donate_tip": "Apoyar en DonationAlerts",
                "cursor_tip": "LMB+RMB - cambiar a cursor desde todos los modos\nRMB - seleccionar puntero láser",
                "pen_tip": "LMB - modo dibujo\nRMB - seleccionar tamaño de línea",
                "shape_tip": "LMB - dibujar formas\nRMB - seleccionar forma",
                "text_tip": "LMB - insertar texto\nRMB - seleccionar fuente y tamaño",
                "eraser_tip": "LMB - borrar líneas, RMB - eliminar objetos\nRMB - seleccionar tamaño de borrador",
                "image_tip": "LMB - insertar desde archivo\nRMB - seleccionar modo de inserción",
                "select_tip": "LMB - gestionar texto e imágenes insertados\nCtrl + LMB - copiar objeto seleccionado\nRueda del ratón - rotar objeto\nCtrl + rueda del ratón - aumentar/disminuir objeto",
                "lang_tip": "LMB - siguiente idioma\nRMB - seleccionar idioma",
                "theme_tip": "LMB - ocultar/mostrar texto\nRMB - seleccionar tema oscuro/claro",
                "ai_tip": "Al usar LMB - recorta un área rectangular\nAl usar RMB - recorta un área arbitraria",
                "color_tip": "LMB - seleccionar color del botón izquierdo\nRMB - seleccionar color del botón derecho",
                "paste_img": "Pegar del portapapeles", "paste_chart_img": "Pegar sin fondo",
                "insert_img_from_file": "Insertar desde archivo", "paste_img_no_bg": "Insertar sin fondo",
                "insert_folder_wheel": "Insertar carpeta (Shift + rueda del ratón)",
                "insert_folder_no_bg_wheel": "Insertar carpeta sin fondo (Shift + rueda del ratón)",
                "no_img_clip": "No hay imagen en el portapapeles.",
                "no_img_folder": "No se encontraron imágenes en la carpeta.",
                "theme_light": "Tema claro", "theme_dark": "Tema oscuro",
                "normal_cursor": "Cursor normal", "laser_cursor": "Puntero láser",
                "laser_tip": "El cursor se convierte en un punto rojo.\n(Los clics se bloquean hasta volver al cursor normal)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Guardar como...", "remove_bg": "Quitar fondo",
                "font": "Fuente", "remove_clicked_color": "Quitar color seleccionado",
                "screenshot_tip": "Al crear con LMB - copiar al portapapeles y abrir archivo\nAl crear con RMB - solo copiar al portapapeles",
                "rotate": "Rotar / Tamaño", "ai": "Corte Inteligente"
            },
            "PT": {
                "cursor": "Cursor", "pen": "Caneta", "shape": "Formas", "text": "Texto",
                "eraser": "Borracha", "color": "Cor", "image": "Imagem", "select": "Selecionar",
                "screenshot": "Captura", "delete": "Excluir",
                "front": "Para frente", "middle": "Camada média", "back": "Para trás",
                "undo": "Desfazer", "redo": "Refazer", "hide": "Ocultar", "show": "Mostrar", "clear": "Limpar",
                "exit": "Sair",
                "width": "Espessura: {}", "size": "Tamanho: {}",
                "line": "Linha", "rect": "Retângulo", "ellipse": "Elipse", "arrow": "Seta",
                "next_lang": "FR", "current_lang": "PT", "donate_tip": "Apoiar no DonationAlerts",
                "cursor_tip": "LMB+RMB - mudar para cursor de todos os modos\nRMB - selecionar ponteiro laser",
                "pen_tip": "LMB - modo desenho\nRMB - selecionar tamanho da linha",
                "shape_tip": "LMB - desenhar formas\nRMB - selecionar forma",
                "text_tip": "LMB - inserir texto\nRMB - selecionar fonte e tamanho",
                "eraser_tip": "LMB - apagar linhas, RMB - excluir objetos\nRMB - selecionar tamanho da borracha",
                "image_tip": "LMB - inserir do arquivo\nRMB - selecionar modo de inserção",
                "select_tip": "LMB - gerenciar texto e imagens inseridos\nCtrl + LMB - copiar objeto selecionado\nRoda do mouse - girar objeto\nCtrl + roda do mouse - aumentar/diminuir objeto",
                "lang_tip": "LMB - próximo idioma\nRMB - selecionar idioma",
                "theme_tip": "LMB - ocultar/mostrar texto\nRMB - selecionar tema escuro/claro",
                "ai_tip": "Ao usar LMB - recorta uma área retangular\nAo usar RMB - recorta uma área arbitrária",
                "color_tip": "LMB - selecionar cor do botão esquerdo\nRMB - selecionar cor do botão direito",
                "paste_img": "Colar da área de transferência", "paste_chart_img": "Colar sem fundo",
                "insert_img_from_file": "Inserir do arquivo", "paste_img_no_bg": "Inserir sem fundo",
                "insert_folder_wheel": "Inserir pasta (Shift + roda do mouse)",
                "insert_folder_no_bg_wheel": "Inserir pasta sem fundo (Shift + roda do mouse)",
                "no_img_clip": "Nenhuma imagem na área de transferência.",
                "no_img_folder": "Nenhuma imagem encontrada na pasta.",
                "theme_light": "Tema claro", "theme_dark": "Tema escuro",
                "normal_cursor": "Cursor normal", "laser_cursor": "Ponteiro laser",
                "laser_tip": "O cursor vira um ponto vermelho.\n(Cliques bloqueados até voltar ao cursor normal)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Salvar como...", "remove_bg": "Remover fundo",
                "font": "Fonte", "remove_clicked_color": "Remover cor selecionada",
                "screenshot_tip": "Ao criar com LMB - copiar para a área de transferência e abrir arquivo\nAo criar com RMB - apenas copiar para a área de transferência",
                "rotate": "Girar / Tamanho", "ai": "Corte Inteligente"
            },
            "FR": {
                "cursor": "Curseur", "pen": "Stylo", "shape": "Formes", "text": "Texte",
                "eraser": "Gomme", "color": "Couleur", "image": "Image", "select": "Sélectionner",
                "screenshot": "Capture", "delete": "Supprimer",
                "front": "Premier plan", "middle": "Plan moyen", "back": "Arrière-plan",
                "undo": "Annuler", "redo": "Rétablir", "hide": "Masquer", "show": "Afficher", "clear": "Effacer",
                "exit": "Quitter",
                "width": "Épaisseur: {}", "size": "Taille: {}",
                "line": "Ligne", "rect": "Rectangle", "ellipse": "Ellipse", "arrow": "Flèche",
                "next_lang": "DE", "current_lang": "FR", "donate_tip": "Soutenir sur DonationAlerts",
                "cursor_tip": "LMB+RMB - passer au curseur depuis tous les modes\nRMB - sélectionner le pointeur laser",
                "pen_tip": "LMB - mode dessin\nRMB - sélectionner la taille de la ligne",
                "shape_tip": "LMB - dessiner des formes\nRMB - sélectionner la forme",
                "text_tip": "LMB - insérer du texte\nRMB - sélectionner la police et la taille",
                "eraser_tip": "LMB - effacer les lignes, RMB - supprimer des objets\nRMB - sélectionner la taille de la gomme",
                "image_tip": "LMB - insérer à partir du fichier\nRMB - sélectionner le mode d'insertion",
                "select_tip": "LMB - gérer le texte et les images insérés\nCtrl + LMB - copier l'objet sélectionné\nMolette de la souris - faire pivoter l'objet\nCtrl + molette de la souris - augmenter/diminuer l'objet",
                "lang_tip": "LMB - langue suivante\nRMB - sélectionner la langue",
                "theme_tip": "LMB - masquer/afficher le texte\nRMB - sélectionner le thème sombre/clair",
                "ai_tip": "En utilisant LMB - découpe une zone rectangulaire\nEn utilisant RMB - découpe une zone arbitraire",
                "color_tip": "LMB - sélectionner la couleur du bouton gauche\nRMB - sélectionner la couleur du bouton droit",
                "paste_img": "Coller depuis le presse-papiens", "paste_chart_img": "Coller sans arrière-plan",
                "insert_img_from_file": "Insérer depuis un fichier", "paste_img_no_bg": "Insérer sans arrière-plan",
                "insert_folder_wheel": "Insérer un dossier (Shift + molette)",
                "insert_folder_no_bg_wheel": "Insérer un dossier sans arrière-plan (Shift + molette)",
                "no_img_clip": "Aucune image dans le presse-papiens.",
                "no_img_folder": "Aucune image trouvée dans le dossier.",
                "theme_light": "Thème clair", "theme_dark": "Thème sombre",
                "normal_cursor": "Curseur normal", "laser_cursor": "Pointeur laser",
                "laser_tip": "Le curseur devient un point rouge.\n(Les clics sont bloqués jusqu'au retour au curseur normal)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Enregistrer sous...", "remove_bg": "Supprimer l'arrière-plan",
                "font": "Police", "remove_clicked_color": "Supprimer la couleur sélectionnée",
                "screenshot_tip": "En créant avec LMB - copier dans le presse-papiens et ouvrir le fichier\nEn créant avec RMB - copier uniquement dans le presse-papiens",
                "rotate": "Pivoter / Taille", "ai": "Découpe Intelligente"
            },
            "DE": {
                "cursor": "Cursor", "pen": "Stift", "shape": "Formen", "text": "Text",
                "eraser": "Radierer", "color": "Farbe", "image": "Bild", "select": "Auswählen",
                "screenshot": "Screenshot", "delete": "Löschen",
                "front": "In den Vordergrund", "middle": "Mittlere Ebene", "back": "In den Hintergrund",
                "undo": "Rückgängig", "redo": "Wiederholen", "hide": "Ausblenden", "show": "Anzeigen",
                "clear": "Leeren",
                "exit": "Beenden",
                "width": "Breite: {}", "size": "Größe: {}",
                "line": "Linie", "rect": "Rechteck", "ellipse": "Ellipse", "arrow": "Pfeil",
                "next_lang": "IT", "current_lang": "DE", "donate_tip": "Auf DonationAlerts unterstützen",
                "cursor_tip": "LMT+RMT - von allen Modi zum Cursor wechseln\nRMT - Laserpointer auswählen",
                "pen_tip": "LMT - Zeichenmodus\nRMT - Liniengröße auswählen",
                "shape_tip": "LMT - Formen zeichnen\nRMT - Form auswählen",
                "text_tip": "LMT - Text einfügen\nRMT - Schriftart und Größe auswählen",
                "eraser_tip": "LMT - Linien löschen, RMT - Objekte löschen\nRMT - Radiergröße auswählen",
                "image_tip": "LMT - aus Datei einfügen\nRMT - Einfügemodus auswählen",
                "select_tip": "LMT - eingefügten Text und Bilder verwalten\nStrg + LMT - ausgewähltes Objekt kopieren\nMausrad - Objekt drehen\nStrg + Mausrad - Objekt vergrößern/verkleinern",
                "lang_tip": "LMT - nächste Sprache\nRMT - Sprache auswählen",
                "theme_tip": "LMT - Text ausblenden/anzeigen\nRMT - dunkles/helles Thema auswählen",
                "ai_tip": "Bei Verwendung von LMT - schneidet einen rechteckigen Bereich aus\nBei Verwendung von RMT - schneidet einen beliebigen Bereich aus",
                "color_tip": "LMT - Farbe der linken Taste auswählen\nRMT - Farbe der rechten Taste auswählen",
                "paste_img": "Aus Zwischenablage einfügen", "paste_chart_img": "Ohne Hintergrund einfügen",
                "insert_img_from_file": "Aus Datei einfügen", "paste_img_no_bg": "Ohne Hintergrund einfügen",
                "insert_folder_wheel": "Ordner einfügen (Shift + Mausrad)",
                "insert_folder_no_bg_wheel": "Ordner ohne Hintergrund einfügen (Shift + Mausrad)",
                "no_img_clip": "Kein Bild in der Zwischenablage.", "no_img_folder": "Keine Bilder im Ordner gefunden.",
                "theme_light": "Helles Design", "theme_dark": "Dunkles Design",
                "normal_cursor": "Normaler Cursor", "laser_cursor": "Laserpointer",
                "laser_tip": "Der Cursor wird zu einem roten Punkt.\n(Klicks sind blockiert, bis zum normalen Cursor zurückgekehrt wird)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Speichern unter...", "remove_bg": "Hintergrund entfernen",
                "font": "Schriftart", "remove_clicked_color": "Ausgewählte Farbe entfernen",
                "screenshot_tip": "Beim Erstellen mit LMT - in die Zwischenablage kopieren und Datei öffnen\nBeim Erstellen mit RMT - nur in die Zwischenablage kopieren",
                "rotate": "Drehen / Größe", "ai": "Smarter Schnitt"
            },
            "IT": {
                "cursor": "Cursore", "pen": "Penna", "shape": "Forme", "text": "Testo",
                "eraser": "Gomma", "color": "Colore", "image": "Immagine", "select": "Seleziona",
                "screenshot": "Screenshot", "delete": "Elimina",
                "front": "In primo piano", "middle": "Livello medio", "back": "In secondo piano",
                "undo": "Annulla", "redo": "Ripeti", "hide": "Nascondi", "show": "Mostra", "clear": "Cancella",
                "exit": "Esci",
                "width": "Spessore: {}", "size": "Dimensione: {}",
                "line": "Linea", "rect": "Rettangolo", "ellipse": "Ellisse", "arrow": "Freccia",
                "next_lang": "عر", "current_lang": "IT", "donate_tip": "Supporta su DonationAlerts",
                "cursor_tip": "LMB+RMB - passa al cursore da tutte le modalità\nRMB - seleziona puntatore laser",
                "pen_tip": "LMB - modalità disegno\nRMB - seleziona dimensione linea",
                "shape_tip": "LMB - disegna forme\nRMB - seleziona forma",
                "text_tip": "LMB - inserisci testo\nRMB - seleziona font e dimensione",
                "eraser_tip": "LMB - cancella linee, RMB - elimina oggetti\nRMB - seleziona dimensione gomma",
                "image_tip": "LMB - inserisci da file\nRMB - seleziona modalità di inserimento",
                "select_tip": "LMB - gestisci testo e immagini inserite\nCtrl + LMB - copia oggetto selezionato\nRotella del mouse - ruota oggetto\nCtrl + rotella del mouse - aumenta/diminuisci oggetto",
                "lang_tip": "LMB - lingua successiva\nRMB - seleziona lingua",
                "theme_tip": "LMB - nascondi/mostra testo\nRMB - seleziona tema scuro/chiaro",
                "ai_tip": "Usando LMB - ritaglia un'area rettangolare\nUsando RMB - ritaglia un'area arbitraria",
                "color_tip": "LMB - seleziona colore pulsante sinistro\nRMB - seleziona colore pulsante destro",
                "paste_img": "Incolla dagli appunti", "paste_chart_img": "Incolla senza sfondo",
                "insert_img_from_file": "Inserisci da file", "paste_img_no_bg": "Inserisci senza sfondo",
                "insert_folder_wheel": "Inserisci cartella (Shift + rotella del mouse)",
                "insert_folder_no_bg_wheel": "Inserisci cartella senza sfondo (Shift + rotella del mouse)",
                "no_img_clip": "Nessuna immagine negli appunti.",
                "no_img_folder": "Nessuna immagine trovata nella cartella.",
                "theme_light": "Tema chiaro", "theme_dark": "Tema scuro",
                "normal_cursor": "Cursore normale", "laser_cursor": "Puntatore laser",
                "laser_tip": "Il cursore diventa un punto rosso.\n(I clic sono bloccati fino al ritorno al cursore normale)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "Salva come...", "remove_bg": "Rimuovi sfondo",
                "font": "Carattere", "remove_clicked_color": "Rimuovi colore selezionato",
                "screenshot_tip": "Creando con LMB - copia negli appunti e apri file\nCreando con RMB - copia solo negli appunti",
                "rotate": "Ruota / Dimensione", "ai": "Taglio Intelligente"
            },
            "AR": {
                "cursor": "المؤشر", "pen": "القلم", "shape": "الأشكال", "text": "النص",
                "eraser": "الممحاة", "color": "اللون", "image": "الصورة", "select": "اختيار",
                "screenshot": "لقطة شاشة", "delete": "حذف",
                "front": "إلى الأمام", "middle": "طبقة وسطى", "back": "إلى الخلف",
                "undo": "تراجع", "redo": "إعادة", "hide": "إخفاء", "show": "إظهار", "clear": "مسح",
                "exit": "خروج",
                "width": "السمك: {}", "size": "الحجم: {}",
                "line": "خط", "rect": "مستطيل", "ellipse": "قطع ناقص", "arrow": "سهم",
                "next_lang": "हिं", "current_lang": "عر", "donate_tip": "الدعم على DonationAlerts",
                "cursor_tip": "زر أيسر+أيمن - التبديل إلى المؤشر من جميع الأوضاع\nزر أيمن - اختيار مؤشر الليزر",
                "pen_tip": "زر أيسر - وضع الرسم\nزر أيمن - اختيار حجم الخط",
                "shape_tip": "زر أيسر - رسم أشكال\nزر أيمن - اختيار الشكل",
                "text_tip": "زر أيسر - إدراج نص\nزر أيمن - اختيار الخط والحجم",
                "eraser_tip": "زر أيسر - مسح الخطوط، زر أيمن - حذف الكائنات\nزر أيمن - اختيار حجم الممحاة",
                "image_tip": "زر أيسر - إدراج من ملف\nزر أيمن - اختيار وضع الإدراج",
                "select_tip": "زر أيسر - إدارة النص والصور المدرجة\nCtrl + زر أيسر - نسخ الكائن المحدد\nعجلة الفأرة - تدوير الكائن\nCtrl + عجلة الفأرة - تكبير/تصغير الكائن",
                "lang_tip": "زر أيسر - اللغة التالية\nزر أيمن - اختيار اللغة",
                "theme_tip": "زر أيسر - إخفاء/إظهار النص\nزر أيمن - اختيار السمة الداكنة/الفاتحة",
                "ai_tip": "عند استخدام زر أيسر - يقطع مساحة مستطيلة\nعند استخدام زر أيمن - يقطع مساحة عشوائية",
                "color_tip": "زر أيسر - اختيار لون الزر الأيسر\nزر أيمن - اختيار لون الزر الأيمن",
                "paste_img": "لصق من الحافظة", "paste_chart_img": "لصق بدون خلفية",
                "insert_img_from_file": "إدراج من ملف", "paste_img_no_bg": "إدراج بدون خلفية",
                "insert_folder_wheel": "إدراج مجلد (Shift + عجلة الفأرة)",
                "insert_folder_no_bg_wheel": "إدراج مجلد بدون خلفية (Shift + عجلة الفأرة)",
                "no_img_clip": "لا توجد صورة في الحافظة.", "no_img_folder": "لم يتم العثور على صور في المجلد.",
                "theme_light": "مظهر فاتح", "theme_dark": "مظهر داكن",
                "normal_cursor": "مؤشر عادي", "laser_cursor": "مؤشر ليزر",
                "laser_tip": "يتحول المؤشر إلى نقطة حمراء.\n(النقرات محظورة حتى العودة للمؤشر العادي)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "حفظ باسم...", "remove_bg": "إزالة الخلفية",
                "font": "الخط", "remove_clicked_color": "إزالة اللون المحدد",
                "screenshot_tip": "عند الإنشاء بزر أيسر - نسخ إلى الحافظة وفتح الملف\nعند الإنشاء بزر أيمن - نسخ إلى الحافظة فقط",
                "rotate": "تدوير / حجم", "ai": "قص ذكي"
            },
            "HI": {
                "cursor": "कर्सर", "pen": "पेन", "shape": "आकार", "text": "पाठ",
                "eraser": "इरेज़र", "color": "रंग", "image": "छवि", "select": "चयन",
                "screenshot": "स्क्रीनशॉट", "delete": "हटाएं",
                "front": "सामने लाएं", "middle": "मध्य परत", "back": "पीछे भेजें",
                "undo": "पूर्ववत", "redo": "पुनः करें", "hide": "छिपाएं", "show": "दिखाएं", "clear": "साफ़ करें",
                "exit": "बाहर निकलें",
                "width": "मोटाई: {}", "size": "आकार: {}",
                "line": "रेखा", "rect": "आयत", "ellipse": "दीर्घवृत्त", "arrow": "तीर",
                "next_lang": "日", "current_lang": "हिं", "donate_tip": "DonationAlerts पर समर्थन करें",
                "cursor_tip": "बायां+दायां - सभी मोड से कर्सर पर स्विच करें\nदायां - लेज़र पॉइंटर चुनें",
                "pen_tip": "बायां - ड्राइंग मोड\nदायां - लाइन का आकार चुनें",
                "shape_tip": "बायां - आकार बनाएं\nदायां - आकार चुनें",
                "text_tip": "बायां - टेक्स्ट डालें\nदायां - फ़ॉन्ट और आकार चुनें",
                "eraser_tip": "बायां - लाइनें मिटाएं, दायां - वस्तुएं हटाएं\nदायां - इरेज़र का आकार चुनें",
                "image_tip": "बायां - फ़ाइल से डालें\nदायां - इंसर्शन मोड चुनें",
                "select_tip": "बायां - डाले गए टेक्स्ट और चित्र प्रबंधित करें\nCtrl + बायां - चयनित वस्तु कॉपी करें\nमाउस व्हील - वस्तु घुमाएं\nCtrl + माउस व्हील - वस्तु बढ़ाएं/घटाएं",
                "lang_tip": "बायां - अगली भाषा\nदायां - भाषा चुनें",
                "theme_tip": "बायां - टेक्स्ट छिपाएं/दिखाएं\nदायां - डार्क/लाइट थीम चुनें",
                "ai_tip": "बायां का उपयोग करते समय - एक आयताकार क्षेत्र काटता है\nदायां का उपयोग करते समय - एक मनमाना क्षेत्र काटता है",
                "color_tip": "बायां - बाएं बटन का रंग चुनें\nदायां - दाएं बटन का रंग चुनें",
                "paste_img": "क्लिपबोर्ड से चिपकाएं", "paste_chart_img": "बिना पृष्ठभूमि चिपकाएं",
                "insert_img_from_file": "फ़ाइल से डालें", "paste_img_no_bg": "बिना पृष्ठभूमि डालें",
                "insert_folder_wheel": "फ़ोल्डर डालें (Shift + माउस व्हील)",
                "insert_folder_no_bg_wheel": "बिना पृष्ठभूमि फ़ोल्डर डालें (Shift + माउस व्हील)",
                "no_img_clip": "क्लिपबोर्ड में कोई छवि नहीं है।", "no_img_folder": "फ़ोल्डर में कोई छवि नहीं मिली।",
                "theme_light": "हल्की थीम", "theme_dark": "गहरी थीम",
                "normal_cursor": "सामान्य कर्सर", "laser_cursor": "लेज़र पॉइंटर",
                "laser_tip": "कर्सर लाल बिंदु बन जाता है।\n(सामान्य कर्सर पर लौटने तक क्लिक अवरुद्ध हैं)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "इस रूप में सहेजें...", "remove_bg": "पृष्ठभूमि हटाएं",
                "font": "फ़ॉन्ट", "remove_clicked_color": "चयनित रंग हटाएं",
                "screenshot_tip": "बायां क्लिक से बनाते समय - क्लिपबोर्ड पर कॉपी करें और फ़ाइल खोलें\nदायां क्लिक से बनाते समय - केवल क्लिपबोर्ड पर कॉपी करें",
                "rotate": "घुमाएं / आकार", "ai": "स्मार्ट कट"
            },
            "JA": {
                "cursor": "カーソル", "pen": "ペン", "shape": "図形", "text": "テキスト",
                "eraser": "消しゴム", "color": "色", "image": "画像", "select": "選択",
                "screenshot": "スクリーンショット", "delete": "削除",
                "front": "前面へ", "middle": "中間層", "back": "背面へ",
                "undo": "元に戻す", "redo": "やり直し", "hide": "非表示", "show": "表示", "clear": "クリア",
                "exit": "終了",
                "width": "太さ: {}", "size": "サイズ: {}",
                "line": "直線", "rect": "四角形", "ellipse": "楕円", "arrow": "矢印",
                "next_lang": "한", "current_lang": "日", "donate_tip": "DonationAlertsで支援",
                "cursor_tip": "左+右クリック - すべてのモードからカーソルに切替\n右クリック - レーザーポインター選択",
                "pen_tip": "左クリック - 描画モード\n右クリック - 線のサイズ選択",
                "shape_tip": "左クリック - 図形描画\n右クリック - 図形選択",
                "text_tip": "左クリック - テキスト挿入\n右クリック - フォントとサイズ選択",
                "eraser_tip": "左クリック - 線を消去、右クリック - オブジェクト削除\n右クリック - 消しゴムのサイズ選択",
                "image_tip": "左クリック - ファイルから挿入\n右クリック - 挿入モード選択",
                "select_tip": "左クリック - 挿入したテキストと画像を管理\nCtrl + 左クリック - 選択したオブジェクトをコピー\nマウスホイール - オブジェクトを回転\nCtrl + マウスホイール - オブジェクトを拡大/縮小",
                "lang_tip": "左クリック - 次の言語\n右クリック - 言語選択",
                "theme_tip": "左クリック - テキストを隠す/表示する\n右クリック - ダーク/ライトテーマ選択",
                "ai_tip": "左クリック使用時 - 長方形の領域を切り取ります\n右クリック使用時 - 任意の領域を切り取ります",
                "color_tip": "左クリック - 左ボタンの色を選択\n右クリック - 右ボタンの色を選択",
                "paste_img": "クリップボードから貼付", "paste_chart_img": "背景なしで貴付",
                "insert_img_from_file": "ファイルから挿入", "paste_img_no_bg": "背景なしで挿入",
                "insert_folder_wheel": "フォルダを挿入 (Shift + マウスホイール)",
                "insert_folder_no_bg_wheel": "背景なしフォルダを挿入 (Shift + マウスホイール)",
                "no_img_clip": "クリップボードに画像がありません。", "no_img_folder": "フォルダに画像が見つかりません。",
                "theme_light": "ライトテーマ", "theme_dark": "ダークテーマ",
                "normal_cursor": "通常カーソル", "laser_cursor": "レーザーポインター",
                "laser_tip": "カーソルが赤い点になります。\n(通常カーソルに戻るまでクリックは無効)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "名前を付けて保存...", "remove_bg": "背景を削除",
                "font": "フォント", "remove_clicked_color": "選択した色を削除",
                "screenshot_tip": "左クリックで作成時 - クリップボードにコピーしてファイルを開く\n右クリックで作成時 - クリップボードにのみコピー",
                "rotate": "回転 / サイズ", "ai": "スマートカット"
            },
            "KO": {
                "cursor": "커서", "pen": "펜", "shape": "도형", "text": "텍스트",
                "eraser": "지우개", "color": "색상", "image": "이미지", "select": "선택",
                "screenshot": "스크린샷", "delete": "삭제",
                "front": "맨 앞으로", "middle": "중간 레이어", "back": "맨 뒤로",
                "undo": "실행 취소", "redo": "다시 실행", "hide": "숨기기", "show": "표시", "clear": "지우기",
                "exit": "종료",
                "width": "두께: {}", "size": "크기: {}",
                "line": "직선", "rect": "직사각형", "ellipse": "타원", "arrow": "화살표",
                "next_lang": "EN", "current_lang": "한", "donate_tip": "DonationAlerts에서 후원",
                "cursor_tip": "좌+우클릭 - 모든 모드에서 커서로 전환\n우클릭 - 레이저 포인터 선택",
                "pen_tip": "좌클릭 - 그리기 모드\n우클릭 - 선 크기 선택",
                "shape_tip": "좌클릭 - 도형 그리기\n우클릭 - 도형 선택",
                "text_tip": "좌클릭 - 텍스트 삽入\n우클릭 - 글꼴 및 크기 선택",
                "eraser_tip": "좌클릭 - 선 지우기, 우클릭 - 객체 삭제\n우클릭 - 지우개 크기 선택",
                "image_tip": "좌클릭 - 파일에서 삽入\n우클릭 - 삽入 모드 선택",
                "select_tip": "좌클릭 - 삽入된 텍스트 및 그림 관리\nCtrl + 좌클릭 - 선택한 객체 복사\n마우스 휠 - 객체 회전\nCtrl + 마우스 휠 - 객체 확대/축소",
                "lang_tip": "좌클릭 - 다음 언어\n우클릭 - 언어 선택",
                "theme_tip": "좌클릭 - 텍스트 숨기기/표시\n우클릭 - 다크/라이트 테마 선택",
                "ai_tip": "좌클릭 사용 시 - 사각형 영역을 잘라냅니다\n우클릭 사용 시 - 임의의 영역을 잘라냅니다",
                "color_tip": "좌클릭 - 왼쪽 버튼 색상 선택\n우클릭 - 오른쪽 버튼 색상 선택",
                "paste_img": "클립보드에서 붙여넣기", "paste_chart_img": "배경 없이 붙여넣기",
                "insert_img_from_file": "파일에서 삽入", "paste_img_no_bg": "배경 없이 삽入",
                "insert_folder_wheel": "폴더 삽入 (Shift + 마우스 휠)",
                "insert_folder_no_bg_wheel": "배경 없이 폴더 삽入 (Shift + 마우스 휠)",
                "no_img_clip": "클립보드에 이미지가 없습니다.", "no_img_folder": "폴더에 이미지가 없습니다.",
                "theme_light": "라이트 테마", "theme_dark": "다크 테마",
                "normal_cursor": "일반 커서", "laser_cursor": "레이저 포인터",
                "laser_tip": "커서가 빨간 점이 됩니다.\n(일반 커서로 돌아갈 때까지 클릭이 차단됩니다)",
                "lang_ru": "Русский", "lang_en": "English", "lang_zh": "中文",
                "save_as": "다른 이름으로 저장...", "remove_bg": "배경 제거",
                "font": "글꼴", "remove_clicked_color": "선택한 색상 제거",
                "screenshot_tip": "좌클릭으로 생성 시 - 클립보드에 복사하고 파일 열기\n우클릭으로 생성 시 - 클립보드에만 복사",
                "rotate": "회전 / 크기", "ai": "스마트 컷"
            }
        }
        tr = self.translations[self.lang]

        self.toolbar_widget = QFrame(self)
        self.toolbar_widget.setObjectName("ToolbarContainer")
        self.toolbar_widget.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self.toolbar_widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.setCentralWidget(self.toolbar_widget)

        self.all_buttons = []

        top_v_layout = QVBoxLayout()
        top_v_layout.setContentsMargins(0, 0, 0, 4)
        top_v_layout.setSpacing(2)
        top_v_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(4)
        row1_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        self.btn_collapse = QToolButton(self.toolbar_widget)
        # Используем плоскую иконку для кнопки свернуть
        self.btn_collapse.setIcon(get_flat_svg_icon(ICON_COLLAPSE, self.icon_color))
        self.btn_collapse.setIconSize(QSize(24, 24))
        self.btn_collapse.setToolTip("Свернуть")
        self.btn_collapse.setFixedSize(40, 32)
        self.btn_collapse.installEventFilter(self)
        self.drag_moved = False
        self.drag_start_pos = QPoint()
        self.drag_start_global = QPoint()
        row1_layout.addWidget(self.btn_collapse)

        self.app_title = QLabel("Paste Pen", self.toolbar_widget)
        self.app_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.app_title.setFixedHeight(32)
        self.app_title.setToolTip("v.2.5")
        row1_layout.addWidget(self.app_title)
        top_v_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(4)
        row2_layout.setAlignment(Qt.AlignLeft)

        self.btn_toggle_text = QToolButton(self.toolbar_widget)
        self.btn_toggle_text.setIcon(get_svg_icon(ICON_TOGGLE_TEXT, self.icon_color))
        self.btn_toggle_text.setIconSize(QSize(24, 24))
        self.btn_toggle_text.setToolTip(tr.get("theme_tip", "скрыть/показать название кнопок"))
        self.btn_toggle_text.clicked.connect(self.toggle_text_mode)
        self.btn_toggle_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_toggle_text.customContextMenuRequested.connect(self.show_theme_menu)
        self.btn_toggle_text.setFixedSize(40, 32)
        row2_layout.addWidget(self.btn_toggle_text)

        self.btn_lang = QToolButton(self.toolbar_widget)
        self.btn_lang.setObjectName("LangButton")
        self.btn_lang.setIcon(get_svg_icon(LANG_ICONS_SVG.get(self.lang, LANG_ICONS_SVG["EN"]), self.icon_color))
        self.btn_lang.setIconSize(QSize(24, 24))
        self.btn_lang.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btn_lang.setToolTip(tr.get("lang_tip", "ЛКМ - следующий язык,\nПКМ - выбор языка"))
        self.btn_lang.clicked.connect(self.toggle_language)
        self.btn_lang.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_lang.customContextMenuRequested.connect(self.show_language_menu)
        self.btn_lang.setFixedSize(40, 32)
        row2_layout.addWidget(self.btn_lang)

        self.btn_donate = QToolButton(self.toolbar_widget)
        self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))
        self.btn_donate.setIconSize(QSize(18, 18))
        self.btn_donate.setToolTip(tr["donate_tip"])
        self.btn_donate.clicked.connect(self.open_donate_link)
        self.btn_donate.setFixedSize(32, 32)
        row2_layout.addWidget(self.btn_donate)

        top_v_layout.addLayout(row2_layout)
        layout.addLayout(top_v_layout)

        self.btn_cursor = self.create_tool_button(tr["cursor"], ICON_CURSOR, self.set_normal_cursor)
        self.btn_cursor.setToolTip(tr["cursor_tip"])
        self.btn_cursor.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.act_normal_cursor = QAction(tr["normal_cursor"], self.btn_cursor)
        self.act_normal_cursor.triggered.connect(self.set_normal_cursor)
        self.act_laser_cursor = QAction(tr["laser_cursor"], self.btn_cursor)
        self.act_laser_cursor.triggered.connect(self.toggle_laser_mode)
        self.btn_cursor.addAction(self.act_normal_cursor)
        self.btn_cursor.addAction(self.act_laser_cursor)
        layout.addWidget(self.btn_cursor)

        self.btn_pen = self.create_tool_button(tr["pen"], ICON_PEN, lambda: self.overlay.set_tool("pen"))
        self.btn_pen.setToolTip(tr.get("pen_tip", tr["width"]))
        self.setup_menu(self.btn_pen, [2, 5, 10, 20, 30, 50], self.set_pen_width, tr["width"])
        layout.addWidget(self.btn_pen)

        self.btn_shape = self.create_tool_button(tr["shape"], ICON_SHAPES, lambda: self.overlay.set_tool("shape"))
        self.btn_shape.setToolTip(tr.get("shape_tip", tr["line"]))
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)
        layout.addWidget(self.btn_shape)

        self.btn_text = self.create_tool_button(tr["text"], ICON_TEXT, lambda: self.overlay.set_tool("text"))
        self.btn_text.setToolTip(tr.get("text_tip", tr["font"]))
        self.active_text_font_family = "Arial"
        self.act_font = QAction(f"{tr['font']}: {self.active_text_font_family}", self.btn_text)
        self.act_font.triggered.connect(self.choose_text_font)
        self.btn_text.addAction(self.act_font)

        self.setup_menu(self.btn_text, [16, 24, 36, 48, 72, 100, 150, 200, 300], self.set_text_font_size, tr["size"])
        layout.addWidget(self.btn_text)

        self.btn_eraser = self.create_tool_button(tr["eraser"], ICON_ERASER, lambda: self.overlay.set_tool("eraser"))
        self.btn_eraser.setToolTip(tr["eraser_tip"])
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60, 100, 200], self.set_eraser_width, tr["width"])
        layout.addWidget(self.btn_eraser)

        self.btn_color = self.create_tool_button(tr["color"], ICON_COLOR, self.choose_left_color)
        self.btn_color.setToolTip(tr["color_tip"])
        self.btn_color.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_color.customContextMenuRequested.connect(self.choose_right_color)
        layout.addWidget(self.btn_color)

        self.btn_image = self.create_tool_button(tr["image"], ICON_IMAGE, self.load_image)
        self.btn_image.setToolTip(tr.get("image_tip", ""))
        self.btn_image.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.act_paste_img = QAction(tr["paste_img"], self.btn_image)
        self.act_paste_img.triggered.connect(self.paste_image_from_clipboard)
        self.btn_image.addAction(self.act_paste_img)
        self.act_paste_chart_img = QAction(tr["paste_chart_img"], self.btn_image)
        self.act_paste_chart_img.triggered.connect(self.paste_chart_from_clipboard)
        self.btn_image.addAction(self.act_paste_chart_img)
        self.act_load_img = QAction(tr["insert_img_from_file"], self.btn_image)
        self.act_load_img.triggered.connect(self.load_image)
        self.btn_image.addAction(self.act_load_img)
        self.act_load_img_no_bg = QAction(tr["paste_img_no_bg"], self.btn_image)
        self.act_load_img_no_bg.triggered.connect(self.load_image_no_bg)
        self.btn_image.addAction(self.act_load_img_no_bg)
        self.act_load_folder = QAction(tr["insert_folder_wheel"], self.btn_image)
        self.act_load_folder.triggered.connect(self.load_folder_wheel)
        self.btn_image.addAction(self.act_load_folder)
        self.act_load_folder_no_bg = QAction(tr["insert_folder_no_bg_wheel"], self.btn_image)
        self.act_load_folder_no_bg.triggered.connect(self.load_folder_no_bg_wheel)
        self.btn_image.addAction(self.act_load_folder_no_bg)
        layout.addWidget(self.btn_image)

        self.btn_select = self.create_tool_button(tr["select"], ICON_SELECT, lambda: self.overlay.set_tool("select"))
        self.btn_select.setToolTip(tr.get("select_tip", ""))
        layout.addWidget(self.btn_select)

        self.btn_screenshot = self.create_tool_button(tr["screenshot"], ICON_SCREENSHOT, self.set_screenshot_tool_open)
        self.btn_screenshot.setToolTip(tr["screenshot_tip"])
        self.btn_screenshot.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_screenshot.customContextMenuRequested.connect(self.set_screenshot_tool_silent)
        layout.addWidget(self.btn_screenshot)

        self.btn_ai = self.create_tool_button(tr["ai"], ICON_AI, lambda: self.overlay.set_tool("ai"))
        self.btn_ai.setToolTip(tr.get("ai_tip", ""))
        layout.addWidget(self.btn_ai)

        self.btn_hide = self.create_tool_button(tr["hide"], ICON_HIDE, self.toggle_hide_mode)
        layout.addWidget(self.btn_hide)

        self.btn_undo = self.create_tool_button(tr["undo"], ICON_UNDO, self.overlay.undo)
        layout.addWidget(self.btn_undo)

        self.btn_clear = self.create_tool_button(tr["clear"], ICON_CLEAR, self.overlay.clear_all)
        layout.addWidget(self.btn_clear)

        self.btn_exit = self.create_tool_button(tr["exit"], ICON_EXIT, self.close_app)
        layout.addWidget(self.btn_exit)

        self.apply_theme()
        self.calculate_fixed_width()
        screen = QApplication.primaryScreen().geometry()
        self.resize(self.fixed_width, self.sizeHint().height())
        self.move(20, screen.height() // 2 - self.height() // 2)

        self.lock_size()
        self.set_normal_cursor()
        self.force_topmost_all()
        self.topmost_timer = QTimer(self)
        self.topmost_timer.timeout.connect(self.force_topmost_all)
        # 500 мс: заодно мгновенно реагируем на открытие модального диалога
        # (пока он открыт, оверлей убран с экрана — см. force_topmost_all)
        self.topmost_timer.start(500)

        # Подписка на вкл/выкл монитора и состояние дисплея: событие приходит
        # в окно оверлея как WM_POWERBROADCAST и запускает усиленное
        # восстановление topmost. Регистрируем через user32.
        self._power_notify_handles = _register_power_notifications(int(self.overlay.winId()))

    def focusInEvent(self, event):
        self.force_topmost_all()
        super().focusInEvent(event)

    def _active_dialog_widget(self):
        """Открытый модальный диалог приложения (иначе None).

        Только МОДАЛЬНЫЕ окна: popup-меню намеренно не трогаем — у меню оверлей
        является родителем (QMenu(self)), и его скрытие спрятало бы само меню.
        """
        try:
            return QApplication.activeModalWidget()
        except Exception:
            return None

    def _active_popup_widget(self):
        """Открытое popup-меню приложения (правый клик по кнопкам), иначе None."""
        try:
            return QApplication.activePopupWidget()
        except Exception:
            return None

    def force_topmost_all(self):
        """Держит оба окна поверх всех. Вызывается таймером раз в секунду.

        1) флаг WS_EX_TOPMOST потерян -> ставим немедленно;
        2) раз в 5 с детерминированный тоггл NOTOPMOST->TOPMOST — на случай,
           когда флаг формально стоит, но DWM опустил окно под другие
           topmost-окна (гашение экрана по таймеру простоя).
        Время берём у time.monotonic(): у v2.5 «раз в 15 тиков» зависело от
        того, сколько раз таймер вообще успел сработать, и растягивалось.
        isVisible() не проверяем — флаг должен стоять и у скрытого окна.
        """
        dlg = self._active_dialog_widget()
        if dlg is not None:
            # Открыт модальный диалог приложения (ошибка/файл/цвет): таймер
            # ЗАМИРАЕТ. Оверлей не скрываем — рисунки должны оставаться на экране.
            # Наши окна НЕ трогаем: панель и оверлей тоже topmost, и любой
            # SetWindowPos(TOPMOST) по ним поднял бы их выше диалога — тогда его
            # кнопки «не нажимаются» (проверено на живой системе). Диалог при
            # появлении поднимаем один раз.
            if not getattr(self, '_dialog_mode', False):
                self._dialog_mode = True
                try:
                    _win_set_topmost(int(dlg.winId()))
                except Exception:
                    pass
            # на время диалога оверлей пропускает мышь сквозь себя (рисунки видны,
            # а клик доходит до диалога и до остальных окон системы)
            try:
                _win_set_click_through(int(self.overlay.winId()), True)
            except Exception:
                pass
            return
        if getattr(self, '_dialog_mode', False):
            # диалог закрылся — снова работаем: снимаем «сквозную» прозрачность,
            # возвращаем порядок «панель выше оверлея» и продолжаем следить
            self._dialog_mode = False
            self.overlay.show()
            now = time.monotonic()
            self._topmost_toggled_at = now
            self._zcheck_at = now
            for w in (self.overlay, self):
                try:
                    _win_set_topmost(int(w.winId()), toggle=True)
                except Exception:
                    pass
        try:
            _win_set_click_through(int(self.overlay.winId()), False)
        except Exception:
            pass
        popup = self._active_popup_widget()
        if popup is not None:
            # Открыто меню (в т.ч. правым кликом по кнопкам панели). Поднимаем
            # МЕНЮ, а панель и оверлей не трогаем — иначе они оказываются выше
            # меню и пункты не читаются/не нажимаются.
            try:
                _win_set_topmost(int(popup.winId()))
            except Exception:
                pass
            return
        now = time.monotonic()
        toggle = (now - getattr(self, '_topmost_toggled_at', 0.0)) >= 5.0
        if toggle:
            self._topmost_toggled_at = now
        # Порядок важен: оверлей (рисунки и вставленные картинки) поднимаем
        # первым, панель — вторым, поэтому панель всегда оказывается ВЫШЕ
        # рисунков и картинок.
        for w in (self.overlay, self):
            try:
                hwnd = int(w.winId())
            except Exception:
                continue
            if toggle or not _win_is_topmost(hwnd):
                _win_set_topmost(hwnd, toggle=toggle)

        # Страховка: сторонние события/DWM могут переставить topmost-окна местами
        # (флаги одинаковые, а порядок разный) — раз в секунду сверяем z-order.
        if now - getattr(self, '_zcheck_at', 0.0) >= 1.0:
            self._zcheck_at = now
            try:
                if _z_index(int(self.winId())) > _z_index(int(self.overlay.winId())):
                    _win_set_topmost(int(self.winId()))
            except Exception:
                pass

    def showEvent(self, event):
        super().showEvent(event)
        self.force_topmost_all()

    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == QEvent.ActivationChange and self.isActiveWindow():
            # Вернули фокус — сразу восстанавливаем TOPMOST, не дожидаясь таймера
            self.force_topmost_all()

    def restore_topmost_aggressive(self):
        """Полное восстановление «поверх всех» после сна и вкл/выкл мониторов.

        Одиночный повторный TOPMOST не помогает, когда окно формально осталось
        в topmost-диапазоне, но оказалось НИЖЕ других topmost-окон: после
        включения мониторов DWM и другие программы перестраивают z-order.
        Тоггл NOTOPMOST->TOPMOST поднимает окно на самый верх диапазона.
        Три прохода (0/400/1200 мс) — на случай, если Windows ещё достраивает
        окна после пробуждения.
        """
        now = time.monotonic()
        if getattr(self, '_restore_pending_until', 0) > now:
            return
        self._restore_pending_until = now + 3.4
        for delay in (0, 400, 1200, 3000):
            QTimer.singleShot(delay, self._toggle_topmost_once)

    def _toggle_topmost_once(self):
        for w in (self.overlay, self):     # панель поднимается последней
            try:
                hwnd = int(w.winId())
            except Exception:
                continue
            _win_set_topmost(hwnd, toggle=True)
        self._topmost_toggled_at = time.monotonic()
        # Если конфигурация мониторов менялась, пока экраны были выключены,
        # оверлей мог остаться со старой геометрией — пересинхронизируем.
        try:
            screen = QApplication.primaryScreen()
            if screen and self.overlay.geometry() != screen.virtualGeometry():
                self.overlay.setGeometry(screen.virtualGeometry())
        except Exception:
            pass

    def _qimage_to_numpy(self, qimg):
        w, h = qimg.width(), qimg.height()
        ptr = qimg.bits()
        try:
            ptr.setsize(qimg.byteCount())
            arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()
        except Exception:
            arr = np.zeros((h, w, 4), dtype=np.uint8)
            for y in range(h):
                for x in range(w):
                    rgb = qimg.pixel(x, y)
                    arr[y, x, 0] = (rgb >> 16) & 0xFF
                    arr[y, x, 1] = (rgb >> 8) & 0xFF
                    arr[y, x, 2] = rgb & 0xFF
                    arr[y, x, 3] = (rgb >> 24) & 0xFF
        return arr

    def _apply_alpha_mask(self, arr, target_colors, threshold):
        arr_float = arr[:, :, :3].astype(float)
        min_distances = np.full(arr.shape[:2], np.inf)
        for bg in target_colors:
            dist = np.sqrt(np.sum((arr_float - bg) ** 2, axis=-1))
            min_distances = np.minimum(min_distances, dist)

        alpha = np.clip((min_distances - threshold / 2) / (threshold / 2) * 255, 0, 255).astype(np.uint8)
        current_alpha = arr[:, :, 3]
        arr[:, :, 3] = np.minimum(current_alpha, alpha)
        return arr

    def remove_chart_background(self, pixmap, threshold=20):
        if pixmap.isNull(): return pixmap
        qimg = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()
        if w < 40 or h < 40: return pixmap

        arr = self._qimage_to_numpy(qimg)

        ps = 5
        off = 5
        c_x = w // 2
        c_y = h // 2
        half_ps = ps // 2

        patches = [
            arr[off:off + ps, off:off + ps],
            arr[off:off + ps, c_x - half_ps:c_x - half_ps + ps],
            arr[off:off + ps, w - off - ps:w - off],
            arr[c_y - half_ps:c_y - half_ps + ps, off:off + ps],
            arr[c_y - half_ps:c_y - half_ps + ps, w - off - ps:w - off],
            arr[h - off - ps:h - off, off:off + ps],
            arr[h - off - ps:h - off, c_x - half_ps:c_x - half_ps + ps],
            arr[h - off - ps:h - off, w - off - ps:w - off]
        ]
        bg_colors = [p[:, :, :3].mean(axis=(0, 1)) for p in patches]

        arr = self._apply_alpha_mask(arr, bg_colors, threshold)

        new_qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
        new_pixmap = QPixmap.fromImage(new_qimg.copy())
        return new_pixmap

    def remove_color_at_pos(self, pixmap, pos, threshold=20):
        if pixmap.isNull(): return pixmap
        qimg = pixmap.toImage()
        if pos.x() < 0 or pos.x() >= qimg.width() or pos.y() < 0 or pos.y() >= qimg.height():
            return pixmap

        rgb = qimg.pixel(pos.x(), pos.y())
        r = (rgb >> 16) & 0xFF
        g = (rgb >> 8) & 0xFF
        b = rgb & 0xFF
        target_color = (r, g, b)

        return self.remove_specific_color(pixmap, target_color, threshold)

    def remove_specific_color(self, pixmap, target_color, threshold=20):
        if pixmap.isNull(): return pixmap
        qimg = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()

        arr = self._qimage_to_numpy(qimg)

        arr = self._apply_alpha_mask(arr, [target_color], threshold)

        new_qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
        new_pixmap = QPixmap.fromImage(new_qimg.copy())
        return new_pixmap

    def apply_theme(self):
        if self.theme == "dark":
            self.icon_color = "white"
            self.setStyleSheet("""
                QFrame#ToolbarContainer { background: #1e1e1e; border: 1px solid #0a0a0a; border-radius: 12px; }
                                QToolButton {
                    color: #e0e0e0; background: transparent; border: none; border-radius: 6px; padding: 2px 8px 2px 8px; font-size: 18px; font-family: Segoe UI; text-align: left;
                }
                QToolButton#LangButton { padding: 6px 8px 6px 8px; text-align: center; }
                QToolButton:hover { background: #333333; color: white; }
                QToolButton:pressed { background: #404040; }
                QToolButton::menu-indicator { image: none; }
                QMenu { background: #1e1e1e; border: 1px solid #0a0a0a; border-radius: 8px; color: #e0e0e0; padding: 8px; font-size: 18px; }
                QMenu::item { background: transparent; padding: 10px 30px; border-radius: 4px; }
                QMenu::item:selected { background: #333333; }
                QMenu::separator { height: 1px; background: #333333; margin: 5px 10px; }
            """)
            self.app_title.setStyleSheet(
                "QLabel { color: #DAA520; font-size: 20px; font-family: 'Segoe Script', 'Segoe Print', cursive; font-weight: bold; padding: 0px; }")
        else:
            self.icon_color = "black"
            self.setStyleSheet("""
                QFrame#ToolbarContainer { background: #f0f0f0; border: 1px solid #cccccc; border-radius: 12px; }
                                QToolButton {
                    color: #222222; background: transparent; border: none; border-radius: 6px; padding: 2px 8px 2px 8px; font-size: 18px; font-family: Segoe UI; text-align: left;
                }
                QToolButton#LangButton { padding: 6px 8px 6px 8px; text-align: center; }
                QToolButton:hover { background: #dcdcdc; color: black; }
                QToolButton:pressed { background: #d0d0d0; }
                QToolButton::menu-indicator { image: none; }
                QMenu { background: #f0f0f0; border: 1px solid #cccccc; border-radius: 8px; color: #222222; padding: 8px; font-size: 18px; }
                QMenu::item { background: transparent; padding: 10px 30px; border-radius: 4px; }
                QMenu::item:selected { background: #dcdcdc; }
                QMenu::separator { height: 1px; background: #cccccc; margin: 5px 10px; }
            """)
            self.app_title.setStyleSheet(
                "QLabel { color: #B8860B; font-size: 20px; font-family: 'Segoe Script', 'Segoe Print', cursive; font-weight: bold; padding: 0px; }")

        for btn in self.all_buttons:
            svg = btn.property("svg")
            if svg: btn.setIcon(get_svg_icon(svg, self.icon_color))

        # Кнопка свернуть использует плоскую иконку
        self.btn_collapse.setIcon(get_flat_svg_icon(ICON_COLLAPSE, self.icon_color))

        self.btn_toggle_text.setIcon(get_svg_icon(ICON_TOGGLE_TEXT, self.icon_color))
        self.btn_lang.setIcon(get_svg_icon(LANG_ICONS_SVG.get(self.lang, LANG_ICONS_SVG["EN"]), self.icon_color))
        if self.overlay.tool == "laser": self.btn_cursor.setIcon(get_svg_icon(ICON_LASER, self.icon_color))
        self.set_shape_type(self.overlay.shape_type)
        self.update_hide_button_state()
        if self.lang == "RU":
            self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))
        elif self.lang == "EN":
            self.btn_donate.setIcon(get_svg_icon(ICON_DOLLAR, self.icon_color))
        elif self.lang == "ZH":
            self.btn_donate.setIcon(get_svg_icon(ICON_YUAN, self.icon_color))
        elif self.lang in ("ES", "PT", "FR", "DE", "IT"):
            self.btn_donate.setIcon(get_svg_icon(ICON_EURO, self.icon_color))
        elif self.lang == "AR":
            self.btn_donate.setIcon(get_svg_icon(ICON_RIAL, self.icon_color))
        elif self.lang == "HI":
            self.btn_donate.setIcon(get_svg_icon(ICON_RUPEE, self.icon_color))
        elif self.lang == "JA":
            self.btn_donate.setIcon(get_svg_icon(ICON_YEN, self.icon_color))
        elif self.lang == "KO":
            self.btn_donate.setIcon(get_svg_icon(ICON_WON, self.icon_color))

    def show_theme_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())
        tr = self.translations[self.lang]
        act_light = menu.addAction(tr["theme_light"])
        act_dark = menu.addAction(tr["theme_dark"])
        action = menu.exec_(self.btn_toggle_text.mapToGlobal(pos))
        if action == act_light:
            self.theme = "light";
            self.settings.setValue("theme", self.theme);
            self.apply_theme()
        elif action == act_dark:
            self.theme = "dark";
            self.settings.setValue("theme", self.theme);
            self.apply_theme()

    def show_language_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(self.styleSheet())
        actions = []
        actions.append(("EN", menu.addAction("English")))
        actions.append(("RU", menu.addAction("Русский")))
        actions.append(("ZH", menu.addAction("中文")))
        actions.append(("ES", menu.addAction("Español")))
        actions.append(("PT", menu.addAction("Português")))
        actions.append(("FR", menu.addAction("Français")))
        actions.append(("DE", menu.addAction("Deutsch")))
        actions.append(("IT", menu.addAction("Italiano")))
        actions.append(("AR", menu.addAction("العربية")))
        actions.append(("HI", menu.addAction("हिन्दी")))
        actions.append(("JA", menu.addAction("日本語")))
        actions.append(("KO", menu.addAction("한국어")))
        action = menu.exec_(self.btn_lang.mapToGlobal(pos))
        for lang_code, act in actions:
            if action == act:
                self.set_language(lang_code)
                break

    def calculate_fixed_width(self):
        if self.icons_only:
            self.fixed_width = 56
            return
        self.toolbar_widget.layout().invalidate()
        self.toolbar_widget.layout().activate()
        self.fixed_width = self.toolbar_widget.sizeHint().width()

    def create_tool_button(self, text, icon_svg, callback):
        btn = QToolButton(self.toolbar_widget)
        btn.setText("  " + text)
        btn.setProperty("svg", icon_svg)
        btn.setIcon(get_svg_icon(icon_svg, self.icon_color))
        btn.setIconSize(QSize(20, 20))
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setMinimumWidth(130)
        btn.setFixedHeight(32)
        btn.clicked.connect(callback)
        self.all_buttons.append(btn)
        return btn

    def setup_menu(self, btn, items, callback, text_format="{}"):
        btn.setContextMenuPolicy(Qt.ActionsContextMenu)
        for item in items:
            if isinstance(item, tuple):
                name, val = item
            else:
                name = text_format.format(item);
                val = item
            act = QAction(name, btn)
            act.triggered.connect(lambda checked, v=val: callback(v))
            btn.addAction(act)

    def populate_font_menu(self):
        self.font_menu.clear()
        db = QFontDatabase()
        for family in db.families():
            act = QAction(family, self.font_menu)
            act.setCheckable(True)
            act.setChecked(family == self.active_text_font_family)
            act.triggered.connect(lambda checked, f=family: self.set_text_font_family(f))
            self.font_menu.addAction(act)

    def choose_text_font(self, item_to_change=None):
        tr = self.translations[self.lang]
        dialog = QDialog(self)
        dialog.setWindowTitle(tr["font"])
        dialog.setModal(True)
        dialog.setMinimumWidth(300)
        dialog.setMinimumHeight(600)

        layout = QVBoxLayout(dialog)
        list_widget = QListWidget()
        db = QFontDatabase()
        all_families = db.families()

        recent_str = self.settings.value("recent_fonts", "", type=str)
        recent = recent_str.split("|||") if recent_str else []
        recent = [f for f in recent if f in all_families]
        remaining = [f for f in all_families if f not in recent]

        display_list = recent + ["———"] + remaining if recent else remaining
        list_widget.addItems(display_list)

        if recent:
            sep_item = list_widget.item(len(recent))
            sep_item.setFlags(Qt.NoItemFlags)

        app_font = QApplication.font()
        base_size = app_font.pointSize()
        if base_size < 1: base_size = 8
        large_size = int(base_size * 1.8)

        for i in range(len(display_list)):
            list_item = list_widget.item(i)
            font = QFont(display_list[i])
            font.setPointSize(large_size)
            list_item.setFont(font)

        current_font = self.active_text_font_family if not item_to_change else item_to_change.get('font_family',
                                                                                                  'Arial')
        if current_font in display_list:
            idx = display_list.index(current_font)
            list_widget.setCurrentRow(idx)
            list_widget.scrollToItem(list_widget.currentItem())

        layout.addWidget(list_widget)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(button_box)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)

        if dialog.exec_() == QDialog.Accepted:
            selected = list_widget.currentItem()
            if selected and selected.text() != "———":
                sel_font = selected.text()

                if sel_font in recent: recent.remove(sel_font)
                recent.insert(0, sel_font)
                self.settings.setValue("recent_fonts", "|||".join(recent[:5]))

                if item_to_change:
                    self.overlay.change_text_font(item_to_change, sel_font)
                else:
                    self.active_text_font_family = sel_font
                    self.act_font.setText(f"{tr['font']}: {self.active_text_font_family}")
                    self.overlay.set_tool("text")

        self.force_topmost_all()

    def choose_text_color_for_item(self, item):
        color = QColorDialog.getColor(item.get('color', Qt.white), self, "Цвет текста")
        if color.isValid():
            item['color'] = color
            self.overlay.rebuild_canvas()
            self.overlay.update()
        self.force_topmost_all()

    def set_text_font_family(self, family):
        self.active_text_font_family = family
        tr = self.translations[self.lang]
        self.act_font.setText(f"{tr['font']}: {family}")
        for act in self.font_menu.actions():
            act.setChecked(act.text() == family)

    def open_donate_link(self):
        if self.lang == "RU":
            webbrowser.open("https://boosty.to/yaroslavkhmelev/donate")
        else:
            webbrowser.open("https://www.donationalerts.com/r/yaroslavkhmelev")

    def toggle_language(self):
        order = ["EN", "RU", "ZH", "ES", "PT", "FR", "DE", "IT", "AR", "HI", "JA", "KO"]
        idx = order.index(self.lang) if self.lang in order else 0
        self.lang = order[(idx + 1) % len(order)]
        self.settings.setValue("language", self.lang)
        self.update_language()

    def set_language(self, lang):
        if self.lang != lang:
            self.lang = lang
            self.settings.setValue("language", self.lang)
            self.update_language()

    def update_language(self):
        tr = self.translations[self.lang]
        self.btn_cursor.setText("  " + tr["cursor"])
        self.btn_cursor.setToolTip(tr["cursor_tip"])
        self.act_normal_cursor.setText(tr["normal_cursor"])
        self.act_laser_cursor.setText(tr["laser_cursor"])
        self.btn_pen.setText("  " + tr["pen"])
        self.btn_pen.setToolTip(tr.get("pen_tip", tr["width"]))
        self.btn_shape.setText("  " + tr["shape"])
        self.btn_shape.setToolTip(tr.get("shape_tip", tr["line"]))
        self.btn_text.setText("  " + tr["text"])
        self.btn_text.setToolTip(tr.get("text_tip", tr["font"]))
        self.act_font.setText(f"{tr['font']}: {self.active_text_font_family}")
        self.btn_eraser.setText("  " + tr["eraser"])
        self.btn_eraser.setToolTip(tr["eraser_tip"])
        self.btn_color.setText("  " + tr["color"])
        self.btn_color.setToolTip(tr["color_tip"])
        self.act_paste_img.setText(tr["paste_img"])
        self.act_paste_chart_img.setText(tr["paste_chart_img"])
        self.act_load_img.setText(tr["insert_img_from_file"])
        self.act_load_img_no_bg.setText(tr["paste_img_no_bg"])
        self.act_load_folder.setText(tr["insert_folder_wheel"])
        self.act_load_folder_no_bg.setText(tr["insert_folder_no_bg_wheel"])
        self.btn_image.setText("  " + tr["image"])
        self.btn_image.setToolTip(tr.get("image_tip", ""))
        self.btn_select.setText("  " + tr["select"])
        self.btn_select.setToolTip(tr.get("select_tip", ""))
        self.btn_screenshot.setText("  " + tr["screenshot"])
        self.btn_screenshot.setToolTip(tr["screenshot_tip"])
        self.btn_ai.setText("  " + tr["ai"])
        self.btn_ai.setToolTip(tr.get("ai_tip", ""))
        self.btn_undo.setText("  " + tr["undo"])

        self.update_hide_button_state()
        self.btn_donate.setToolTip(tr["donate_tip"])
        self.btn_lang.setIcon(get_svg_icon(LANG_ICONS_SVG.get(self.lang, LANG_ICONS_SVG["EN"]), self.icon_color))
        self.btn_lang.setToolTip(tr.get("lang_tip", "ЛКМ - следующий язык, ПКМ - выбор языка"))
        self.btn_toggle_text.setToolTip(tr.get("theme_tip", "скрыть/показать текст"))
        self.btn_clear.setText("  " + tr["clear"])
        self.btn_exit.setText("  " + tr["exit"])

        if self.lang == "RU":
            self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))
        elif self.lang == "EN":
            self.btn_donate.setIcon(get_svg_icon(ICON_DOLLAR, self.icon_color))
        elif self.lang == "ZH":
            self.btn_donate.setIcon(get_svg_icon(ICON_YUAN, self.icon_color))
        elif self.lang in ("ES", "PT", "FR", "DE", "IT"):
            self.btn_donate.setIcon(get_svg_icon(ICON_EURO, self.icon_color))
        elif self.lang == "AR":
            self.btn_donate.setIcon(get_svg_icon(ICON_RIAL, self.icon_color))
        elif self.lang == "HI":
            self.btn_donate.setIcon(get_svg_icon(ICON_RUPEE, self.icon_color))
        elif self.lang == "JA":
            self.btn_donate.setIcon(get_svg_icon(ICON_YEN, self.icon_color))
        elif self.lang == "KO":
            self.btn_donate.setIcon(get_svg_icon(ICON_WON, self.icon_color))

        for btn in [self.btn_pen, self.btn_shape, self.btn_text, self.btn_eraser]:
            for action in btn.actions(): btn.removeAction(action)
        self.setup_menu(self.btn_pen, [2, 5, 10, 20, 30, 50], self.set_pen_width, tr["width"])
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)

        self.act_font = QAction(f"{tr['font']}: {self.active_text_font_family}", self.btn_text)
        self.act_font.triggered.connect(self.choose_text_font)
        self.btn_text.addAction(self.act_font)

        self.setup_menu(self.btn_text, [16, 24, 36, 48, 72, 100, 150, 200, 300], self.set_text_font_size, tr["size"])
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60, 100, 200], self.set_eraser_width, tr["width"])

        self.calculate_fixed_width()
        if not self.is_collapsed: self.resize(self.fixed_width, self.sizeHint().height())

        if self.overlay.tool == "ai":
            self.overlay.update_ai_cursor()

    def toggle_text_mode(self):
        self.icons_only = not self.icons_only
        style = Qt.ToolButtonIconOnly if self.icons_only else Qt.ToolButtonTextBesideIcon
        start_rect = self.geometry()

        for btn in self.all_buttons:
            btn.setToolButtonStyle(style)
            if self.icons_only:
                btn.setMinimumWidth(0);
                btn.setFixedSize(40, 32)
            else:
                btn.setMinimumSize(0, 0);
                btn.setMaximumSize(16777215, 16777215);
                btn.setMinimumWidth(130)
                btn.setFixedHeight(32)

        if self.icons_only:
            self.btn_donate.hide();
            self.btn_lang.hide();
            self.app_title.hide()
        else:
            self.btn_donate.show();
            self.btn_lang.show();
            self.app_title.show()

        self.toolbar_widget.layout().invalidate()
        self.toolbar_widget.layout().activate()

        self.calculate_fixed_width()
        target_rect = QRect(start_rect.topLeft(), QSize(self.fixed_width, self.height()))
        self.animate_geometry(start_rect, target_rect)

    def toggle_hide_mode(self):
        self.overlay.toggle_hide()
        if self.overlay.is_hidden: self.set_normal_cursor()
        self.update_hide_button_state()

    def update_hide_button_state(self):
        tr = self.translations[self.lang]
        if self.overlay.is_hidden:
            self.btn_hide.setText("  " + tr["show"])
            self.btn_hide.setIcon(get_svg_icon(ICON_SHOW, self.icon_color))
        else:
            self.btn_hide.setText("  " + tr["hide"])
            self.btn_hide.setIcon(get_svg_icon(ICON_HIDE, self.icon_color))
        if self.icons_only:
            start_rect = self.geometry()
            self.calculate_fixed_width()
            target_rect = QRect(start_rect.topLeft(), QSize(self.fixed_width, self.sizeHint().height()))
            self.animate_geometry(start_rect, target_rect)

    def toggle_collapse(self):
        start_rect = self.geometry()
        if not self.is_collapsed:
            self.is_collapsed = True
            self.setMinimumSize(0, 0)
            for btn in self.all_buttons: btn.hide()
            self.btn_toggle_text.hide()
            self.btn_donate.hide()
            self.btn_lang.hide()
            self.app_title.hide()
            target_rect = QRect(start_rect.left(), start_rect.top(), 56, 44)
        else:
            self.is_collapsed = False
            self.btn_toggle_text.show()
            if not self.icons_only:
                self.btn_donate.show()
                self.btn_lang.show()
                self.app_title.show()
            for btn in self.all_buttons: btn.show()
            self.toolbar_widget.layout().invalidate()
            self.toolbar_widget.layout().activate()
            target_rect = QRect(start_rect.left(), start_rect.top(), self.fixed_width, self.sizeHint().height())
        self.animate_geometry(start_rect, target_rect)

    def animate_geometry(self, start_rect, target_rect):
        if self.anim: self.anim.stop()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(target_rect)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(self.lock_size)
        self.anim.start()

    def lock_size(self):
        self.setFixedSize(self.width(), self.height())

    def set_pen_width(self, width):
        self.overlay.pen_width = width
        self.overlay.set_tool("pen")

    def set_eraser_width(self, width):
        self.overlay.eraser_width = width
        self.overlay.update_eraser_cursor()
        self.overlay.set_tool("eraser")

    def set_shape_type(self, shape_id):
        self.overlay.shape_type = shape_id
        self.overlay.set_tool("shape")
        if shape_id == "line":
            self.btn_shape.setIcon(get_svg_icon(ICON_SHAPE_LINE, self.icon_color))
        elif shape_id == "rect":
            self.btn_shape.setIcon(get_svg_icon(ICON_SHAPE_RECT, self.icon_color))
        elif shape_id == "ellipse":
            self.btn_shape.setIcon(get_svg_icon(ICON_SHAPE_ELLIPSE, self.icon_color))
        elif shape_id == "arrow":
            self.btn_shape.setIcon(get_svg_icon(ICON_SHAPE_ARROW, self.icon_color))

    def set_text_font_size(self, size):
        self.overlay.text_font_size = size
        self.overlay.set_tool("text")

    def set_normal_cursor(self):
        self.overlay.laser_mode = False
        self.overlay.set_tool("cursor")
        self.btn_cursor.setIcon(get_svg_icon(ICON_CURSOR, self.icon_color))
        self.btn_cursor.setToolTip(self.translations[self.lang]["cursor_tip"])

    def toggle_laser_mode(self):
        if self.overlay.is_hidden:
            self.overlay.is_hidden = False
            self.update_hide_button_state()
        self.overlay.laser_mode = not self.overlay.laser_mode
        self.overlay.update_cursor()
        self.overlay.update()
        if self.overlay.laser_mode:
            self.btn_cursor.setIcon(get_svg_icon(ICON_LASER, self.icon_color))
            self.btn_cursor.setToolTip(self.translations[self.lang]["laser_tip"])
        else:
            self.btn_cursor.setIcon(get_svg_icon(ICON_CURSOR, self.icon_color))
            self.btn_cursor.setToolTip(self.translations[self.lang]["cursor_tip"])

    def set_screenshot_tool_open(self):
        self.overlay.screenshot_open_file = True
        self.overlay.set_tool("screenshot")

    def set_screenshot_tool_silent(self):
        self.overlay.screenshot_open_file = False
        self.overlay.set_tool("screenshot")

    def eventFilter(self, obj, event):
        if obj == self.btn_collapse:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                    self.drag_start_pos = event.pos()
                    # Порог «тащат / кликнули» считаем в ГЛОБАЛЬНЫХ координатах:
                    # панель едет за курсором, поэтому в локальных координатах
                    # кнопки смещение почти нулевое, порог 5 px не набирался, и
                    # перетаскивание засчитывалось как клик (панель сворачивалась).
                    self.drag_start_global = event.globalPos()
                    self.drag_moved = False
                    self.btn_collapse.grabMouse()
                    return True

            elif event.type() == QEvent.MouseMove:
                if self.drag_pos is not None:
                    if (event.globalPos() - self.drag_start_global).manhattanLength() > 5:
                        self.drag_moved = True
                    self.move(event.globalPos() - self.drag_pos)
                    return True

            elif event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self.btn_collapse.releaseMouse()
                    if not self.drag_moved:
                        self.toggle_collapse()
                    self.drag_pos = None
                    return True

        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            child = self.childAt(event.pos())
            if child is None or not child.inherits("QToolButton"):
                self.drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self.drag_pos is not None:
            self.move(event.globalPos() - self.drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = None

    def choose_left_color(self):
        color = QColorDialog.getColor(self.overlay.left_color, self, "Цвет левой кнопки мыши")
        if color.isValid():
            self.overlay.left_color = color
            self.overlay.set_tool("pen")
            self.raise_();
            self.activateWindow()
        self.force_topmost_all()

    def choose_right_color(self, pos):
        color = QColorDialog.getColor(self.overlay.right_color, self, "Цвет правой кнопки мыши")
        if color.isValid():
            self.overlay.right_color = color
            self.overlay.set_tool("pen")
            self.raise_();
            self.activateWindow()
        self.force_topmost_all()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "",
                                                   "Images (*.png *.jpg *.jpeg *.bmp *.webp);;PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;WEBP (*.webp)")
        if file_path:
            pixmap = QPixmap(file_path)
            self.overlay.insert_pixmap(pixmap)
            self.raise_();
            self.activateWindow()
        self.force_topmost_all()

    def load_image_no_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "",
                                                   "Images (*.png *.jpg *.jpeg *.bmp *.webp);;PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp);;WEBP (*.webp)")
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                processed_pixmap = self.remove_chart_background(pixmap, threshold=20)
                self.overlay.insert_pixmap(processed_pixmap)
                self.raise_();
                self.activateWindow()
        self.force_topmost_all()

    def load_folder_wheel(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder_path:
            success = self.overlay.load_folder(folder_path, remove_bg=False)
            if not success:
                QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_folder"])
            else:
                self.raise_();
                self.activateWindow()
        self.force_topmost_all()

    def load_folder_no_bg_wheel(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder_path:
            success = self.overlay.load_folder(folder_path, remove_bg=True)
            if not success:
                QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_folder"])
            else:
                self.raise_();
                self.activateWindow()
        self.force_topmost_all()

    def paste_image_from_clipboard(self):
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.overlay.insert_pixmap(pixmap)
            self.raise_();
            self.activateWindow()
        else:
            QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_clip"])

    def paste_chart_from_clipboard(self):
        clipboard = QApplication.clipboard()
        image = clipboard.image()
        if not image.isNull():
            pixmap = QPixmap.fromImage(image)
            processed_pixmap = self.remove_chart_background(pixmap, threshold=20)
            self.overlay.insert_pixmap(processed_pixmap)
            self.raise_();
            self.activateWindow()
        else:
            QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_clip"])

    def save_image_as(self, pixmap):
        if pixmap.isNull(): return
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "",
                                                   "PNG (*.png);;JPEG (*.jpg);;BMP (*.bmp);;WEBP (*.webp)")
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            fmt = "PNG" if ext in [".png", ""] else "JPG" if ext in [".jpg",
                                                                     ".jpeg"] else "BMP" if ext == ".bmp" else "WEBP"
            pixmap.save(file_path, fmt)
        self.force_topmost_all()

    def close_app(self):
        self.is_closing = True
        self.overlay.close()
        self.tray_icon.hide()
        self.close()

        _unregister_power_notifications(getattr(self, '_power_notify_handles', None))
        self._power_notify_handles = []

        global app_mutex
        if app_mutex:
            # HANDLE 64-битный: без прототипа CloseHandle получал усечённое значение
            _k32.CloseHandle(app_mutex)
            app_mutex = None

        QApplication.quit()

    def closeEvent(self, event):
        if not self.is_closing:
            event.ignore()
        else:
            event.accept()


app_mutex = None

if __name__ == "__main__":
    mutex_name = "Paste_Pen_App_Single_Instance_Mutex"
    app_mutex = _k32.CreateMutexW(None, False, mutex_name)
    if _k32.GetLastError() == 183:
        app = QApplication(sys.argv)
        QMessageBox.information(None, "Paste Pen", "Программа уже запущена.")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    window.raise_()
    sys.exit(app.exec_())