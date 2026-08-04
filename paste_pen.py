import sys
import math
import ctypes
import webbrowser
import os
import time
import tempfile
import numpy as np
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QToolBar, QAction, QLabel,
                             QFileDialog, QColorDialog, QMainWindow, QToolButton, QMenu, QLineEdit, QFrame, QVBoxLayout,
                             QHBoxLayout, QSizePolicy, QMessageBox, QSystemTrayIcon)
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QCursor, QPolygonF, QFont, QFontMetrics, QIcon, QTransform, \
    QPainterPath, QPainterPathStroker, QImage, QDesktopServices
from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize, QPointF, QPropertyAnimation, QEasingCurve, QSettings, QUrl


# --- Функция для создания векторных иконок (с возможностью перекраски) ---
def get_svg_icon(svg_path, color="white"):
    colored_svg = svg_path.replace('white', color)
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    pixmap.loadFromData(bytearray(colored_svg, encoding='utf-8'), "SVG")
    return QIcon(pixmap)


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
ICON_LASER = '<svg viewBox="0 0 24 24" fill="#FF0000" stroke="white" stroke-width="1.5"><circle cx="12" cy="12" r="7" /></svg>'


class OverlayWidget(QWidget):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)

        screen = QApplication.primaryScreen()
        if screen:
            self.setGeometry(screen.virtualGeometry())
        self.show()

        self.tool = "cursor"
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

        # Переменные для режима папки
        self.active_folder_item = None
        self.folder_files = []
        self.folder_index = -1
        self.folder_remove_bg = False

        self.moving_image = None
        self.resizing_image = None
        self.resizing_handle = None
        self.move_offset = QPoint(0, 0)
        self.resize_start_pos = QPoint(0, 0)
        self.resize_start_points = []
        self.resize_button = Qt.NoButton

        self.shape_start_pos = None
        self.shape_end_pos = None
        self.screenshot_start_pos = None
        self.screenshot_end_pos = None
        self.is_capturing = False
        self.text_input = None
        self.text_color = None
        self.screenshot_open_file = True

        self.undo_stack = []
        self.update_cursor()

    def closeEvent(self, event):
        if not self.main_window.is_closing:
            event.ignore()
        else:
            event.accept()

    def save_state(self):
        if len(self.undo_stack) >= 15:
            self.undo_stack.pop(0)
        drawings_copy = []
        for d in self.drawings:
            nd = d.copy()
            if 'path' in nd: nd['path'] = QPainterPath(nd['path'])
            if 'pixmap' in nd: nd['pixmap'] = nd['pixmap'].copy()
            if 'points' in nd: nd['points'] = [QPointF(p) for p in nd['points']]
            drawings_copy.append(nd)
        self.undo_stack.append({'canvas': self.canvas.copy(), 'drawings': drawings_copy})

    def undo(self):
        self.commit_text()
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.canvas = state['canvas']
            self.drawings = state['drawings']
            self.deselect_all_images()
            self.active_folder_item = None  # Сбрасываем режим папки при отмене
            self.update()

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
        return super().nativeEvent(eventType, message)

    def set_tool(self, tool):
        if self.tool == "text" and tool != "text":
            self.commit_text()

        if self.is_hidden and tool in ("pen", "eraser", "shape", "text", "select"):
            self.is_hidden = False
            self.main_window.update_hide_button_state()

        # Отключаем режим папки, если выбран инструмент, отличный от Выбора и Курсора
        if self.active_folder_item and tool not in ("select", "cursor"):
            self.active_folder_item = None
            self.folder_files = []
            self.folder_index = -1

        self.tool = tool
        self.update_cursor()
        self.update()

    def update_cursor(self):
        if self.tool == "eraser":
            self.update_eraser_cursor()
        elif self.laser_mode:
            self.update_laser_cursor()
        elif self.tool == "cursor":
            self.deselect_all_images()
            self.unsetCursor()
        elif self.tool == "text":
            self.setCursor(Qt.IBeamCursor)
        else:
            self.setCursor(Qt.CrossCursor)

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
        self.update()

    def get_handle_rect(self, pt):
        return QRectF(pt.x() - 5, pt.y() - 5, 10, 10)

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
            arrow_size = max(10, pen_width * 4)
            p1 = QPointF(end.x() - arrow_size * math.cos(angle - math.pi / 6),
                         end.y() - arrow_size * math.sin(angle - math.pi / 6))
            p2 = QPointF(end.x() - arrow_size * math.cos(angle + math.pi / 6),
                         end.y() - arrow_size * math.sin(angle + math.pi / 6))
            path.addPolygon(QPolygonF([QPointF(end), p1, p2]))
        return path

    def draw_item_on_painter(self, painter, item):
        if item['type'] == 'pen':
            pen = QPen(item['color'], item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPath(item['path'])
        elif item['type'] == 'shape':
            pen = QPen(item['color'], item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            if item['shape_type'] == 'arrow':
                painter.setBrush(item['color'])
            else:
                painter.setBrush(Qt.NoBrush)
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawPath(item['path'])
        elif item['type'] == 'eraser':
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen = QPen(Qt.white, item['width'], Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawPath(item['path'])
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
        elif item['type'] == 'text':
            font = QFont("Arial")
            font.setPixelSize(item['font_size'])
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(item['color'])
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            painter.drawText(item['pos'], item['text'])

    def rebuild_canvas(self):
        self.canvas.fill(Qt.transparent)
        p = QPainter(self.canvas)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        for item in self.drawings:
            if item['type'] != 'image':
                self.draw_item_on_painter(p, item)
        p.end()

    def hit_test_item(self, item, pos):
        if item['type'] in ('pen', 'shape'):
            stroker = QPainterPathStroker()
            stroker.setWidth(item['width'] + 6)
            hit_path = stroker.createStroke(item['path'])
            if hit_path.contains(pos): return True
            if item['path'].contains(pos): return True
        elif item['type'] == 'text':
            font = QFont("Arial")
            font.setPixelSize(item['font_size'])
            font.setBold(True)
            fm = QFontMetrics(font)
            rect = fm.boundingRect(item['text'])
            text_top = item['pos'].y() + 2
            text_rect = QRect(item['pos'].x(), text_top, rect.width(), rect.height())
            if text_rect.contains(pos): return True
        return False

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if (self.tool != "cursor" or self.laser_mode) and not self.is_capturing:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

        if not self.is_hidden:
            for item in self.drawings:
                if item['type'] == 'image' and item.get('layer', 'front') == 'back':
                    self.draw_image_item(painter, item)

            painter.drawPixmap(0, 0, self.canvas)

            if self.current_item:
                self.draw_item_on_painter(painter, self.current_item)

            for item in self.drawings:
                if item['type'] == 'image' and item.get('layer', 'front') == 'front':
                    self.draw_image_item(painter, item)

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
                                painter.setPen(Qt.NoPen)
                                painter.drawRect(handle)

        if self.tool == "screenshot" and self.screenshot_start_pos is not None and not self.is_capturing:
            rect = QRect(self.screenshot_start_pos, self.screenshot_end_pos).normalized()
            mask_color = QColor(0, 0, 0, 150)
            painter.fillRect(QRect(0, 0, self.width(), rect.y()), mask_color)
            painter.fillRect(QRect(0, rect.bottom() + 1, self.width(), self.height() - rect.bottom() - 1), mask_color)
            painter.fillRect(QRect(0, rect.y(), rect.x(), rect.height()), mask_color)
            painter.fillRect(QRect(rect.right() + 1, rect.y(), self.width() - rect.right() - 1, rect.height()),
                             mask_color)
            painter.setPen(QPen(QColor(0, 120, 215), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() not in (Qt.LeftButton, Qt.RightButton): return
        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.commit_text()
            self.main_window.set_normal_cursor()
            self.last_pos = None
            self.current_item = None
            self.moving_image = None
            self.resizing_image = None
            self.screenshot_start_pos = None
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
            path = QPainterPath()
            path.moveTo(event.pos())
            item_type = self.tool
            width = self.eraser_width if self.tool == "eraser" else self.pen_width
            self.current_item = {'type': item_type, 'color': self.current_color, 'width': width, 'path': path}
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
                                 'width': self.pen_width, 'path': path}
            self.update()

        elif self.tool == "screenshot":
            self.screenshot_start_pos = event.pos()
            self.screenshot_end_pos = event.pos()
            self.update()

        elif self.tool == "text":
            if event.button() in (Qt.LeftButton, Qt.RightButton):
                self.commit_text()
                self.save_state()
                self.deselect_all_images()
                self.text_color = self.current_color
                self.text_input = QLineEdit(self)
                self.text_input.setStyleSheet(
                    f"QLineEdit {{ background: rgba(255, 255, 255, 180); border: 1px dashed gray; color: {self.text_color.name()}; font-size: {self.text_font_size}px; font-family: Arial; padding: 2px; }}")
                self.text_input.move(event.pos())
                self.text_input.show()
                self.text_input.setFocus()
                self.text_input.editingFinished.connect(self.commit_text)

        elif self.tool == "select":
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
                            self.deselect_all_images()
                            item['selected'] = True
                            self.moving_image = item
                            # Если кликнули на другую картинку, выходим из режима папки
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
                            back_action = menu.addAction(tr["back"])
                            menu.addSeparator()
                            remove_bg_action = menu.addAction(tr["remove_bg"])
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
                            elif action == back_action:
                                self.save_state()
                                item['layer'] = 'back'
                                self.update()
                            elif action == remove_bg_action:
                                self.save_state()
                                processed_pixmap = self.main_window.remove_chart_background(item['pixmap'],
                                                                                            threshold=40)
                                if not processed_pixmap.isNull():
                                    item['pixmap'] = processed_pixmap
                                    self.update()
                            elif action == save_as_action:
                                self.main_window.save_image_as(item['pixmap'])
                            return
            if event.button() == Qt.LeftButton:
                # Отключаем режим папки, если кликнули в пустое место
                if self.active_folder_item:
                    self.active_folder_item = None
                    self.folder_files = []
                    self.folder_index = -1
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
            item = {'type': 'text', 'color': self.text_color, 'font_size': self.text_font_size, 'pos': pos,
                    'text': text}
            self.drawings.append(item)
            p = QPainter(self.canvas)
            p.setRenderHint(QPainter.Antialiasing)
            self.draw_item_on_painter(p, item)
            p.end()
            self.update()
        self.text_input.deleteLater()
        self.text_input = None
        self.text_color = None

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.last_pos = None
            self.current_item = None
            self.moving_image = None
            self.resizing_image = None
            self.screenshot_start_pos = None
            return

        if not (event.buttons() & (Qt.LeftButton | Qt.RightButton)): return
        if self.is_hidden and self.tool != "screenshot": return

        if self.current_item:
            if self.current_item['type'] in ('pen', 'eraser'):
                self.current_item['path'].lineTo(event.pos())
                p = QPainter(self.canvas)
                p.setRenderHint(QPainter.Antialiasing)
                self.draw_item_on_painter(p, self.current_item)
                p.end()
                padding = self.current_item['width'] + 10
                rect = QRect(self.last_pos if self.last_pos else event.pos(), event.pos()).normalized()
                self.update(rect.adjusted(-padding, -padding, padding, padding))
                self.last_pos = event.pos()
            elif self.current_item['type'] == 'shape':
                self.shape_end_pos = event.pos()
                self.current_item['path'] = self.get_shape_path(self.current_item['shape_type'], self.shape_start_pos,
                                                                self.shape_end_pos, self.pen_width)
                self.update()
        elif self.screenshot_start_pos is not None:
            self.screenshot_end_pos = event.pos()
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
                    vx = tr.x() - tl.x();
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
        if event.button() not in (Qt.LeftButton, Qt.RightButton): return

        if self.tool == "screenshot" and self.screenshot_start_pos is not None:
            rect = QRect(self.screenshot_start_pos, self.screenshot_end_pos).normalized()
            self.screenshot_start_pos = None
            self.screenshot_end_pos = None
            self.is_capturing = True
            self.update()
            QApplication.processEvents()
            time.sleep(0.15)
            if rect.width() > 5 and rect.height() > 5:
                global_top_left = self.mapToGlobal(rect.topLeft())
                global_bottom_right = self.mapToGlobal(rect.bottomRight())
                global_rect = QRect(global_top_left, global_bottom_right).normalized()
                virtual_geo = QApplication.primaryScreen().virtualGeometry()
                desktop_pixmap = QApplication.primaryScreen().grabWindow(0, virtual_geo.x(), virtual_geo.y(),
                                                                         virtual_geo.width(), virtual_geo.height())
                pixmap_x = global_rect.x() - virtual_geo.x()
                pixmap_y = global_rect.y() - virtual_geo.y()
                pixmap_rect = QRect(pixmap_x, pixmap_y, global_rect.width(), global_rect.height()).intersected(
                    desktop_pixmap.rect())
                if not pixmap_rect.isEmpty():
                    screenshot_pixmap = desktop_pixmap.copy(pixmap_rect)
                    if not screenshot_pixmap.isNull():
                        QApplication.clipboard().setPixmap(screenshot_pixmap)
                        if self.screenshot_open_file:
                            try:
                                temp_dir = tempfile.gettempdir()
                                filename = f"paste_pen_{int(time.time())}.png"
                                file_path = os.path.join(temp_dir, filename)
                                screenshot_pixmap.save(file_path, "PNG")
                                QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
                            except Exception:
                                pass
            self.is_capturing = False
            self.set_tool("cursor")
            self.update()
            return

        if self.current_item:
            if self.current_item['type'] == 'shape' and self.shape_start_pos == self.shape_end_pos:
                self.current_item = None
                self.update()
                return
            self.drawings.append(self.current_item)
            if self.current_item['type'] == 'shape':
                p = QPainter(self.canvas)
                p.setRenderHint(QPainter.Antialiasing)
                self.draw_item_on_painter(p, self.current_item)
                p.end()
            self.current_item = None
            self.last_pos = None
            self.update()

        self.moving_image = None
        self.resizing_image = None

    def wheelEvent(self, event):
        # Обработка прокрутки колесика для режима папки
        if self.active_folder_item and self.tool == "select":
            delta = event.angleDelta().y()
            if delta > 0:
                # Прокрутка вверх
                self.folder_index = (self.folder_index - 1) % len(self.folder_files)
            else:
                # Прокрутка вниз
                self.folder_index = (self.folder_index + 1) % len(self.folder_files)

            file_path = self.folder_files[self.folder_index]
            new_pixmap = QPixmap(file_path)
            if not new_pixmap.isNull():
                # Если выбран режим удаления фона, обрабатываем pixmap
                if self.folder_remove_bg:
                    new_pixmap = self.main_window.remove_chart_background(new_pixmap, threshold=40)

                if new_pixmap.width() > 1500 or new_pixmap.height() > 1500:
                    new_pixmap = new_pixmap.scaled(1500, 1500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                # Сохраняем текущий левый верхний угол
                old_tl = self.active_folder_item['points'][0]

                w = new_pixmap.width()
                h = new_pixmap.height()

                # Формируем новые точки (прямоугольник) исходя из новых размеров
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
        self.drawings.append({'type': 'image', 'pixmap': pixmap, 'points': points, 'selected': True, 'layer': 'front'})
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

        pixmap = QPixmap(files[0])

        if pixmap.isNull(): return False

        if self.folder_remove_bg:
            pixmap = self.main_window.remove_chart_background(pixmap, threshold=40)

        if pixmap.width() > 1500 or pixmap.height() > 1500:
            pixmap = pixmap.scaled(1500, 1500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        x = self.width() // 2 - pixmap.width() // 2
        y = self.height() // 2 - pixmap.height() // 2
        w = pixmap.width()
        h = pixmap.height()
        points = [QPointF(x, y), QPointF(x + w, y), QPointF(x + w, y + h), QPointF(x, y + h)]

        self.save_state()
        self.deselect_all_images()
        self.drawings.append({'type': 'image', 'pixmap': pixmap, 'points': points, 'selected': True, 'layer': 'front'})
        self.active_folder_item = self.drawings[-1]  # Запоминаем элемент как активный для прокрутки

        self.tool = "select"  # Включаем режим выбора
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

        self.translations = {
            "RU": {
                "cursor": "Курсор", "pen": "Ручка", "shape": "Фигуры", "text": "Текст",
                "eraser": "Ластик", "color": "Цвет", "image": "Картинка", "select": "Выбор",
                "screenshot": "Скриншот", "delete": "Удалить",
                "front": "На передний план", "back": "На задний план",
                "undo": "Назад", "hide": "Скрыть", "show": "Показать", "clear": "Очистить",
                "exit": "Выход",
                "width": "Толщина: {}", "size": "Размер: {}",
                "line": "Линия", "rect": "Прямоугольник", "ellipse": "Эллипс", "arrow": "Стрелка",
                "next_lang": "中", "donate_tip": "Поддержать на Boosty",
                "cursor_tip": "Переключение на курсор: ЛКМ + ПКМ",
                "color_tip": "ЛКМ: цвет левой кнопки\nПКМ: цвет правой кнопки",
                "paste_img": "Вставить из буфера", "paste_chart_img": "Вставить из буфера без фона",
                "insert_img_from_file": "Вставить из файла", "paste_img_no_bg": "Вставить из файла без фона",
                "insert_folder_wheel": "Вставить папку (колесико мыши)",
                "insert_folder_no_bg_wheel": "Вставить папку без фона (колесико мыши)",
                "no_img_clip": "В буфере обмена нет изображения.",
                "no_img_folder": "В выбранной папке нет изображений.",
                "theme_light": "Светлая тема", "theme_dark": "Темная тема",
                "eraser_tip": "ЛКМ: стирание ластиком\nПКМ: удаление линии целиком",
                "normal_cursor": "Обычный курсор", "laser_cursor": "Лазерная указка",
                "laser_tip": "Курсор станет красной точкой.\n(Клики заблокированы до возврата на обычный курсор)",
                "lang_ru": "Русский", "lang_en": "Английский", "lang_zh": "Китайский",
                "save_as": "Сохранить как...", "remove_bg": "Убрать фон",
                "screenshot_tip": "ЛКМ: копирование в буфер и открытие файла\nПКМ мыши: только копирование в буфер"
            },
            "EN": {
                "cursor": "Cursor", "pen": "Pen", "shape": "Shapes", "text": "Text",
                "eraser": "Eraser", "color": "Color", "image": "Image", "select": "Select",
                "screenshot": "Screenshot", "delete": "Delete",
                "front": "Bring to Front", "back": "Send to Back",
                "undo": "Undo", "hide": "Hide", "show": "Show", "clear": "Clear",
                "exit": "Exit",
                "width": "Width: {}", "size": "Size: {}",
                "line": "Line", "rect": "Rectangle", "ellipse": "Ellipse", "arrow": "Arrow",
                "next_lang": "РУ", "donate_tip": "Support on DonationAlerts",
                "cursor_tip": "Switch to cursor: LMB + RMB",
                "color_tip": "LMB: left button color\nRMB: right button color",
                "paste_img": "Paste from clipboard", "paste_chart_img": "Paste from clipboard without background",
                "insert_img_from_file": "Insert from file", "paste_img_no_bg": "Insert from file without background",
                "insert_folder_wheel": "Insert folder (mouse wheel)",
                "insert_folder_no_bg_wheel": "Insert folder without background (mouse wheel)",
                "no_img_clip": "No image in clipboard.", "no_img_folder": "No images found in the selected folder.",
                "theme_light": "Light Theme", "theme_dark": "Dark Theme",
                "eraser_tip": "LMB: erase pixels\nRMB: delete entire line",
                "normal_cursor": "Normal Cursor", "laser_cursor": "Laser Pointer",
                "laser_tip": "Cursor becomes a red dot.\n(Clicks are blocked until returning to normal cursor)",
                "lang_ru": "Russian", "lang_en": "English", "lang_zh": "Chinese",
                "save_as": "Save As...", "remove_bg": "Remove background",
                "screenshot_tip": "LMB: copy to clipboard and open file\nRMB: copy to clipboard only"
            },
            "ZH": {
                "cursor": "光标", "pen": "画笔", "shape": "形状", "text": "文本",
                "eraser": "橡皮擦", "color": "颜色", "image": "图片", "select": "选择",
                "screenshot": "截图", "delete": "删除",
                "front": "置于顶层", "back": "置于底层",
                "undo": "撤销", "hide": "隐藏", "show": "显示", "clear": "清除",
                "exit": "退出",
                "width": "粗细: {}", "size": "大小: {}",
                "line": "直线", "rect": "矩形", "ellipse": "椭圆", "arrow": "箭头",
                "next_lang": "EN", "donate_tip": "在 DonationAlerts 上支持",
                "cursor_tip": "切换到光标: 鼠标左键 + 右键",
                "color_tip": "左键: 左键颜色\n右键: 右键颜色",
                "paste_img": "从剪贴板粘贴", "paste_chart_img": "从剪贴板粘贴无背景",
                "insert_img_from_file": "从文件插入", "paste_img_no_bg": "从文件插入无背景图片",
                "insert_folder_wheel": "插入文件夹 (鼠标滚轮)",
                "insert_folder_no_bg_wheel": "插入无背景文件夹 (鼠标滚轮)", "no_img_clip": "剪贴板中没有图像。",
                "no_img_folder": "所选文件夹中没有图像。",
                "theme_light": "浅色主题", "theme_dark": "深色主题",
                "eraser_tip": "左键: 擦除像素\n右键: 删除整条线",
                "normal_cursor": "普通光标", "laser_cursor": "激光笔",
                "laser_tip": "光标变为红点。\n（在返回普通光标前点击被阻止）",
                "lang_ru": "俄语", "lang_en": "英语", "lang_zh": "中文",
                "save_as": "另存为...", "remove_bg": "移除背景",
                "screenshot_tip": "鼠标左键: 复制到剪贴板并打开文件\n鼠标右键: 仅复制到剪贴板"
            }
        }
        tr = self.translations[self.lang]

        self.toolbar_widget = QFrame(self)
        self.toolbar_widget.setObjectName("ToolbarContainer")
        self.toolbar_widget.setContentsMargins(0, 0, 0, 0)
        layout = QVBoxLayout(self.toolbar_widget)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(2)
        self.setCentralWidget(self.toolbar_widget)

        self.all_buttons = []

        top_v_layout = QVBoxLayout()
        top_v_layout.setContentsMargins(0, 0, 0, 4)
        top_v_layout.setSpacing(2)

        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(4)
        row1_layout.setAlignment(Qt.AlignLeft)

        self.btn_collapse = QToolButton(self.toolbar_widget)
        self.btn_collapse.setIcon(get_svg_icon(ICON_COLLAPSE, self.icon_color))
        self.btn_collapse.setIconSize(QSize(28, 28))
        self.btn_collapse.setToolTip("Свернуть")
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        self.btn_collapse.setFixedSize(44, 32)
        row1_layout.addWidget(self.btn_collapse)

        self.app_title = QLabel("Paste Pen", self.toolbar_widget)
        self.app_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        row1_layout.addWidget(self.app_title)
        top_v_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(4)
        row2_layout.setAlignment(Qt.AlignLeft)

        self.btn_toggle_text = QToolButton(self.toolbar_widget)
        self.btn_toggle_text.setIcon(get_svg_icon(ICON_TOGGLE_TEXT, self.icon_color))
        self.btn_toggle_text.setIconSize(QSize(28, 28))
        self.btn_toggle_text.setToolTip("Скрыть/Показать текст")
        self.btn_toggle_text.clicked.connect(self.toggle_text_mode)
        self.btn_toggle_text.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_toggle_text.customContextMenuRequested.connect(self.show_theme_menu)
        self.btn_toggle_text.setFixedSize(44, 32)
        row2_layout.addWidget(self.btn_toggle_text)

        self.btn_lang = QToolButton(self.toolbar_widget)
        self.btn_lang.setText(tr["next_lang"])
        self.btn_lang.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_lang.clicked.connect(self.toggle_language)
        self.btn_lang.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_lang.customContextMenuRequested.connect(self.show_language_menu)
        self.btn_lang.setFixedSize(44, 32)
        row2_layout.addWidget(self.btn_lang)

        self.btn_donate = QToolButton(self.toolbar_widget)
        self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))
        self.btn_donate.setIconSize(QSize(20, 20))
        self.btn_donate.setToolTip(tr["donate_tip"])
        self.btn_donate.clicked.connect(self.open_donate_link)
        self.btn_donate.setFixedSize(36, 32)
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
        self.setup_menu(self.btn_pen, [2, 5, 10, 20, 30, 50], self.set_pen_width, tr["width"])
        layout.addWidget(self.btn_pen)

        self.btn_shape = self.create_tool_button(tr["shape"], ICON_SHAPES, lambda: self.overlay.set_tool("shape"))
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)
        layout.addWidget(self.btn_shape)

        self.btn_text = self.create_tool_button(tr["text"], ICON_TEXT, lambda: self.overlay.set_tool("text"))
        self.setup_menu(self.btn_text, [16, 24, 36, 48, 72, 100, 150, 200, 300], self.set_text_font_size, tr["size"])
        layout.addWidget(self.btn_text)

        self.btn_eraser = self.create_tool_button(tr["eraser"], ICON_ERASER, lambda: self.overlay.set_tool("eraser"))
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60, 100, 200], self.set_eraser_width, tr["width"])
        self.btn_eraser.setToolTip(tr["eraser_tip"])
        layout.addWidget(self.btn_eraser)

        self.btn_color = self.create_tool_button(tr["color"], ICON_COLOR, self.choose_left_color)
        self.btn_color.setToolTip(tr["color_tip"])
        self.btn_color.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_color.customContextMenuRequested.connect(self.choose_right_color)
        layout.addWidget(self.btn_color)

        self.btn_image = self.create_tool_button(tr["image"], ICON_IMAGE, self.load_image)
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
        layout.addWidget(self.btn_select)

        self.btn_screenshot = self.create_tool_button(tr["screenshot"], ICON_SCREENSHOT, self.set_screenshot_tool_open)
        self.btn_screenshot.setToolTip(tr["screenshot_tip"])
        self.btn_screenshot.setContextMenuPolicy(Qt.CustomContextMenu)
        self.btn_screenshot.customContextMenuRequested.connect(self.set_screenshot_tool_silent)
        layout.addWidget(self.btn_screenshot)

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

    def remove_chart_background(self, pixmap, threshold=40):
        if pixmap.isNull(): return pixmap
        qimg = pixmap.toImage().convertToFormat(QImage.Format_RGBA8888)
        w, h = qimg.width(), qimg.height()

        ptr = qimg.bits()
        ptr.setsize(qimg.byteCount())
        arr = np.frombuffer(ptr, dtype=np.uint8).reshape((h, w, 4)).copy()

        bg_color = arr[0, 0, :3].astype(float)
        distances = np.sqrt(np.sum((arr[:, :, :3].astype(float) - bg_color) ** 2, axis=-1))
        alpha = np.clip((distances - threshold / 2) / (threshold / 2) * 255, 0, 255).astype(np.uint8)
        arr[:, :, 3] = alpha

        new_qimg = QImage(arr.data, w, h, 4 * w, QImage.Format_RGBA8888)
        new_pixmap = QPixmap.fromImage(new_qimg.copy())
        return new_pixmap

    def apply_theme(self):
        if self.theme == "dark":
            self.icon_color = "white"
            self.setStyleSheet("""
                QFrame#ToolbarContainer { background: #1e1e1e; border: 1px solid #0a0a0a; border-radius: 12px; }
                QToolButton { color: #e0e0e0; background: transparent; border: none; border-radius: 6px; padding: 4px 8px 4px 8px; font-size: 18px; font-family: Segoe UI; text-align: left; }
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
                QToolButton { color: #222222; background: transparent; border: none; border-radius: 6px; padding: 4px 8px 4px 8px; font-size: 18px; font-family: Segoe UI; text-align: left; }
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
        self.btn_collapse.setIcon(get_svg_icon(ICON_COLLAPSE, self.icon_color))
        self.btn_toggle_text.setIcon(get_svg_icon(ICON_TOGGLE_TEXT, self.icon_color))
        if self.overlay.tool == "laser": self.btn_cursor.setIcon(get_svg_icon(ICON_LASER, self.icon_color))
        self.set_shape_type(self.overlay.shape_type)
        self.update_hide_button_state()
        if self.lang == "EN":
            self.btn_donate.setIcon(get_svg_icon(ICON_DOLLAR, self.icon_color))
        elif self.lang == "ZH":
            self.btn_donate.setIcon(get_svg_icon(ICON_YUAN, self.icon_color))
        else:
            self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))

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
        tr = self.translations[self.lang]

        act_en = menu.addAction(tr["lang_en"])
        act_ru = menu.addAction(tr["lang_ru"])
        act_zh = menu.addAction(tr["lang_zh"])

        action = menu.exec_(self.btn_lang.mapToGlobal(pos))
        if action == act_en:
            self.set_language("EN")
        elif action == act_ru:
            self.set_language("RU")
        elif action == act_zh:
            self.set_language("ZH")

    def calculate_fixed_width(self):
        if self.icons_only:
            self.fixed_width = 44 + 12
            return
        max_w = 0
        for btn in self.all_buttons: max_w = max(max_w, btn.sizeHint().width())
        top_w = 44 * 3 + 4 * 2 + 12
        row1_w = 44 + 4 + self.app_title.sizeHint().width() + 12
        top_w = max(top_w, row1_w)
        self.fixed_width = max(max_w, top_w) + 12

    def create_tool_button(self, text, icon_svg, callback):
        btn = QToolButton(self.toolbar_widget)
        btn.setText("  " + text)
        btn.setProperty("svg", icon_svg)
        btn.setIcon(get_svg_icon(icon_svg, self.icon_color))
        btn.setIconSize(QSize(24, 24))
        btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        btn.setMinimumWidth(130)
        btn.clicked.connect(callback)
        self.all_buttons.append(btn)
        return btn

    def setup_menu(self, btn, items, callback, text_format="{}"):
        btn.setContextMenuPolicy(Qt.ActionsContextMenu)
        for item in items:
            if isinstance(item, tuple):
                name, val = item
            else:
                name = text_format.format(item); val = item
            act = QAction(name, btn)
            act.triggered.connect(lambda checked, v=val: callback(v))
            btn.addAction(act)

    def open_donate_link(self):
        if self.lang in ("EN", "ZH"):
            webbrowser.open("https://www.donationalerts.com/r/yaroslavkhmelev")
        else:
            webbrowser.open("https://boosty.to/yaroslavkhmelev/donate")

    def toggle_language(self):
        if self.lang == "EN":
            self.lang = "RU"
        elif self.lang == "RU":
            self.lang = "ZH"
        else:
            self.lang = "EN"

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
        self.btn_shape.setText("  " + tr["shape"])
        self.btn_text.setText("  " + tr["text"])
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
        self.btn_select.setText("  " + tr["select"])
        self.btn_screenshot.setText("  " + tr["screenshot"])
        self.btn_screenshot.setToolTip(tr["screenshot_tip"])
        self.btn_undo.setText("  " + tr["undo"])

        self.update_hide_button_state()
        self.btn_donate.setToolTip(tr["donate_tip"])
        self.btn_lang.setText(tr["next_lang"])
        self.btn_clear.setText("  " + tr["clear"])
        self.btn_exit.setText("  " + tr["exit"])

        if self.lang == "EN":
            self.btn_donate.setIcon(get_svg_icon(ICON_DOLLAR, self.icon_color))
        elif self.lang == "ZH":
            self.btn_donate.setIcon(get_svg_icon(ICON_YUAN, self.icon_color))
        else:
            self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE, self.icon_color))

        for btn in [self.btn_pen, self.btn_shape, self.btn_text, self.btn_eraser]:
            for action in btn.actions(): btn.removeAction(action)
        self.setup_menu(self.btn_pen, [2, 5, 10, 20, 30, 50], self.set_pen_width, tr["width"])
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)
        self.setup_menu(self.btn_text, [16, 24, 36, 48, 72, 100, 150, 200, 300], self.set_text_font_size, tr["size"])
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60, 100, 200], self.set_eraser_width, tr["width"])

        self.calculate_fixed_width()
        if not self.is_collapsed: self.resize(self.fixed_width, self.sizeHint().height())

    def toggle_text_mode(self):
        self.icons_only = not self.icons_only
        style = Qt.ToolButtonIconOnly if self.icons_only else Qt.ToolButtonTextBesideIcon
        start_rect = self.geometry()
        for btn in self.all_buttons:
            btn.setToolButtonStyle(style)
            if self.icons_only:
                btn.setMinimumWidth(0);
                btn.setFixedSize(44, 32)
            else:
                btn.setMinimumSize(0, 0);
                btn.setMaximumSize(16777215, 16777215);
                btn.setMinimumWidth(130)
        if self.icons_only:
            self.btn_donate.hide();
            self.btn_lang.hide();
            self.app_title.hide()
        else:
            self.btn_donate.show();
            self.btn_lang.show();
            self.app_title.show()
        self.calculate_fixed_width()
        target_rect = QRect(start_rect.topLeft(), QSize(self.fixed_width, self.sizeHint().height()))
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
            self.btn_toggle_text.hide();
            self.btn_donate.hide();
            self.btn_lang.hide();
            self.app_title.hide()
            target_rect = QRect(start_rect.left(), start_rect.top(), 56, 44)
        else:
            self.is_collapsed = False
            for btn in self.all_buttons: btn.show()
            self.btn_toggle_text.show()
            if not self.icons_only:
                self.btn_donate.show();
                self.btn_lang.show();
                self.app_title.show()
            target_rect = QRect(start_rect.left(), start_rect.top(), self.fixed_width, self.sizeHint().height())
        self.animate_geometry(start_rect, target_rect)

    def animate_geometry(self, start_rect, target_rect):
        if self.anim: self.anim.stop()
        self.anim = QPropertyAnimation(self, b"geometry")
        self.anim.setDuration(250)
        self.anim.setStartValue(start_rect)
        self.anim.setEndValue(target_rect)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.start()

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

    def choose_right_color(self, pos):
        color = QColorDialog.getColor(self.overlay.right_color, self, "Цвет правой кнопки мыши")
        if color.isValid():
            self.overlay.right_color = color
            self.overlay.set_tool("pen")
            self.raise_();
            self.activateWindow()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "", "PNG Images (*.png)")
        if file_path:
            pixmap = QPixmap(file_path)
            self.overlay.insert_pixmap(pixmap)
            self.raise_();
            self.activateWindow()

    def load_image_no_bg(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "", "PNG Images (*.png)")
        if file_path:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                processed_pixmap = self.remove_chart_background(pixmap, threshold=40)
                self.overlay.insert_pixmap(processed_pixmap)
                self.raise_();
                self.activateWindow()

    def load_folder_wheel(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder_path:
            success = self.overlay.load_folder(folder_path, remove_bg=False)
            if not success:
                QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_folder"])
            else:
                self.raise_();
                self.activateWindow()

    def load_folder_no_bg_wheel(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder_path:
            success = self.overlay.load_folder(folder_path, remove_bg=True)
            if not success:
                QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_folder"])
            else:
                self.raise_();
                self.activateWindow()

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
            processed_pixmap = self.remove_chart_background(pixmap, threshold=40)
            self.overlay.insert_pixmap(processed_pixmap)
            self.raise_();
            self.activateWindow()
        else:
            QMessageBox.information(self, "Paste Pen", self.translations[self.lang]["no_img_clip"])

    def save_image_as(self, pixmap):
        if pixmap.isNull(): return
        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить как", "", "PNG Images (*.png)")
        if file_path:
            pixmap.save(file_path, "PNG")

    def close_app(self):
        self.is_closing = True
        self.overlay.close()
        self.tray_icon.hide()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not self.is_closing:
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    mutex_name = "Paste_Pen_App_Single_Instance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)
    if ctypes.windll.kernel32.GetLastError() == 183:
        app = QApplication(sys.argv)
        QMessageBox.information(None, "Paste Pen", "Программа уже запущена.")
        sys.exit(0)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    window.raise_()
    sys.exit(app.exec_())