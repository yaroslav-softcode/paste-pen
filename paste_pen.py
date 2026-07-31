import sys
import math
import ctypes
import webbrowser
import os
import time
import tempfile
from ctypes import wintypes
from PyQt5.QtWidgets import (QApplication, QWidget, QToolBar, QAction, QLabel,
                             QFileDialog, QColorDialog, QMainWindow, QToolButton, QMenu, QLineEdit, QFrame, QVBoxLayout, QHBoxLayout, QSizePolicy, QMessageBox) # <--- Добавлено QMessageBox
from PyQt5.QtGui import QPainter, QPen, QColor, QPixmap, QCursor, QPolygonF, QFont, QFontMetrics, QIcon
from PyQt5.QtCore import Qt, QPoint, QRect, QRectF, QSize, QPointF, QPropertyAnimation, QEasingCurve, QSettings


# --- Функция для создания векторных иконок ---
def get_svg_icon(svg_path):
    pixmap = QPixmap(32, 32)
    pixmap.fill(Qt.transparent)
    pixmap.loadFromData(bytearray(svg_path, encoding='utf-8'), "SVG")
    return QIcon(pixmap)


# --- SVG иконки ---
ICON_CURSOR = '<svg viewBox="0 0 24 24" fill="white"><path d="M5.5 3.5L19 12L13 13.5L11 19.5L5.5 3.5Z"/></svg>'
ICON_PEN = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 20L8 16M8 16L16 8L20 12L12 20L4 20Z M14 6L16 4L20 8L18 10"/></svg>'
ICON_SHAPES = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="7" height="7" rx="1"/><circle cx="17.5" cy="6.5" r="3.5"/><path d="M7 15L11 21H3L7 15Z"/><path d="M14 21L21 14"/></svg>'
ICON_TEXT = '<svg viewBox="0 0 24 24" fill="white"><path d="M5 4H19V8H17V6H14V18H16V20H8V18H10V6H7V8H5V4Z"/></svg>'
ICON_ERASER = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 20H8.5a2.5 2.5 0 0 1-1.77-.73l-4.5-4.5a2.5 2.5 0 0 1 0-3.54l9.5-9.5a2.5 2.5 0 0 1 3.54 0l5.5 5.5a2.5 2.5 0 0 1 0 3.54L11.5 20"/><path d="M9 11l4 4"/></svg>'
ICON_COLOR = '<svg viewBox="0 0 24 24" fill="white"><path d="M12 2C6.5 2 2 6.5 2 12s4.5 10 10 10c1 0 2-.8 2-2 0-.5-.2-1-.6-1.4-.3-.4-.4-.8-.4-1.1 0-1 .8-1.5 1.5-1.5H17c2.8 0 5-2.2 5-5 0-4.4-4.5-8-10-8zm-5 9c-.8 0-1.5-.7-1.5-1.5S6.2 8 7 8s1.5.7 1.5 1.5S7.8 11 7 11zm3-4c-.8 0-1.5-.7-1.5-1.5S9.2 4 10 4s1.5.7 1.5 1.5S10.8 7 10 7zm4 0c-.8 0-1.5-.7-1.5-1.5S13.2 4 14 4s1.5.7 1.5 1.5S14.8 7 14 7zm3 4c-.8 0-1.5-.7-1.5-1.5S16.2 8 17 8s1.5.7 1.5 1.5S17.8 11 17 11z"/></svg>'
ICON_IMAGE = '<svg viewBox="0 0 24 24" fill="white"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg>'
ICON_SELECT = '<svg viewBox="0 0 24 24" fill="white"><path d="M12 2L8 6h3v3h2V6h3l-4-4zm0 20l4-4h-3v-3h-2v3H8l4 4zM2 12l4 4v-3h3v-2H6V8l-4 4zm20 0l-4-4v3h-3v2h3v3l4-4z"/></svg>'
ICON_SCREENSHOT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>'
ICON_UNDO = '<svg viewBox="0 0 24 24" fill="white"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg>'
ICON_HIDE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>'
ICON_SHOW = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>'
ICON_CLEAR = '<svg viewBox="0 0 24 24" fill="white"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>'
ICON_EXIT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 3h-2v10h2V3zm4.83 2.17l-1.42 1.42C17.99 7.86 19 9.81 19 12c0 3.87-3.13 7-7 7s-7-3.13-7-7c0-2.19 1.01-4.14 2.58-5.42L6.17 5.17C4.23 6.82 3 9.26 3 12c0 4.97 4.03 9 9 9s9-4.03 9-9c0-2.74-1.23-5.18-3.17-6.83z"/></svg>'

ICON_TOGGLE_TEXT = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round"><path d="M4 6h16M4 12h16M4 18h10"/></svg>'
ICON_COLLAPSE = '<svg viewBox="0 0 24 24" fill="white"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0S9.6.84 9.18 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg>'

ICON_RUBLE = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4v16"/><path d="M8 4h6a4 4 0 0 1 0 8H8"/><path d="M5 12h9"/><path d="M5 16h9"/></svg>'
ICON_DOLLAR = '<svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="2" x2="12" y2="22"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>'


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
        self.pen_color = QColor(255, 0, 0)
        self.pen_width = 3
        self.eraser_width = 20

        self.text_font_size = 24
        self.shape_type = "line"

        self.canvas = QPixmap(self.size())
        self.canvas.fill(Qt.transparent)
        self.last_pos = None

        self.drawings = []
        self.is_hidden = False

        self.moving_image = None
        self.resizing_image = None
        self.resizing_handle = None
        self.move_offset = QPoint(0, 0)
        self.resize_start_pos = QPoint(0, 0)
        self.resize_start_rect = QRect(0, 0, 0, 0)

        self.shape_start_pos = None
        self.shape_end_pos = None
        self.screenshot_start_pos = None
        self.screenshot_end_pos = None
        self.is_capturing = False
        self.text_input = None

        self.undo_stack = []
        self.unsetCursor()

    def closeEvent(self, event):
        if not self.main_window.is_closing:
            event.ignore()
        else:
            event.accept()

    def save_state(self):
        if len(self.undo_stack) >= 30:
            self.undo_stack.pop(0)
        drawings_copy = []
        for d in self.drawings:
            drawings_copy.append({
                'type': d['type'],
                'pixmap': d['pixmap'],
                'rect': QRect(d['rect']),
                'selected': d['selected']
            })
        self.undo_stack.append({'canvas': self.canvas.copy(), 'drawings': drawings_copy})

    def undo(self):
        self.commit_text()
        if self.undo_stack:
            state = self.undo_stack.pop()
            self.canvas = state['canvas']
            self.drawings = state['drawings']
            self.deselect_all_images()
            self.update()

    def nativeEvent(self, eventType, message):
        if eventType == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == 0x0084:  # WM_NCHITTEST
                pt = QPoint(msg.pt.x, msg.pt.y)

                if self.main_window.geometry().contains(pt):
                    return True, -1

                if self.tool == "cursor":
                    return True, -1

                return True, 1
        return super().nativeEvent(eventType, message)

    def set_tool(self, tool):
        if self.tool == "text" and tool != "text":
            self.commit_text()

        self.tool = tool
        if tool == "cursor":
            self.deselect_all_images()
            self.unsetCursor()
        elif tool == "eraser":
            self.update_eraser_cursor()
        elif tool == "text":
            self.setCursor(Qt.IBeamCursor)
        else:
            self.setCursor(Qt.CrossCursor)
        self.update()

    def update_eraser_cursor(self):
        size = self.eraser_width
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        color = QColor(50, 50, 50, 150)
        pen = QPen(color, 1.5)
        pen.setStyle(Qt.CustomDashLine)
        pen.setDashPattern([4, 6])
        pen.setCapStyle(Qt.RoundCap)

        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(QRectF(0.5, 0.5, size - 1, size - 1))
        painter.end()
        self.setCursor(QCursor(pixmap, int(size / 2), int(size / 2)))

    def deselect_all_images(self):
        for item in self.drawings:
            if item['type'] == 'image':
                item['selected'] = False
        self.update()

    def get_handle_rect(self, corner, item_rect):
        item_rect = item_rect.normalized()
        if corner == 'TL':
            pt = item_rect.topLeft()
        elif corner == 'TR':
            pt = item_rect.topRight()
        elif corner == 'BL':
            pt = item_rect.bottomLeft()
        elif corner == 'BR':
            pt = item_rect.bottomRight()
        return QRect(pt.x() - 5, pt.y() - 5, 10, 10)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)

        if self.tool != "cursor" and not self.is_capturing:
            painter.fillRect(self.rect(), QColor(0, 0, 0, 1))

        if not self.is_hidden:
            painter.drawPixmap(0, 0, self.canvas)

            for item in self.drawings:
                if item['type'] == 'image':
                    painter.drawPixmap(item['rect'], item['pixmap'])
                    if item.get('selected', False):
                        painter.setPen(QPen(QColor(0, 120, 215), 2, Qt.DashLine))
                        painter.drawRect(item['rect'])

                        # Отрисовка ползунков (углов)
                        for corner in ['TL', 'TR', 'BL', 'BR']:
                            handle = self.get_handle_rect(corner, item['rect'])
                            if corner == 'TR':
                                # Оранжевый квадрат для пропорционального изменения
                                painter.setBrush(QColor(255, 165, 0))
                                painter.setPen(QPen(Qt.white, 1))
                                painter.drawRect(handle)
                            else:
                                # Синие квадраты для обычного изменения
                                painter.setBrush(QColor(0, 120, 215))
                                painter.setPen(Qt.NoPen)
                                painter.drawRect(handle)

            if self.tool == "shape" and self.shape_start_pos is not None:
                pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)

                if self.shape_type == "line":
                    painter.drawLine(self.shape_start_pos, self.shape_end_pos)
                elif self.shape_type == "rect":
                    painter.drawRect(QRect(self.shape_start_pos, self.shape_end_pos).normalized())
                elif self.shape_type == "ellipse":
                    painter.drawEllipse(QRect(self.shape_start_pos, self.shape_end_pos).normalized())
                elif self.shape_type == "arrow":
                    self.draw_arrow(painter, self.shape_start_pos, self.shape_end_pos)

        # Отрисовка рамки скриншота
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

    def draw_arrow(self, painter, start, end):
        painter.drawLine(start, end)
        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = max(10, self.pen_width * 4)

        p1 = QPointF(end.x() - arrow_size * math.cos(angle - math.pi / 6),
                     end.y() - arrow_size * math.sin(angle - math.pi / 6))
        p2 = QPointF(end.x() - arrow_size * math.cos(angle + math.pi / 6),
                     end.y() - arrow_size * math.sin(angle + math.pi / 6))

        arrow_head = QPolygonF([QPointF(end), p1, p2])
        painter.setBrush(self.pen_color)
        painter.drawPolygon(arrow_head)

    def mousePressEvent(self, event):
        if event.button() not in (Qt.LeftButton, Qt.RightButton):
            return

        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.commit_text()
            self.set_tool("cursor")
            self.last_pos = None
            self.shape_start_pos = None
            self.moving_image = None
            self.resizing_image = None
            self.screenshot_start_pos = None
            return

        if self.is_hidden and self.tool != "screenshot":
            return

        if self.tool in ("pen", "eraser"):
            self.save_state()
            self.deselect_all_images()
            self.last_pos = event.pos()
            self.draw_line_to(event.pos())

        elif self.tool == "shape":
            self.save_state()
            self.deselect_all_images()
            self.shape_start_pos = event.pos()
            self.shape_end_pos = event.pos()

        elif self.tool == "screenshot":
            self.screenshot_start_pos = event.pos()
            self.screenshot_end_pos = event.pos()
            self.update()

        elif self.tool == "text":
            if event.button() == Qt.LeftButton:
                self.commit_text()
                self.save_state()
                self.deselect_all_images()

                self.text_input = QLineEdit(self)
                self.text_input.setStyleSheet(f"""
                    QLineEdit {{
                        background: rgba(255, 255, 255, 180);
                        border: 1px dashed gray;
                        color: {self.pen_color.name()};
                        font-size: {self.text_font_size}px;
                        font-family: Arial;
                        padding: 2px;
                    }}
                """)
                self.text_input.move(event.pos())
                self.text_input.show()
                self.text_input.setFocus()
                self.text_input.editingFinished.connect(self.commit_text)

        elif self.tool == "select":
            # 1. Проверка изменения размера (только левая кнопка)
            if event.button() == Qt.LeftButton:
                for item in reversed(self.drawings):
                    if item['type'] == 'image' and item.get('selected', False):
                        for corner in ['TL', 'TR', 'BL', 'BR']:
                            if self.get_handle_rect(corner, item['rect']).contains(event.pos()):
                                self.save_state()
                                self.resizing_image = item
                                self.resizing_handle = corner
                                self.resize_start_pos = event.pos()
                                self.resize_start_rect = QRect(item['rect'])
                                return

            # 2. Проверка клика по картинке (Левая - перемещение, Правая - меню)
            for item in reversed(self.drawings):
                if item['type'] == 'image' and item['rect'].contains(event.pos()):
                    if event.button() == Qt.LeftButton:
                        self.save_state()
                        self.deselect_all_images()
                        item['selected'] = True
                        self.moving_image = item
                        self.move_offset = event.pos() - item['rect'].topLeft()
                        self.update()
                        return
                    elif event.button() == Qt.RightButton:
                        self.deselect_all_images()
                        item['selected'] = True
                        self.update()

                        # Показываем контекстное меню
                        menu = QMenu(self)
                        menu.setStyleSheet("""
                            QMenu {
                                background: #1e1e1e; border: 1px solid #0a0a0a; border-radius: 8px; color: #e0e0e0; padding: 8px;
                            }
                            QMenu::item { background: transparent; padding: 10px 30px; border-radius: 4px; }
                            QMenu::item:selected { background: #333333; }
                        """)
                        tr_delete = self.main_window.translations[self.main_window.lang]["delete"]
                        delete_action = menu.addAction(tr_delete)
                        action = menu.exec_(self.mapToGlobal(event.pos()))
                        if action == delete_action:
                            self.save_state()
                            self.drawings.remove(item)
                            self.update()
                        return

            if event.button() == Qt.LeftButton:
                self.deselect_all_images()

    def commit_text(self):
        if not self.text_input:
            return

        try:
            self.text_input.editingFinished.disconnect()
        except TypeError:
            pass

        text = self.text_input.text()
        if text:
            painter = QPainter(self.canvas)
            painter.setRenderHint(QPainter.Antialiasing)

            font = QFont("Arial", self.text_font_size, QFont.Bold)
            painter.setFont(font)
            painter.setPen(self.pen_color)

            pos = self.text_input.pos()
            fm = QFontMetrics(font)
            painter.drawText(pos.x(), pos.y() + fm.ascent() + 2, text)
            painter.end()
            self.update()

        self.text_input.deleteLater()
        self.text_input = None

    def mouseMoveEvent(self, event):
        if (event.buttons() & Qt.LeftButton) and (event.buttons() & Qt.RightButton):
            self.last_pos = None
            self.shape_start_pos = None
            self.moving_image = None
            self.resizing_image = None
            self.screenshot_start_pos = None
            return

        if not (event.buttons() & (Qt.LeftButton | Qt.RightButton)):
            return

        if self.is_hidden and self.tool != "screenshot":
            return

        if self.last_pos is not None:
            self.draw_line_to(event.pos())
            self.last_pos = event.pos()

        elif self.shape_start_pos is not None:
            self.shape_end_pos = event.pos()
            self.update()

        elif self.screenshot_start_pos is not None:
            self.screenshot_end_pos = event.pos()
            self.update()

        elif self.moving_image:
            if not (event.buttons() & Qt.LeftButton):
                return
            new_top_left = event.pos() - self.move_offset
            self.moving_image['rect'].moveTopLeft(new_top_left)
            self.update()

        elif self.resizing_image:
            if not (event.buttons() & Qt.LeftButton):
                return

            delta = event.pos() - self.resize_start_pos
            new_rect = QRect(self.resize_start_rect)

            if self.resizing_handle == 'BR':
                new_rect.setBottomRight(self.resize_start_rect.bottomRight() + delta)
            elif self.resizing_handle == 'BL':
                new_rect.setBottomLeft(self.resize_start_rect.bottomLeft() + delta)
            elif self.resizing_handle == 'TR':
                # ПРОПОРЦИОНАЛЬНОЕ ИЗМЕНЕНИЕ (якорь - нижний левый угол)
                start_rect = self.resize_start_rect.normalized()
                start_w = start_rect.width()
                start_h = start_rect.height()
                if start_w > 0 and start_h > 0:
                    aspect = start_h / start_w
                    new_w = int(start_w + delta.x())
                    if new_w < 20: new_w = 20
                    new_h = int(new_w * aspect)
                    if new_h < 20: new_h = 20
                    bl = start_rect.bottomLeft()
                    # QRect(x, y, w, h)
                    new_rect = QRect(bl.x(), bl.y() - new_h + 1, new_w, new_h).normalized()
                else:
                    new_rect.setTopRight(self.resize_start_rect.topRight() + delta)
            elif self.resizing_handle == 'TL':
                new_rect.setTopLeft(self.resize_start_rect.topLeft() + delta)

            new_rect = new_rect.normalized()
            if new_rect.width() < 20: new_rect.setWidth(20)
            if new_rect.height() < 20: new_rect.setHeight(20)

            self.resizing_image['rect'] = new_rect
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() not in (Qt.LeftButton, Qt.RightButton):
            return

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

                desktop_pixmap = QApplication.primaryScreen().grabWindow(0,
                                                                         virtual_geo.x(), virtual_geo.y(),
                                                                         virtual_geo.width(), virtual_geo.height())

                pixmap_x = global_rect.x() - virtual_geo.x()
                pixmap_y = global_rect.y() - virtual_geo.y()
                pixmap_rect = QRect(pixmap_x, pixmap_y, global_rect.width(), global_rect.height())

                pixmap_rect = pixmap_rect.intersected(desktop_pixmap.rect())

                if not pixmap_rect.isEmpty():
                    screenshot_pixmap = desktop_pixmap.copy(pixmap_rect)

                    if not screenshot_pixmap.isNull():
                        temp_dir = tempfile.gettempdir()
                        filename = f"paste_pen_{int(time.time())}.png"
                        file_path = os.path.join(temp_dir, filename)
                        screenshot_pixmap.save(file_path, "PNG")
                        os.startfile(file_path)

            self.is_capturing = False
            self.set_tool("cursor")
            self.update()
            return

        if self.tool == "shape" and self.shape_start_pos is not None:
            painter = QPainter(self.canvas)
            painter.setRenderHint(QPainter.Antialiasing)
            pen = QPen(self.pen_color, self.pen_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            if self.shape_type == "line":
                painter.drawLine(self.shape_start_pos, self.shape_end_pos)
            elif self.shape_type == "rect":
                painter.drawRect(QRect(self.shape_start_pos, self.shape_end_pos).normalized())
            elif self.shape_type == "ellipse":
                painter.drawEllipse(QRect(self.shape_start_pos, self.shape_end_pos).normalized())
            elif self.shape_type == "arrow":
                self.draw_arrow(painter, self.shape_start_pos, self.shape_end_pos)

            painter.end()
            self.shape_start_pos = None
            self.shape_end_pos = None
            self.update()

        self.last_pos = None
        self.moving_image = None
        self.resizing_image = None

    def draw_line_to(self, pos):
        painter = QPainter(self.canvas)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen()
        if self.tool == "eraser":
            painter.setCompositionMode(QPainter.CompositionMode_Clear)
            pen.setColor(Qt.white)
            pen.setWidth(self.eraser_width)
        else:
            painter.setCompositionMode(QPainter.CompositionMode_SourceOver)
            pen.setColor(self.pen_color)
            pen.setWidth(self.pen_width)

        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(self.last_pos, pos)
        painter.end()

        rect = QRect(self.last_pos, pos).normalized().united(QRect(pos, pos).normalized())
        self.update(rect.adjusted(-20, -20, 20, 20))

    def insert_image(self, file_path):
        pixmap = QPixmap(file_path)
        if pixmap.isNull(): return

        if pixmap.width() > 2000 or pixmap.height() > 2000:
            pixmap = pixmap.scaled(2000, 2000, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        rect = QRect(self.width() // 2 - pixmap.width() // 2,
                     self.height() // 2 - pixmap.height() // 2,
                     pixmap.width(), pixmap.height())

        self.save_state()
        self.deselect_all_images()
        self.drawings.append({'type': 'image', 'pixmap': pixmap, 'rect': rect, 'selected': True})
        self.set_tool("select")
        self.update()

    def clear_all(self):
        self.commit_text()
        self.save_state()
        self.canvas.fill(Qt.transparent)
        self.drawings = []
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

        # Инициализация сохранения настроек
        self.settings = QSettings("PastePenApp", "PastePen")
        # Загружаем язык (по умолчанию RU)
        self.lang = self.settings.value("language", "RU", type=str)
        self.translations = {
            "RU": {
                "cursor": "Курсор", "pen": "Ручка", "shape": "Фигуры", "text": "Текст",
                "eraser": "Ластик", "color": "Цвет", "image": "Картинка", "select": "Выбор",
                "screenshot": "Скриншот", "delete": "Удалить",
                "undo": "Назад", "hide": "Скрыть", "show": "Показать", "clear": "Очистить",
                "exit": "Выход",
                "width": "Толщина: {}px", "size": "Размер: {}px",
                "line": "Линия", "rect": "Прямоугольник", "ellipse": "Эллипс", "arrow": "Стрелка",
                "next_lang": "EN", "donate_tip": "Поддержать на Boosty", "cursor_tip": "Прав. + лев. клик мыши"
            },
            "EN": {
                "cursor": "Cursor", "pen": "Pen", "shape": "Shapes", "text": "Text",
                "eraser": "Eraser", "color": "Color", "image": "Image", "select": "Select",
                "screenshot": "Screenshot", "delete": "Delete",
                "undo": "Undo", "hide": "Hide", "show": "Show", "clear": "Clear",
                "exit": "Exit",
                "width": "Width: {}px", "size": "Size: {}px",
                "line": "Line", "rect": "Rectangle", "ellipse": "Ellipse", "arrow": "Arrow",
                "next_lang": "RU", "donate_tip": "Support on DonationAlerts", "cursor_tip": "Right + Left mouse click"
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

        self.setStyleSheet("""
            QFrame#ToolbarContainer {
                background: #1e1e1e;
                border: 1px solid #0a0a0a;
                border-radius: 12px;
            }
            QToolButton {
                color: #e0e0e0;
                background: transparent;
                border: none;
                border-radius: 6px;
                padding: 4px 8px 4px 8px; 
                font-size: 18px; 
                font-family: Segoe UI;
                text-align: left;
            }
            QToolButton:hover {
                background: #333333;
                color: white;
            }
            QToolButton:pressed {
                background: #404040;
            }
            QToolButton::menu-indicator {
                image: none;
            }
            QMenu {
                background: #1e1e1e;
                border: 1px solid #0a0a0a;
                border-radius: 8px;
                color: #e0e0e0;
                padding: 8px;
                font-size: 14pt; 
            }
            QMenu::item {
                background: transparent;
                padding: 10px 30px; 
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: #333333;
            }
        """)

        self.all_buttons = []

        top_v_layout = QVBoxLayout()
        top_v_layout.setContentsMargins(0, 0, 0, 4)
        top_v_layout.setSpacing(2)

        # Ряд 1: Свернуть и Название приложения
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(4)
        row1_layout.setAlignment(Qt.AlignLeft)

        self.btn_collapse = QToolButton(self.toolbar_widget)
        self.btn_collapse.setIcon(get_svg_icon(ICON_COLLAPSE))
        self.btn_collapse.setIconSize(QSize(28, 28))
        self.btn_collapse.setToolTip("Свернуть")
        self.btn_collapse.clicked.connect(self.toggle_collapse)
        self.btn_collapse.setFixedSize(44, 32)
        row1_layout.addWidget(self.btn_collapse)

        self.app_title = QLabel("Paste Pen", self.toolbar_widget)
        self.app_title.setStyleSheet("""
            QLabel {
                color: #DAA520; 
                font-size: 20px; 
                font-family: 'Segoe Script', 'Segoe Print', cursive; 
                font-weight: bold;
                padding-left: 0px;
                padding-right: 0px;
            }
        """)
        self.app_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        row1_layout.addWidget(self.app_title)

        top_v_layout.addLayout(row1_layout)

        # Ряд 2: Текст, Рубль/Доллар, Язык
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, 0, 0, 0)
        row2_layout.setSpacing(0)
        row2_layout.setAlignment(Qt.AlignLeft)

        self.btn_toggle_text = QToolButton(self.toolbar_widget)
        self.btn_toggle_text.setIcon(get_svg_icon(ICON_TOGGLE_TEXT))
        self.btn_toggle_text.setIconSize(QSize(28, 28))
        self.btn_toggle_text.setToolTip("Скрыть/Показать текст")
        self.btn_toggle_text.clicked.connect(self.toggle_text_mode)
        self.btn_toggle_text.setFixedSize(44, 32)
        row2_layout.addWidget(self.btn_toggle_text)

        self.btn_donate = QToolButton(self.toolbar_widget)
        self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE))
        self.btn_donate.setIconSize(QSize(28, 28))
        self.btn_donate.setToolTip(tr["donate_tip"])
        self.btn_donate.clicked.connect(self.open_donate_link)
        self.btn_donate.setFixedSize(44, 32)
        row2_layout.addWidget(self.btn_donate)

        self.btn_lang = QToolButton(self.toolbar_widget)
        self.btn_lang.setText(tr["next_lang"])
        self.btn_lang.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.btn_lang.clicked.connect(self.toggle_language)
        self.btn_lang.setFixedSize(44, 32)
        row2_layout.addWidget(self.btn_lang)

        top_v_layout.addLayout(row2_layout)
        layout.addLayout(top_v_layout)

        # --- ОСНОВНЫЕ КНОПКИ ---
        self.btn_cursor = self.create_tool_button(tr["cursor"], ICON_CURSOR, lambda: self.overlay.set_tool("cursor"))
        self.btn_cursor.setToolTip(tr["cursor_tip"])  # ДОБАВЛЕНА ПОДСКАЗКА
        layout.addWidget(self.btn_cursor)

        self.btn_pen = self.create_tool_button(tr["pen"], ICON_PEN, lambda: self.overlay.set_tool("pen"))
        self.setup_menu(self.btn_pen, [2, 5, 10, 20], self.set_pen_width, tr["width"])
        layout.addWidget(self.btn_pen)

        self.btn_shape = self.create_tool_button(tr["shape"], ICON_SHAPES, lambda: self.overlay.set_tool("shape"))
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)
        layout.addWidget(self.btn_shape)

        self.btn_text = self.create_tool_button(tr["text"], ICON_TEXT, lambda: self.overlay.set_tool("text"))
        self.setup_menu(self.btn_text, [16, 24, 36, 48], self.set_text_font_size, tr["size"])
        layout.addWidget(self.btn_text)

        self.btn_eraser = self.create_tool_button(tr["eraser"], ICON_ERASER, lambda: self.overlay.set_tool("eraser"))
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60], self.set_eraser_width, tr["width"])
        layout.addWidget(self.btn_eraser)

        self.btn_color = self.create_tool_button(tr["color"], ICON_COLOR, self.choose_color)
        layout.addWidget(self.btn_color)

        self.btn_image = self.create_tool_button(tr["image"], ICON_IMAGE, self.load_image)
        layout.addWidget(self.btn_image)

        self.btn_select = self.create_tool_button(tr["select"], ICON_SELECT, lambda: self.overlay.set_tool("select"))
        layout.addWidget(self.btn_select)

        self.btn_screenshot = self.create_tool_button(tr["screenshot"], ICON_SCREENSHOT,
                                                      lambda: self.overlay.set_tool("screenshot"))
        layout.addWidget(self.btn_screenshot)

        self.btn_undo = self.create_tool_button(tr["undo"], ICON_UNDO, self.overlay.undo)
        layout.addWidget(self.btn_undo)

        self.btn_hide = self.create_tool_button(tr["hide"], ICON_HIDE, self.toggle_hide_mode)
        layout.addWidget(self.btn_hide)

        self.btn_clear = self.create_tool_button(tr["clear"], ICON_CLEAR, self.overlay.clear_all)
        layout.addWidget(self.btn_clear)

        self.btn_exit = self.create_tool_button(tr["exit"], ICON_EXIT, self.close_app)
        layout.addWidget(self.btn_exit)

        self.calculate_fixed_width()

        screen = QApplication.primaryScreen().geometry()
        self.resize(self.fixed_width, self.sizeHint().height())
        self.move(20, screen.height() // 2 - self.height() // 2)

    def calculate_fixed_width(self):
        if self.icons_only:
            self.fixed_width = 44 + 12
            return

        max_w = 0
        for btn in self.all_buttons:
            max_w = max(max_w, btn.sizeHint().width())

        top_w = 44 * 3 + 4 * 2 + 12
        row1_w = 44 + 4 + self.app_title.sizeHint().width() + 12
        top_w = max(top_w, row1_w)

        self.fixed_width = max(max_w, top_w) + 12

    def create_tool_button(self, text, icon_svg, callback):
        btn = QToolButton(self.toolbar_widget)
        btn.setText("  " + text)
        btn.setIcon(get_svg_icon(icon_svg))
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
                name = text_format.format(item)
                val = item
            act = QAction(name, btn)
            act.triggered.connect(lambda checked, v=val: callback(v))
            btn.addAction(act)

    def open_donate_link(self):
        if self.lang == "EN":
            webbrowser.open("https://www.donationalerts.com/r/yaroslavkhmelev")
        else:
            webbrowser.open("https://boosty.to/yaroslavkhmelev/donate")

    def toggle_language(self):
        self.lang = "EN" if self.lang == "RU" else "RU"
        # Сохраняем выбранный язык в реестр Windows
        self.settings.setValue("language", self.lang)
        self.update_language()

    def update_language(self):
        tr = self.translations[self.lang]
        self.btn_cursor.setText("  " + tr["cursor"])  # Добавлены пробелы
        self.btn_cursor.setToolTip(tr["cursor_tip"])
        self.btn_pen.setText("  " + tr["pen"])
        self.btn_shape.setText("  " + tr["shape"])
        self.btn_text.setText("  " + tr["text"])
        self.btn_eraser.setText("  " + tr["eraser"])
        self.btn_color.setText("  " + tr["color"])
        self.btn_image.setText("  " + tr["image"])
        self.btn_select.setText("  " + tr["select"])
        self.btn_screenshot.setText("  " + tr["screenshot"])
        self.btn_undo.setText("  " + tr["undo"])

        if self.overlay.is_hidden:
            self.btn_hide.setText("  " + tr["show"])
            self.btn_hide.setIcon(get_svg_icon(ICON_SHOW))
        else:
            self.btn_hide.setText("  " + tr["hide"])
            self.btn_hide.setIcon(get_svg_icon(ICON_HIDE))

        self.btn_donate.setToolTip(tr["donate_tip"])
        # Кнопка Язык остается без пробела, так как у нее нет иконки
        self.btn_lang.setText(tr["next_lang"])
        self.btn_clear.setText("  " + tr["clear"])
        self.btn_exit.setText("  " + tr["exit"])

        if self.lang == "EN":
            self.btn_donate.setIcon(get_svg_icon(ICON_DOLLAR))
        else:
            self.btn_donate.setIcon(get_svg_icon(ICON_RUBLE))

        for btn in [self.btn_pen, self.btn_shape, self.btn_text, self.btn_eraser]:
            for action in btn.actions():
                btn.removeAction(action)

        self.setup_menu(self.btn_pen, [2, 5, 10, 20], self.set_pen_width, tr["width"])
        self.setup_menu(self.btn_shape, [(tr["line"], "line"), (tr["rect"], "rect"), (tr["ellipse"], "ellipse"),
                                         (tr["arrow"], "arrow")], self.set_shape_type)
        self.setup_menu(self.btn_text, [16, 24, 36, 48], self.set_text_font_size, tr["size"])
        self.setup_menu(self.btn_eraser, [10, 20, 40, 60], self.set_eraser_width, tr["width"])

        self.calculate_fixed_width()
        if not self.is_collapsed:
            self.resize(self.fixed_width, self.sizeHint().height())

    def toggle_text_mode(self):
        self.icons_only = not self.icons_only
        style = Qt.ToolButtonIconOnly if self.icons_only else Qt.ToolButtonTextBesideIcon

        start_rect = self.geometry()

        for btn in self.all_buttons:
            btn.setToolButtonStyle(style)
            if self.icons_only:
                btn.setMinimumWidth(0)
                btn.setFixedSize(44, 32)
            else:
                btn.setMinimumSize(0, 0)
                btn.setMaximumSize(16777215, 16777215)
                btn.setMinimumWidth(130)

        if self.icons_only:
            self.btn_donate.hide()
            self.btn_lang.hide()
            self.app_title.hide()
        else:
            self.btn_donate.show()
            self.btn_lang.show()
            self.app_title.show()

        self.calculate_fixed_width()
        target_rect = QRect(start_rect.topLeft(), QSize(self.fixed_width, self.sizeHint().height()))
        self.animate_geometry(start_rect, target_rect)

    def toggle_hide_mode(self):
        self.overlay.toggle_hide()
        tr = self.translations[self.lang]
        if self.overlay.is_hidden:
            self.btn_hide.setText("  " + tr["show"])  # Добавлены пробелы
            self.btn_hide.setIcon(get_svg_icon(ICON_SHOW))
        else:
            self.btn_hide.setText("  " + tr["hide"])  # Добавлены пробелы
            self.btn_hide.setIcon(get_svg_icon(ICON_HIDE))

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

            for btn in self.all_buttons:
                btn.hide()
            self.btn_toggle_text.hide()
            self.btn_donate.hide()
            self.btn_lang.hide()
            self.app_title.hide()

            collapsed_width = 56
            collapsed_height = 44

            target_rect = QRect(
                start_rect.left(),
                start_rect.top(),
                collapsed_width,
                collapsed_height
            )
        else:
            self.is_collapsed = False
            for btn in self.all_buttons:
                btn.show()
            self.btn_toggle_text.show()

            if not self.icons_only:
                self.btn_donate.show()
                self.btn_lang.show()
                self.app_title.show()

            target_rect = QRect(start_rect.left(), start_rect.top(), self.fixed_width, self.sizeHint().height())

        self.animate_geometry(start_rect, target_rect)

    def animate_geometry(self, start_rect, target_rect):
        if self.anim:
            self.anim.stop()

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

    def set_text_font_size(self, size):
        self.overlay.text_font_size = size
        self.overlay.set_tool("text")

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

    def choose_color(self):
        color = QColorDialog.getColor(self.overlay.pen_color, self, "Выбор цвета")
        if color.isValid():
            self.overlay.pen_color = color
            self.overlay.set_tool("pen")
            self.raise_()
            self.activateWindow()

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Открыть изображение", "", "PNG Images (*.png)")
        if file_path:
            self.overlay.insert_image(file_path)
            self.raise_()
            self.activateWindow()

    def close_app(self):
        self.is_closing = True
        self.overlay.close()
        self.close()
        QApplication.quit()

    def closeEvent(self, event):
        if not self.is_closing:
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    # 1. Проверяем, запущена ли уже программа (через Windows Mutex)
    mutex_name = "Paste_Pen_App_Single_Instance_Mutex"
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, mutex_name)

    # Если GetLastError() вернет 183, значит мьютекс уже существует (программа запущена)
    if ctypes.windll.kernel32.GetLastError() == 183:
        app = QApplication(sys.argv)
        QMessageBox.information(None, "Paste Pen", "Программа уже запущена.")
        sys.exit(0)

    # 2. Если это первый запуск, запускаем программу нормально
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = MainWindow()
    window.show()
    window.raise_()
    sys.exit(app.exec_())