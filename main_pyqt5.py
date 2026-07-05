#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Folder - 快捷文件夹面板 (PyQt5 版本)
一个可以固定在最顶层的文件夹快捷入口面板

功能:
  - 始终置顶的轻量面板（可取消置顶）
  - 常用 / 非常用分区
  - 每个文件夹：打开 / 关闭 / 粘贴 / 分区切换
  - 拖拽调整文件夹顺序
  - 粘贴文件到文件夹（带进度条）
  - 自动保存配置，重启后恢复
"""

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QListWidget, QListWidgetItem, QTabWidget,
    QFileDialog, QMessageBox, QProgressBar, QDialog, QLineEdit,
    QGroupBox, QFrame, QSplitter, QMenu, QAction, QSystemTrayIcon,
    QStyle, QDesktopWidget, QScrollArea, QSizePolicy, QComboBox, QCheckBox,
    QGridLayout, QInputDialog, QFileIconProvider, QPlainTextEdit
)
from PyQt5.QtCore import (
    Qt, QSize, QPoint, QTimer, QThread, pyqtSignal, QMimeData,
    QUrl, QPropertyAnimation, QEasingCurve, QObject, QEvent,
    QCoreApplication, QFileInfo
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
    QDragEnterEvent, QDropEvent, QMouseEvent, QCursor,
    QLinearGradient, QBrush, QPen, QFontMetrics, QDrag
)
import json
import os
import sys
import subprocess
import shutil
import ctypes
import zipfile
import tarfile
import re
from pathlib import Path
from typing import List, Tuple, Optional

# ============================================================
# 配置
# ============================================================
CONFIG_FILE = Path(__file__).parent / "config.json"

FOLDER_ACTION_MIME = "application/x-quick-folder-action"
FOLDER_ACTION_SLOT_COUNT = 4
DEFAULT_FOLDER_ACTION_ORDER = [
    "open",
    "paste",
    "reorder",
    "rename",
    "new_folder",
    "delete_archives",
    "classify",
    "remove_prefix",
]
FOLDER_ACTIONS = {
    "open": {"label": "打开", "width": 50},
    "paste": {"label": "粘贴", "width": 50},
    "reorder": {"label": "重排序", "width": 65},
    "rename": {"label": "重命名", "width": 65},
    "delete_archives": {"label": "删除zip", "width": 70},
    "classify": {"label": "分类", "width": 50},
    "new_folder": {"label": "新建", "width": 50},
    "remove_prefix": {"label": "删前缀", "width": 60},
}
FOLDER_DELETE_BUTTON_WIDTH = 34
FOLDER_ACTION_BUTTON_SPACING = 4
FOLDER_ACTION_ROW_RIGHT_INSET = 28
ARCHIVE_EXTENSIONS = (
    ".zip", ".rar", ".7z", ".tar", ".tar.gz", ".tgz", ".tar.bz2", ".tbz2",
    ".tar.xz", ".txz", ".gz", ".bz2", ".xz", ".lz", ".lzma", ".zst",
    ".cab", ".iso", ".jar", ".war",
)

# ----- 主题定义 -----
THEMES = {
    "dark_teal": {
        "name": "暗色 teal",
        "bg": "#2b2b2b",
        "fg": "#e0e0e0",
        "title_bg": "#1a1a1a",
        "section_bg": "#333333",
        "item_bg": "#3c3c3c",
        "item_hover": "#484848",
        "btn_bg": "#505050",
        "btn_hover": "#606060",
        "accent": "#26a69a",
        "accent_hover": "#2bbbad",
        "danger": "#ef5350",
        "success": "#66bb6a",
        "gold": "#ffd54f",
        "gray": "#9e9e9e",
        "border": "#444444",
        "tab_active": "#26a69a",
        "tab_inactive": "#252525",
        "tab_hover": "#3a3a3a",
    },
    "dark_blue": {
        "name": "暗色 blue",
        "bg": "#1e1e2e",
        "fg": "#cdd6f4",
        "title_bg": "#11111b",
        "section_bg": "#313244",
        "item_bg": "#45475a",
        "item_hover": "#585b70",
        "btn_bg": "#585b70",
        "btn_hover": "#6c7086",
        "accent": "#89b4fa",
        "accent_hover": "#b4d0fb",
        "danger": "#f38ba8",
        "success": "#a6e3a1",
        "gold": "#f9e2af",
        "gray": "#6c7086",
        "border": "#45475a",
        "tab_active": "#89b4fa",
        "tab_inactive": "#1e1e2e",
        "tab_hover": "#313244",
    },
    "dark_purple": {
        "name": "暗色 purple",
        "bg": "#20202a",
        "fg": "#e0d4f5",
        "title_bg": "#15151f",
        "section_bg": "#2d2d3d",
        "item_bg": "#38384a",
        "item_hover": "#484860",
        "btn_bg": "#4a4a62",
        "btn_hover": "#5c5c78",
        "accent": "#b48ead",
        "accent_hover": "#c8a8d0",
        "danger": "#bf616a",
        "success": "#a3be8c",
        "gold": "#ebcb8b",
        "gray": "#81a1c1",
        "border": "#3d3d52",
        "tab_active": "#b48ead",
        "tab_inactive": "#20202a",
        "tab_hover": "#2d2d3d",
    },
    "light": {
        "name": "浅色",
        "bg": "#f5f5f5",
        "fg": "#333333",
        "title_bg": "#e8e8e8",
        "section_bg": "#ffffff",
        "item_bg": "#ffffff",
        "item_hover": "#f0f0f0",
        "btn_bg": "#e0e0e0",
        "btn_hover": "#d0d0d0",
        "accent": "#00897b",
        "accent_hover": "#00796b",
        "danger": "#d32f2f",
        "success": "#388e3c",
        "gold": "#f9a825",
        "gray": "#757575",
        "border": "#d0d0d0",
        "tab_active": "#00897b",
        "tab_inactive": "#e8e8e8",
        "tab_hover": "#d5d5d5",
    },
}


def get_theme():
    """获取当前主题"""
    return THEMES.get("dark_teal")


C = get_theme()


def generate_stylesheet(theme: dict) -> str:
    """根据主题生成 QSS 样式表"""
    return f"""
    QMainWindow {{
        background-color: {theme['bg']};
    }}
    QWidget {{
        background-color: {theme['bg']};
        color: {theme['fg']};
    }}
    QPushButton {{
        background-color: {theme['btn_bg']};
        color: {theme['fg']};
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 12px;
    }}
    QPushButton:hover {{
        background-color: {theme['btn_hover']};
    }}
    QPushButton:pressed {{
        background-color: {theme['accent']};
    }}
    QListWidget {{
        background-color: {theme['item_bg']};
        border: 1px solid {theme['border']};
        border-radius: 4px;
        padding: 4px 4px 0 4px;
    }}
    QListWidget::item {{
        padding: 8px 8px 4px 8px;
        border-radius: 4px;
    }}
    QListWidget::item:selected {{
        background-color: {theme['accent']};
        color: white;
    }}
    QListWidget::item:hover {{
        background-color: {theme['item_hover']};
    }}
    QTabWidget::pane {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        background-color: {theme['bg']};
    }}
    QTabBar::tab {{
        background-color: {theme['tab_inactive']};
        color: {theme['gray']};
        padding: 8px 16px;
        border: none;
        border-radius: 4px 4px 0 0;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {theme['tab_active']};
        color: {theme['fg']};
    }}
    QTabBar::tab:hover {{
        background-color: {theme['tab_hover']};
    }}
    QLabel {{
        background-color: transparent;
    }}
    QLineEdit {{
        background-color: {theme['item_bg']};
        color: {theme['fg']};
        border: 1px solid {theme['border']};
        padding: 6px;
        border-radius: 4px;
    }}
    QProgressBar {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        text-align: center;
    }}
    QProgressBar::chunk {{
        background-color: {theme['accent']};
        border-radius: 3px;
    }}
    QGroupBox {{
        border: 1px solid {theme['border']};
        border-radius: 4px;
        margin-top: 12px;
        padding-top: 12px;
        padding-bottom: 0px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
    }}
    """


# ============================================================
# 自定义组件
# ============================================================


class DraggableListWidget(QListWidget):
    """支持拖拽排序和外部拖入的列表控件，无滚动条，根据内容自适应高度"""

    _last_dragged_data = None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.DragDrop)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.setMinimumHeight(45)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self._drop_callback = None
        self._move_callback = None

    def set_drop_callback(self, callback):
        self._drop_callback = callback

    def set_move_callback(self, callback):
        self._move_callback = callback

    def startDrag(self, actions):
        item = self.currentItem()
        if item:
            DraggableListWidget._last_dragged_data = item.data(Qt.UserRole)
        super().startDrag(actions)

    def sizeHint(self):
        count = self.count()
        if count == 0:
            return QSize(super().sizeHint().width(), 45)
        h = count * 55
        return QSize(super().sizeHint().width(), h)

    def minimumSizeHint(self):
        return QSize(100, 45)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            # 内部拖拽或跨列表拖拽
            source = event.source()
            if source and source != self:
                event.acceptProposedAction()
            else:
                super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            source = event.source()
            if source and source != self:
                event.acceptProposedAction()
            else:
                super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            # 外部文件/文件夹拖入
            folders = []
            for url in event.mimeData().urls():
                path = url.toLocalFile()
                if path and os.path.isdir(path):
                    folders.append(path)
            if folders and self._drop_callback:
                self._drop_callback(folders)
            event.acceptProposedAction()
        else:
            # 跨列表拖拽（从另一个列表拖入）
            source = event.source()
            if source and source != self and self._move_callback:
                folder_data = DraggableListWidget._last_dragged_data
                if folder_data:
                    DraggableListWidget._last_dragged_data = None
                    drop_row = self.row(self.itemAt(event.pos()))
                    if drop_row < 0:
                        drop_row = self.count()
                    self._move_callback(folder_data, drop_row)
                    event.acceptProposedAction()
                    return
            # 内部拖拽排序
            super().dropEvent(event)


class FolderActionButton(QPushButton):
    def __init__(self, action_id: str, theme: dict, parent=None):
        super().__init__(FOLDER_ACTIONS.get(action_id, {}).get("label", action_id), parent)
        self.action_id = action_id
        self.theme = theme
        self.drag_start_pos = QPoint()
        self.dragging = False
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(FOLDER_ACTIONS.get(action_id, {}).get("width", 60), 30)
        self.setStyleSheet(self.button_style(theme))

    @staticmethod
    def button_style(theme: dict) -> str:
        return f"""
            QPushButton {{
                background-color: {theme['btn_bg']};
                color: {theme['fg']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['accent']};
                color: white;
            }}
        """

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.dragging = False
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self.dragging = True
        mime = QMimeData()
        mime.setData(FOLDER_ACTION_MIME, self.action_id.encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        if self.dragging:
            self.dragging = False
            event.accept()
            return
        super().mouseReleaseEvent(event)


class FolderActionSlotButton(FolderActionButton):
    action_dropped = pyqtSignal(int, str)

    def __init__(self, action_id: str, slot_index: int, theme: dict, parent=None):
        super().__init__(action_id, theme, parent)
        self.slot_index = slot_index
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            action_id = bytes(event.mimeData().data(FOLDER_ACTION_MIME)).decode("utf-8")
            self.action_dropped.emit(self.slot_index, action_id)
            event.acceptProposedAction()


class FolderActionOrderWidget(QWidget):
    order_changed = pyqtSignal(list)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.order = []
        self.setAcceptDrops(True)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(6)

    def set_order(self, order: list):
        self.order = list(order)
        self.rebuild()

    def rebuild(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for index, action_id in enumerate(self.order):
            btn = FolderActionSlotButton(action_id, index, self.theme)
            btn.action_dropped.connect(self.move_action_to_slot)
            self.layout.addWidget(btn)
        self.layout.addStretch()

    def move_action_to_slot(self, slot_index: int, action_id: str):
        order = [a for a in self.order if a in FOLDER_ACTIONS]
        if action_id not in FOLDER_ACTIONS:
            return
        if action_id in order:
            order.remove(action_id)
        slot_index = max(0, min(slot_index, len(order)))
        order.insert(slot_index, action_id)
        self.order = order
        self.rebuild()
        self.order_changed.emit(self.order)

    def dragEnterEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat(FOLDER_ACTION_MIME):
            action_id = bytes(event.mimeData().data(FOLDER_ACTION_MIME)).decode("utf-8")
            self.move_action_to_slot(len(self.order), action_id)
            event.acceptProposedAction()


class FolderItemWidget(QWidget):
    """文件夹项组件"""
    # 信号：删除请求
    delete_requested = pyqtSignal(str)
    section_toggled = pyqtSignal(str, bool)
    rename_requested = pyqtSignal(str, str)
    action_slot_replaced = pyqtSignal(int, str)
    clicked = pyqtSignal()

    _current_selected = None

    def __init__(self, path: str, display_name: str, is_common: bool, theme: dict,
                 action_order: list = None, remove_prefixes: list = None, parent=None):
        super().__init__(parent)
        self.path = path
        self.display_name = display_name
        self.is_common = is_common
        self.theme = theme
        self.action_order = action_order or DEFAULT_FOLDER_ACTION_ORDER
        self.remove_prefixes = remove_prefixes or []
        self._name_full_text = display_name
        self._selected = False
        self._normal_bg = theme['item_bg']
        self._selected_bg = theme['item_hover']

        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 4, 8, 4)
        layout.setSpacing(4)

        # 左侧：图标和名称
        self.sec_icon = QLabel("⭐" if is_common else "📦")
        self.sec_icon.setFont(QFont("Segoe UI Emoji", 11))
        self.sec_icon.setCursor(Qt.PointingHandCursor)
        self.sec_icon.setStyleSheet("background: transparent; padding: 2px;")
        self.sec_icon.mousePressEvent = lambda e: self.section_toggled.emit(self.path, self.is_common)
        layout.addWidget(self.sec_icon)

        exists = os.path.exists(path)
        folder_icon = QLabel("📂" if exists else "⚠️")
        folder_icon.setFont(QFont("Segoe UI Emoji", 11))
        layout.addWidget(folder_icon)

        self.name_label = QLabel(display_name)
        self.name_label.setFont(QFont("Segoe UI", 10))
        self.name_label.setStyleSheet(f"color: {theme['fg'] if exists else theme['danger']}; background: transparent;")
        self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.name_label.setMinimumWidth(0)
        self.name_label.setToolTip(display_name)
        layout.addWidget(self.name_label, 1)

        button_box = QWidget()
        button_box.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        button_box.setStyleSheet("background: transparent;")
        button_layout = QHBoxLayout(button_box)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(FOLDER_ACTION_BUTTON_SPACING)

        # 右侧：可配置功能按钮，删除按钮固定保留
        for slot_index, action_id in enumerate(self.action_order[:FOLDER_ACTION_SLOT_COUNT]):
            btn = FolderActionSlotButton(action_id, slot_index, theme)
            btn.clicked.connect(lambda checked=False, aid=action_id: self.run_action(aid))
            btn.action_dropped.connect(self.action_slot_replaced)
            button_layout.addWidget(btn)

        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(FOLDER_DELETE_BUTTON_WIDTH, 30)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['btn_bg']};
                color: {theme['fg']};
                border: none;
                border-radius: 4px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {theme['danger']};
                color: white;
            }}
        """)
        del_btn.clicked.connect(lambda: self.delete_requested.emit(self.path))
        button_layout.addWidget(del_btn)
        button_box.setFixedWidth(button_layout.sizeHint().width())
        layout.addWidget(button_box)
        self._update_name_elide()

    def event(self, e):
        if e.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease,
                         QEvent.MouseMove, QEvent.MouseButtonDblClick):
            w = self.parentWidget()
            while w:
                if isinstance(w, DraggableListWidget):
                    QCoreApplication.sendEvent(w, e)
                    break
                w = w.parentWidget()
        return super().event(e)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_name_elide()

    def _update_name_elide(self):
        if not hasattr(self, "name_label"):
            return
        metrics = QFontMetrics(self.name_label.font())
        self.name_label.setText(metrics.elidedText(self._name_full_text, Qt.ElideRight, max(0, self.name_label.width() - 4)))

    def _on_click(self, event):
        """点击切换选中状态"""
        if event.button() == Qt.LeftButton:
            self._toggle_selected()
            self.clicked.emit()

    def _toggle_selected(self):
        """切换选中状态"""
        if FolderItemWidget._current_selected and FolderItemWidget._current_selected != self:
            FolderItemWidget._current_selected._selected = False
            FolderItemWidget._current_selected.setStyleSheet(
                f"background-color: {FolderItemWidget._current_selected._normal_bg}; border-radius: 4px;"
            )
        self._selected = not self._selected
        if self._selected:
            FolderItemWidget._current_selected = self
        else:
            FolderItemWidget._current_selected = None
        bg = self._selected_bg if self._selected else self._normal_bg
        self.setStyleSheet(f"background-color: {bg}; border-radius: 4px;")

    def open_folder(self):
        """打开文件夹"""
        if os.path.exists(self.path):
            if sys.platform == "win32":
                os.startfile(self.path)
            elif sys.platform == "darwin":
                subprocess.run(["open", self.path])
            else:
                subprocess.run(["xdg-open", self.path])
        else:
            QMessageBox.warning(self, "提示", f"文件夹不存在:\n{self.path}")

    def run_action(self, action_id: str):
        actions = {
            "open": self.open_folder,
            "paste": self.paste_to,
            "reorder": self.reorder_files,
            "rename": self.rename_folder,
            "delete_archives": self.delete_archive_files,
            "classify": self.classify_files,
            "new_folder": self.create_child_folder,
            "remove_prefix": self.remove_file_prefixes,
        }
        action = actions.get(action_id)
        if action:
            action()

    def rename_folder(self):
        """重命名文件夹（实际文件夹和显示名称）"""
        from PyQt5.QtWidgets import QInputDialog
        new_name, ok = QInputDialog.getText(
            self, "重命名",
            "输入新名称:",
            text=self.display_name
        )
        if ok and new_name.strip():
            self.rename_requested.emit(self.path, new_name.strip())

    def ensure_folder_exists(self) -> bool:
        if os.path.isdir(self.path):
            return True
        QMessageBox.warning(self, "提示", f"文件夹不存在:\n{self.path}")
        return False

    def delete_archive_files(self):
        if not self.ensure_folder_exists():
            return
        archives = []
        for name in os.listdir(self.path):
            full_path = os.path.join(self.path, name)
            lower_name = name.lower()
            if os.path.isfile(full_path) and lower_name.endswith(ARCHIVE_EXTENSIONS):
                archives.append(full_path)
        if not archives:
            QMessageBox.information(self, "提示", "文件夹内没有压缩包")
            return
        reply = QMessageBox.question(
            self, "确认删除",
            f"将删除 {len(archives)} 个压缩包文件。\n\n确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        deleted, errors = 0, 0
        for file_path in archives:
            try:
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                errors += 1
                print(f"删除压缩包失败: {file_path} -> {e}")
        msg = f"已删除 {deleted} 个压缩包"
        if errors:
            msg += f"\n{errors} 个压缩包删除失败"
        QMessageBox.information(self, "完成", msg)

    def classify_files(self):
        if not self.ensure_folder_exists():
            return
        files = [
            os.path.join(self.path, name)
            for name in os.listdir(self.path)
            if os.path.isfile(os.path.join(self.path, name))
        ]
        if not files:
            QMessageBox.information(self, "提示", "文件夹内没有文件")
            return
        moved, errors = 0, 0
        for file_path in files:
            name = os.path.basename(file_path)
            ext = os.path.splitext(name)[1].lower().lstrip(".") or "无后缀"
            target_dir = os.path.join(self.path, ext)
            try:
                os.makedirs(target_dir, exist_ok=True)
                dst = os.path.join(target_dir, name)
                if os.path.abspath(dst) == os.path.abspath(file_path):
                    continue
                if os.path.exists(dst):
                    base, suffix = os.path.splitext(dst)
                    counter = 1
                    while os.path.exists(f"{base}_{counter}{suffix}"):
                        counter += 1
                    dst = f"{base}_{counter}{suffix}"
                shutil.move(file_path, dst)
                moved += 1
            except Exception as e:
                errors += 1
                print(f"分类失败: {file_path} -> {e}")
        msg = f"已分类 {moved} 个文件"
        if errors:
            msg += f"\n{errors} 个文件分类失败"
        QMessageBox.information(self, "完成", msg)

    def create_child_folder(self):
        if not self.ensure_folder_exists():
            return
        name, ok = QInputDialog.getText(self, "新建文件夹", "输入文件夹名称:", text="新建文件夹")
        if not ok or not name.strip():
            return
        new_path = os.path.join(self.path, name.strip())
        try:
            os.makedirs(new_path, exist_ok=False)
            QMessageBox.information(self, "完成", f"已新建文件夹:\n{new_path}")
        except FileExistsError:
            QMessageBox.warning(self, "提示", "同名文件夹已存在")
        except Exception as e:
            QMessageBox.warning(self, "失败", f"新建文件夹失败:\n{e}")

    def remove_file_prefixes(self):
        if not self.ensure_folder_exists():
            return
        prefixes = [p for p in self.remove_prefixes if p]
        if not prefixes:
            QMessageBox.information(self, "提示", "请先在设置中配置要删除的前缀")
            return
        renamed, errors = 0, 0
        for name in os.listdir(self.path):
            old_path = os.path.join(self.path, name)
            if not os.path.isfile(old_path):
                continue
            matched = next((prefix for prefix in prefixes if name.startswith(prefix)), "")
            if not matched:
                continue
            new_name = name[len(matched):]
            if not new_name:
                continue
            new_path = os.path.join(self.path, new_name)
            if os.path.exists(new_path):
                errors += 1
                continue
            try:
                os.rename(old_path, new_path)
                renamed += 1
            except Exception as e:
                errors += 1
                print(f"删除前缀失败: {old_path} -> {e}")
        msg = f"已处理 {renamed} 个文件"
        if errors:
            msg += f"\n{errors} 个文件处理失败"
        QMessageBox.information(self, "完成", msg)

    def paste_to(self):
        """粘贴剪贴板中的文件到此文件夹"""
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        if mime.hasUrls():
            files = [url.toLocalFile() for url in mime.urls() if url.isLocalFile()]
            if files:
                self._copy_files(files)

    def _copy_files(self, files: list):
        """复制文件到目标文件夹"""
        if not os.path.exists(self.path):
            os.makedirs(self.path, exist_ok=True)

        copied = 0
        errors = 0
        for src in files:
            try:
                if os.path.isfile(src):
                    dst = os.path.join(self.path, os.path.basename(src))
                    shutil.copy2(src, dst)
                    copied += 1
                elif os.path.isdir(src):
                    dst = os.path.join(self.path, os.path.basename(src))
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    copied += 1
            except Exception as e:
                errors += 1
                print(f"复制失败: {src} -> {e}")

        if copied > 0:
            msg = f"已粘贴 {copied} 个文件到 {self.display_name}"
            if errors > 0:
                msg += f"\n{errors} 个文件复制失败"
            QMessageBox.information(self, "粘贴完成", msg)

    def reorder_files(self):
        """重命名排序文件夹内的文件"""
        if not os.path.exists(self.path):
            QMessageBox.warning(self, "提示", f"文件夹不存在:\n{self.path}")
            return

        # 获取所有文件
        files = []
        for f in os.listdir(self.path):
            full_path = os.path.join(self.path, f)
            if os.path.isfile(full_path):
                files.append(f)

        if not files:
            QMessageBox.information(self, "提示", "文件夹内没有文件")
            return

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认重排序",
            f"将对 {len(files)} 个文件按名称排序并重命名为 01, 02, 03...\n\n确定继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        # 按文件名排序
        files.sort()

        # 重命名
        renamed = 0
        errors = 0
        for i, old_name in enumerate(files, 1):
            try:
                old_path = os.path.join(self.path, old_name)
                ext = os.path.splitext(old_name)[1]
                new_name = f"{i:02d}{ext}"
                new_path = os.path.join(self.path, new_name)

                # 如果新文件名已存在，跳过
                if os.path.exists(new_path) and old_path != new_path:
                    continue

                os.rename(old_path, new_path)
                renamed += 1
            except Exception as e:
                errors += 1
                print(f"重命名失败: {old_name} -> {e}")

        msg = f"已重命名 {renamed} 个文件"
        if errors > 0:
            msg += f"\n{errors} 个文件重命名失败"
        QMessageBox.information(self, "完成", msg)


class LaunchGridArea(QWidget):
    files_dropped = pyqtSignal(list)
    item_dropped = pyqtSignal(int, int)

    def __init__(self, theme: dict, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.running_cells = set()
        self.setAcceptDrops(True)
        self.setMinimumHeight(220)
        self.setStyleSheet(f"background-color: {theme['item_bg']}; border: 1px solid {theme['border']}; border-radius: 4px;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-quick-folder-launch-index"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-quick-folder-launch-index"):
            event.acceptProposedAction()

    def dropEvent(self, event):
        if event.mimeData().hasFormat("application/x-quick-folder-launch-index"):
            try:
                from_index = int(bytes(event.mimeData().data("application/x-quick-folder-launch-index")).decode("utf-8"))
                self.item_dropped.emit(from_index, self.cell_index_at(event.pos()))
                event.acceptProposedAction()
                return
            except Exception:
                pass
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.toLocalFile() and os.path.isfile(u.toLocalFile())]
        if paths:
            self.files_dropped.emit(paths)
            event.acceptProposedAction()

    def cell_index_at(self, pos: QPoint) -> int:
        cols, cell_h = 4, 102
        cell_w = max(1, self.width() // cols)
        col = max(0, min(cols - 1, pos.x() // cell_w))
        row = max(0, pos.y() // cell_h)
        return int(row * cols + col)

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, False)
        cols, cell_h = 4, 102
        cell_w = max(1, self.width() // cols)
        for idx in self.running_cells:
            row, col = divmod(idx, cols)
            x, y = col * cell_w, row * cell_h
            w = self.width() - x if col == cols - 1 else cell_w
            painter.fillRect(x, y, w, cell_h, QColor(self.theme["tab_active"]))
        normal_pen = QPen(QColor(self.theme["gray"]))
        active_pen = QPen(QColor(self.theme["accent_hover"]))
        for pen in (normal_pen, active_pen):
            pen.setWidth(1)
        rows = max(1, (self.layout().count() + cols - 1) // cols) if self.layout() else 1
        for col in range(1, cols):
            x = col * cell_w
            touches = any((r * cols + col - 1 in self.running_cells) or (r * cols + col in self.running_cells) for r in range(rows))
            painter.setPen(active_pen if touches else normal_pen)
            painter.drawLine(x, 0, x, self.height())
        y = cell_h
        while y < self.height():
            row = y // cell_h
            touches = any(((row - 1) * cols + c in self.running_cells) or (row * cols + c in self.running_cells) for c in range(cols))
            painter.setPen(active_pen if touches else normal_pen)
            painter.drawLine(0, y, self.width(), y)
            y += cell_h

    def set_cell_running(self, index: int, running: bool):
        if running:
            self.running_cells.add(index)
        else:
            self.running_cells.discard(index)
        self.update()


class LaunchCellWidget(QWidget):
    def __init__(self, theme: dict, index: int, parent=None):
        super().__init__(parent)
        self.index = index
        self.setFixedHeight(102)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addStretch()

    def update_state(self, running: bool):
        parent = self.parentWidget()
        if isinstance(parent, LaunchGridArea):
            parent.set_cell_running(self.index, running)


class LaunchItemWidget(QWidget):
    launch_requested = pyqtSignal(dict)
    close_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)

    def __init__(self, item: dict, theme: dict, parent=None):
        super().__init__(parent)
        self.item = item
        self.theme = theme
        self.running = False
        self.drag_start_pos = QPoint()
        self.dragging = False
        self.setCursor(Qt.PointingHandCursor)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.setFixedHeight(100)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addStretch(1)
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.apply_icon()
        layout.addWidget(self.icon_label)
        self.name_label = QLabel(item.get("name") or os.path.basename(item.get("path", "")) or "App")
        self.name_label.setAlignment(Qt.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setFont(QFont("Segoe UI", 9, QFont.Bold))
        layout.addWidget(self.name_label)
        layout.addStretch(1)
        self.update_state(False)

    def apply_icon(self):
        path = self.item.get("path", "")
        if path and os.path.exists(path):
            pix = QFileIconProvider().icon(QFileInfo(path)).pixmap(34, 34)
            if not pix.isNull():
                self.icon_label.setPixmap(pix)
                return
        self.icon_label.setText("APP")

    def update_state(self, running: bool):
        self.running = running
        parent = self.parentWidget()
        if isinstance(parent, LaunchCellWidget):
            parent.update_state(running)
        self.setStyleSheet(f"background: transparent; border: none; color: {'white' if running else self.theme['fg']};")
        self.name_label.setStyleSheet(f"color: {'white' if running else self.theme['fg']}; background: transparent;")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            self.dragging = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if not (event.buttons() & Qt.LeftButton):
            super().mouseMoveEvent(event)
            return
        if (event.pos() - self.drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return
        self.dragging = True
        mime = QMimeData()
        mime.setData("application/x-quick-folder-launch-index", str(self.item.get("_grid_index", -1)).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(event.pos())
        drag.exec_(Qt.MoveAction)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.running and not self.dragging:
            self.close_requested.emit(self.item)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.launch_requested.emit(self.item)
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def show_context_menu(self, pos):
        menu = QMenu(self)
        act = QAction("删除快捷方式", self)
        act.triggered.connect(lambda: self.delete_requested.emit(self.item))
        menu.addAction(act)
        menu.exec_(self.mapToGlobal(pos))


class MergeFolderItemWidget(QWidget):
    """文件夹合并项组件"""

    def __init__(self, path: str, display_name: str, theme: dict, parent=None):
        super().__init__(parent)
        self.path = path
        self.display_name = display_name
        self.theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)

        # 文件夹图标
        icon_label = QLabel("📁")
        icon_label.setFont(QFont("Segoe UI Emoji", 10))
        layout.addWidget(icon_label)

        # 名称
        name_label = QLabel(display_name)
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet(f"color: {theme['fg']};")
        layout.addWidget(name_label, 1)

        # 完整路径
        path_label = QLabel(path)
        path_label.setFont(QFont("Segoe UI", 8))
        path_label.setStyleSheet(f"color: {theme['gray']};")
        layout.addWidget(path_label, 1)

        # 删除按钮
        delete_btn = QPushButton("🗑")
        delete_btn.setFixedSize(28, 28)
        delete_btn.setStyleSheet(f"background-color: {theme['danger']}; color: white;")
        layout.addWidget(delete_btn)


# ============================================================
# 工作线程
# ============================================================


class CopyWorker(QThread):
    """复制文件的工作线程"""
    progress = pyqtSignal(int, int)  # current, total
    finished = pyqtSignal(int, int)  # copied, errors
    error = pyqtSignal(str)

    def __init__(self, files: list, destination: str):
        super().__init__()
        self.files = files
        self.destination = destination
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        copied = 0
        errors = 0
        total = len(self.files)

        for i, src in enumerate(self.files):
            if self._cancelled:
                break

            try:
                if os.path.isfile(src):
                    dst = os.path.join(self.destination, os.path.basename(src))
                    # 处理重名
                    if os.path.exists(dst):
                        base, ext = os.path.splitext(dst)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        dst = f"{base}_{counter}{ext}"
                    shutil.copy2(src, dst)
                    copied += 1
                elif os.path.isdir(src):
                    dst = os.path.join(self.destination, os.path.basename(src))
                    if os.path.exists(dst):
                        base = dst
                        counter = 1
                        while os.path.exists(f"{base}_{counter}"):
                            counter += 1
                        dst = f"{base}_{counter}"
                    shutil.copytree(src, dst)
                    copied += 1
            except Exception as e:
                errors += 1
                self.error.emit(f"复制失败: {src} -> {e}")

            self.progress.emit(i + 1, total)

        self.finished.emit(copied, errors)


class MergeWorker(QThread):
    """合并文件夹的工作线程"""
    progress = pyqtSignal(int, int, str)  # current, total, filename
    finished = pyqtSignal(int, int)  # copied, renamed
    error = pyqtSignal(str)

    def __init__(self, folders: list, output_dir: str):
        super().__init__()
        self.folders = folders
        self.output_dir = output_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        copied = 0
        renamed = 0

        # 计算总文件数
        total_files = 0
        for folder_path, _ in self.folders:
            for root, dirs, files in os.walk(folder_path):
                total_files += len(files)

        current = 0
        for folder_path, _ in self.folders:
            for root, dirs, files in os.walk(folder_path):
                for fname in files:
                    if self._cancelled:
                        return

                    src = os.path.join(root, fname)
                    rel = os.path.relpath(src, folder_path)
                    dst = os.path.join(self.output_dir, rel)

                    # 处理重名文件
                    if os.path.exists(dst):
                        base, ext = os.path.splitext(dst)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        dst = f"{base}_{counter}{ext}"
                        renamed += 1

                    try:
                        os.makedirs(os.path.dirname(dst), exist_ok=True)
                        shutil.copy2(src, dst)
                        copied += 1
                    except Exception as e:
                        self.error.emit(f"复制失败: {src} -> {e}")

                    current += 1
                    self.progress.emit(current, total_files, fname)

        self.finished.emit(copied, renamed)


# ============================================================
# 主窗口
# ============================================================


class QuickFolderPanel(QMainWindow):
    """快捷文件夹面板主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Quick Folder")
        self.setMinimumSize(400, 300)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # 设置窗口图标
        icon_path = Path(__file__).parent / "icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))
        else:
            self.setWindowIcon(QIcon.fromTheme("folder"))

        # 加载配置
        self.config = self.load_config()
        self.theme_name = self.config.get("theme", "dark_teal")
        self.theme = THEMES.get(self.theme_name, THEMES["dark_teal"])
        self.folder_action_order = self.normalize_folder_action_order(self.config.get("folder_action_order"))
        self.folder_remove_prefixes = self.parse_prefix_config(self.config.get("folder_remove_prefixes", ""))
        self.launch_items = self.load_launch_items()
        self.launch_processes = {}
        self.launch_tiles = {}
        self.running_launch_paths = set()
        self.running_launch_pids = {}
        self.launch_timer = QTimer(self)
        self.launch_timer.timeout.connect(self.check_launch_processes)
        self.launch_timer.start(1500)

        # 设置样式
        self.setStyleSheet(generate_stylesheet(self.theme))

        # 初始化UI
        self.init_ui()

        # 应用窗口位置
        self.apply_window_position()

    def load_config(self) -> dict:
        """加载配置文件"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载配置失败: {e}")
        return {"folders": [], "theme": "dark_teal", "window_pos": None}

    def save_config(self):
        """保存配置文件"""
        try:
            config = {
                "folders": [(f["path"], f["is_common"]) for f in self.folders],
                "launch_items": [
                    {"name": i.get("name", ""), "path": i.get("path", ""), "target_path": i.get("target_path", "")}
                    for i in self.launch_items
                ],
                "extract_delete_archive": self.extract_delete_archive_check.isChecked()
                    if hasattr(self, "extract_delete_archive_check")
                    else self.config.get("extract_delete_archive", True),
                "merge_delete_source_folders": self.merge_delete_source_check.isChecked()
                    if hasattr(self, "merge_delete_source_check")
                    else self.config.get("merge_delete_source_folders", False),
                "folder_action_order": self.folder_action_order,
                "folder_remove_prefixes": self.folder_prefix_entry.toPlainText()
                    if hasattr(self, "folder_prefix_entry")
                    else self.config.get("folder_remove_prefixes", ""),
                "folder_sections_collapsed": {
                    "common": self.common_group.isChecked() is False
                        if hasattr(self, "common_group")
                        else self.config.get("folder_sections_collapsed", {}).get("common", False),
                    "uncommon": self.uncommon_group.isChecked() is False
                        if hasattr(self, "uncommon_group")
                        else self.config.get("folder_sections_collapsed", {}).get("uncommon", False),
                },
                "theme": self.theme_name,
                "window_pos": {
                    "x": self.x(),
                    "y": self.y(),
                    "width": self.width(),
                    "height": self.height()
                }
            }
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def apply_window_position(self):
        """应用窗口位置"""
        pos = self.config.get("window_pos")
        if pos:
            self.resize(pos.get("width", 600), pos.get("height", 400))
            self.move(pos.get("x", 100), pos.get("y", 100))
        else:
            self.resize(600, 400)
            # 居中显示
            screen = QDesktopWidget().screenGeometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 4
            self.move(x, y)

    def normalize_folder_action_order(self, raw_order=None) -> list:
        order = []
        for action_id in raw_order or []:
            if action_id in FOLDER_ACTIONS and action_id not in order:
                order.append(action_id)
        for action_id in DEFAULT_FOLDER_ACTION_ORDER:
            if action_id not in order:
                order.append(action_id)
        for action_id in FOLDER_ACTIONS:
            if action_id not in order:
                order.append(action_id)
        return order

    def parse_prefix_config(self, text: str) -> list:
        if not text:
            return []
        parts = re.split(r"[\n,;，；]+", text)
        return [p.strip() for p in parts if p.strip()]

    def folder_action_area_width(self) -> int:
        actions = self.folder_action_order[:FOLDER_ACTION_SLOT_COUNT]
        action_width = sum(FOLDER_ACTIONS.get(a, {}).get("width", 60) for a in actions)
        button_count = len(actions) + 1
        spacing_width = FOLDER_ACTION_BUTTON_SPACING * max(0, button_count - 1)
        return action_width + FOLDER_DELETE_BUTTON_WIDTH + spacing_width + FOLDER_ACTION_ROW_RIGHT_INSET

    def set_folder_action_order(self, order: list):
        self.folder_action_order = self.normalize_folder_action_order(order)
        self.save_config()
        if hasattr(self, "folder_action_order_widget"):
            self.folder_action_order_widget.set_order(self.folder_action_order)
        if hasattr(self, "folder_action_palette_layout"):
            self.rebuild_folder_action_palette()
        if hasattr(self, "common_list"):
            self.refresh_folder_list()

    def move_folder_action_to_slot(self, slot_index: int, action_id: str):
        order = [a for a in self.folder_action_order if a in FOLDER_ACTIONS]
        if action_id not in FOLDER_ACTIONS:
            return
        if action_id in order:
            order.remove(action_id)
        slot_index = max(0, min(slot_index, FOLDER_ACTION_SLOT_COUNT - 1, len(order)))
        order.insert(slot_index, action_id)
        self.set_folder_action_order(order)

    def on_folder_prefixes_changed(self):
        if hasattr(self, "folder_prefix_entry"):
            self.folder_remove_prefixes = self.parse_prefix_config(self.folder_prefix_entry.toPlainText())
            self.save_config()

    def init_ui(self):
        """初始化用户界面"""
        # 启用主窗口拖拽接受
        self.setAcceptDrops(True)

        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 标题栏（包含 Tab 按钮）
        title_bar = self.create_title_bar()
        main_layout.addWidget(title_bar)

        # 内容容器（不用 QTabWidget，手动切换）
        self.content_stack = QWidget()
        self.content_layout = QVBoxLayout(self.content_stack)
        self.content_layout.setContentsMargins(0, 0, 0, 0)

        # 添加标签页
        self.folder_tab = self.create_folder_tab()
        self.merge_tab = self.create_merge_tab()
        self.extract_tab = self.create_extract_tab()
        self.launch_tab = self.create_launch_tab()
        self.settings_tab = self.create_settings_tab()

        self.content_layout.addWidget(self.folder_tab)
        self.content_layout.addWidget(self.merge_tab)
        self.content_layout.addWidget(self.extract_tab)
        self.content_layout.addWidget(self.launch_tab)
        self.content_layout.addWidget(self.settings_tab)

        # 隐藏非活动 tab
        self.merge_tab.hide()
        self.extract_tab.hide()
        self.launch_tab.hide()
        self.settings_tab.hide()

        main_layout.addWidget(self.content_stack, 1)

        # 加载文件夹列表
        self.folders = []
        self.load_folders()

    def create_title_bar(self) -> QWidget:
        """创建标题栏（包含 Tab 按钮和 Pin）"""
        title_bar = QWidget()
        title_bar.setFixedHeight(36)
        title_bar.setObjectName("titleBar")
        title_bar.setStyleSheet(f"""
            #titleBar {{
                background-color: {self.theme['title_bg']};
                border-bottom: 1px solid {self.theme['border']};
            }}
        """)

        layout = QHBoxLayout(title_bar)
        layout.setContentsMargins(8, 0, 8, 0)
        layout.setSpacing(4)

        # Pin 按钮（最左边）
        self.pin_btn = QPushButton("📌")
        self.pin_btn.setFixedSize(32, 32)
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['tab_inactive']};
                color: {self.theme['gray']};
                border: none;
                font-size: 18px;
                border-radius: 4px;
            }}
            QPushButton:checked {{
                background-color: {self.theme['tab_active']};
                color: {self.theme['fg']};
            }}
            QPushButton:hover {{
                background-color: {self.theme['tab_hover']};
            }}
        """)
        self.pin_btn.clicked.connect(self.toggle_topmost)
        layout.addWidget(self.pin_btn)

        # Tab 按钮
        self.tab_buttons = []
        tabs = [
            ("📂 文件夹", 0),
            ("📁 合并", 1),
            ("📦 解压", 2),
            ("🚀 启动", 3),
            ("⚙️ 设置", 4),
        ]

        for label, idx in tabs:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(idx == 0)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {self.theme['tab_inactive']};
                    color: {self.theme['gray']};
                    border: none;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {self.theme['tab_active']};
                    color: {self.theme['fg']};
                }}
                QPushButton:hover {{
                    background-color: {self.theme['tab_hover']};
                }}
            """)
            btn.clicked.connect(lambda checked, i=idx: self.switch_tab(i))
            layout.addWidget(btn)
            self.tab_buttons.append(btn)

        layout.addStretch()

        return title_bar

    def toggle_topmost(self):
        """切换窗口置顶"""
        if self.pin_btn.isChecked():
            self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowStaysOnTopHint)
        self.show()

    def switch_tab(self, index: int):
        """切换标签页"""
        self.current_tab_index = index
        tabs = [self.folder_tab, self.merge_tab, self.extract_tab, self.launch_tab, self.settings_tab]
        for i, tab in enumerate(tabs):
            tab.setVisible(i == index)
        for i, btn in enumerate(self.tab_buttons):
            btn.setChecked(i == index)

    def create_folder_tab(self) -> QWidget:
        """创建快捷文件夹标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # 工具栏
        toolbar = QHBoxLayout()
        add_btn = QPushButton("📁 添加文件夹")
        add_btn.clicked.connect(self.add_folder)
        toolbar.addWidget(add_btn)
        paste_btn = QPushButton("📋 粘贴文件夹")
        paste_btn.clicked.connect(self.paste_folder_tab_folders)
        toolbar.addWidget(paste_btn)
        toolbar.addStretch()
        self.folder_action_palette_box = QWidget()
        self.folder_action_palette_box.setFixedWidth(self.folder_action_area_width())
        self.folder_action_palette_layout = QHBoxLayout()
        self.folder_action_palette_box.setLayout(self.folder_action_palette_layout)
        self.folder_action_palette_layout.setSpacing(4)
        self.folder_action_palette_layout.setContentsMargins(0, 0, 0, 0)
        toolbar.addWidget(self.folder_action_palette_box)
        layout.addLayout(toolbar)
        self.rebuild_folder_action_palette()

        # 分区：常用
        self.common_group = QGroupBox("⭐ 常用")
        self.common_group.setCheckable(True)
        self.common_group.setChecked(not self.config.get("folder_sections_collapsed", {}).get("common", False))
        self.common_group.toggled.connect(lambda checked: self.on_folder_section_toggled("common", checked))
        self.common_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.common_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                padding-bottom: 0px;
                color: {self.theme['gold']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        common_layout = QVBoxLayout(self.common_group)
        common_layout.setContentsMargins(4, 4, 4, 0)
        common_layout.setSpacing(2)
        self.common_list = DraggableListWidget()
        self.common_list.setDragDropMode(QListWidget.DragDrop)
        self.common_list.model().rowsMoved.connect(self.on_folder_reordered)
        self.common_list.set_drop_callback(lambda paths: self.add_folders_from_drop(paths, is_common=True))
        self.common_list.set_move_callback(lambda data, pos: self.move_folder_to_section(data, "common", pos))
        common_layout.addWidget(self.common_list)
        self.common_list.setVisible(self.common_group.isChecked())
        layout.addWidget(self.common_group)

        # 分区：非常用
        self.uncommon_group = QGroupBox("📦 非常用")
        self.uncommon_group.setCheckable(True)
        self.uncommon_group.setChecked(not self.config.get("folder_sections_collapsed", {}).get("uncommon", False))
        self.uncommon_group.toggled.connect(lambda checked: self.on_folder_section_toggled("uncommon", checked))
        self.uncommon_group.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        self.uncommon_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                padding-bottom: 0px;
                color: {self.theme['gray']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        uncommon_layout = QVBoxLayout(self.uncommon_group)
        uncommon_layout.setContentsMargins(4, 4, 4, 0)
        uncommon_layout.setSpacing(2)
        self.uncommon_list = DraggableListWidget()
        self.uncommon_list.setDragDropMode(QListWidget.DragDrop)
        self.uncommon_list.model().rowsMoved.connect(self.on_folder_reordered)
        self.uncommon_list.set_drop_callback(lambda paths: self.add_folders_from_drop(paths, is_common=False))
        self.uncommon_list.set_move_callback(lambda data, pos: self.move_folder_to_section(data, "uncommon", pos))
        uncommon_layout.addWidget(self.uncommon_list)
        self.uncommon_list.setVisible(self.uncommon_group.isChecked())
        layout.addWidget(self.uncommon_group)

        # 空状态提示
        self.empty_label = QLabel("✨ 点击「📁 添加文件夹」按钮添加快捷文件夹")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 14px;")
        layout.addWidget(self.empty_label)

        return tab

    def rebuild_folder_action_palette(self):
        if not hasattr(self, "folder_action_palette_layout"):
            return
        while self.folder_action_palette_layout.count():
            child = self.folder_action_palette_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        if hasattr(self, "folder_action_palette_box"):
            self.folder_action_palette_box.setFixedWidth(self.folder_action_area_width())
        visible_actions = set(self.folder_action_order[:FOLDER_ACTION_SLOT_COUNT])
        for action_id in [a for a in self.folder_action_order if a not in visible_actions]:
            btn = FolderActionButton(action_id, self.theme)
            self.folder_action_palette_layout.addWidget(btn)
        self.folder_action_palette_layout.addStretch()

    def create_launch_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        toolbar = QHBoxLayout()
        add_btn = QPushButton("➕ 添加快捷方式")
        add_btn.clicked.connect(self.add_launch_item)
        toolbar.addWidget(add_btn)
        paste_btn = QPushButton("📋 粘贴路径")
        paste_btn.clicked.connect(self.paste_launch_item)
        toolbar.addWidget(paste_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.launch_scroll = QScrollArea()
        self.launch_scroll.setWidgetResizable(True)
        self.launch_scroll.setFrameShape(QFrame.NoFrame)
        self.launch_grid_host = LaunchGridArea(self.theme)
        self.launch_grid_host.files_dropped.connect(self.add_launch_items_from_drop)
        self.launch_grid_host.item_dropped.connect(self.reorder_launch_item)
        self.launch_grid = QGridLayout(self.launch_grid_host)
        self.launch_grid.setContentsMargins(0, 0, 0, 0)
        self.launch_grid.setSpacing(0)
        self.launch_grid.setAlignment(Qt.AlignTop)
        for col in range(4):
            self.launch_grid.setColumnStretch(col, 1)
        self.launch_scroll.setWidget(self.launch_grid_host)
        layout.addWidget(self.launch_scroll, 1)

        self.launch_empty_label = QLabel("双击方格启动应用；运行后单击方格可确认关闭。")
        self.launch_empty_label.setAlignment(Qt.AlignCenter)
        self.launch_empty_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 13px;")
        layout.addWidget(self.launch_empty_label)
        self.refresh_launch_grid()
        return tab

    def create_merge_tab(self) -> QWidget:
        """创建文件夹合并标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题和按钮
        header = QHBoxLayout()
        title = QLabel("📁 文件夹合并")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {self.theme['fg']};")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("📁 添加文件夹")
        add_btn.clicked.connect(self.merge_add_folder)
        header.addWidget(add_btn)

        paste_btn = QPushButton("📋 粘贴文件夹")
        paste_btn.clicked.connect(self.merge_paste_folders)
        header.addWidget(paste_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.clicked.connect(self.merge_clear_list)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # 文件夹列表
        self.merge_list = DraggableListWidget()
        self.merge_list.setDragDropMode(QListWidget.InternalMove)
        self.merge_list.set_drop_callback(self.merge_add_folders_from_drop)
        layout.addWidget(self.merge_list, 1)

        # 输出目录
        output_layout = QHBoxLayout()
        output_label = QLabel("输出到:")
        output_label.setStyleSheet(f"color: {self.theme['fg']};")
        output_layout.addWidget(output_label)

        self.merge_output_entry = QLineEdit()
        self.merge_output_entry.setPlaceholderText("当前目录")
        output_layout.addWidget(self.merge_output_entry, 1)

        select_btn = QPushButton("📂 选择目录")
        select_btn.setFixedSize(100, 30)
        select_btn.clicked.connect(self.merge_select_output)
        output_layout.addWidget(select_btn)

        layout.addLayout(output_layout)

        # 选项行：当前文件夹 + 开始合并按钮
        merge_option_layout = QHBoxLayout()

        merge_check_layout = QHBoxLayout()
        merge_check_layout.setSpacing(4)

        self.merge_current_folder_check = QCheckBox("当前文件夹")
        self.merge_current_folder_check.setChecked(True)
        self.merge_current_folder_check.setStyleSheet(f"color: {self.theme['fg']};")
        self.merge_current_folder_check.stateChanged.connect(lambda _: self.update_merge_output_suggestion())
        merge_check_layout.addWidget(self.merge_current_folder_check)

        merge_hint_label = QLabel("（建立一个合并文件的文件夹）")
        merge_hint_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 11px;")
        merge_check_layout.addWidget(merge_hint_label)

        self.merge_delete_source_check = QCheckBox("删除旧文件夹")
        self.merge_delete_source_check.setChecked(self.config.get("merge_delete_source_folders", False))
        self.merge_delete_source_check.setStyleSheet(f"color: {self.theme['fg']};")
        self.merge_delete_source_check.stateChanged.connect(lambda _: self.save_config())
        merge_check_layout.addWidget(self.merge_delete_source_check)

        merge_option_layout.addLayout(merge_check_layout)
        merge_option_layout.addStretch()

        merge_btn = QPushButton("▶ 开始合并")
        merge_btn.setFixedSize(100, 30)
        merge_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_hover']};
            }}
        """)
        merge_btn.clicked.connect(self.merge_start)
        merge_option_layout.addWidget(merge_btn)

        layout.addLayout(merge_option_layout)

        # 进度条
        self.merge_progress = QProgressBar()
        self.merge_progress.setVisible(False)
        layout.addWidget(self.merge_progress)

        return tab

    def create_extract_tab(self) -> QWidget:
        """创建文件解压标签页"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)

        # 标题和按钮
        header = QHBoxLayout()
        title = QLabel("📦 文件解压")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet(f"color: {self.theme['fg']};")
        header.addWidget(title)
        header.addStretch()

        add_btn = QPushButton("📁 添加文件夹")
        add_btn.clicked.connect(self.extract_add_files)
        header.addWidget(add_btn)

        paste_btn = QPushButton("📋 粘贴文件夹")
        paste_btn.clicked.connect(self.extract_paste_files)
        header.addWidget(paste_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.clicked.connect(self.extract_clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # 文件列表
        self.extract_list = QListWidget()
        layout.addWidget(self.extract_list, 1)

        # 底部：输出目录
        bottom_layout = QHBoxLayout()

        output_label = QLabel("解压到:")
        output_label.setStyleSheet(f"color: {self.theme['fg']};")
        bottom_layout.addWidget(output_label)

        self.extract_output_entry = QLineEdit()
        self.extract_output_entry.setPlaceholderText("当前目录")
        bottom_layout.addWidget(self.extract_output_entry, 1)

        select_btn = QPushButton("📂 选择目录")
        select_btn.setFixedWidth(100)
        select_btn.clicked.connect(self.extract_select_output)
        bottom_layout.addWidget(select_btn)

        layout.addLayout(bottom_layout)

        # 选项行：独立文件夹 + 开始解压按钮（同一行）
        option_layout = QHBoxLayout()

        self.extract_separate_check = QCheckBox("独立文件夹")
        self.extract_separate_check.setChecked(False)
        self.extract_separate_check.setStyleSheet(f"color: {self.theme['fg']};")
        option_layout.addWidget(self.extract_separate_check)

        hint_label = QLabel("（每个压缩包解压到对应名称文件夹）")
        hint_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 11px;")
        option_layout.addWidget(hint_label)

        self.extract_delete_archive_check = QCheckBox("删除压缩包")
        self.extract_delete_archive_check.setChecked(self.config.get("extract_delete_archive", True))
        self.extract_delete_archive_check.setStyleSheet(f"color: {self.theme['fg']};")
        self.extract_delete_archive_check.stateChanged.connect(lambda _: self.save_config())
        option_layout.addWidget(self.extract_delete_archive_check)

        option_layout.addStretch()

        extract_btn = QPushButton("▶ 开始解压")
        extract_btn.setFixedSize(100, 30)
        extract_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_hover']};
            }}
        """)
        extract_btn.clicked.connect(self.extract_start)
        option_layout.addWidget(extract_btn)

        layout.addLayout(option_layout)

        # 进度条
        self.extract_progress = QProgressBar()
        self.extract_progress.setVisible(False)
        layout.addWidget(self.extract_progress)

        return tab

    def create_settings_tab(self) -> QWidget:
        """创建设置标签页"""
        tab = QWidget()
        outer_layout = QVBoxLayout(tab)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)

        # 主题设置
        theme_group = QGroupBox("🎨 主题设置")
        theme_layout = QHBoxLayout(theme_group)

        theme_label = QLabel("选择主题:")
        theme_label.setStyleSheet(f"color: {self.theme['fg']};")
        theme_layout.addWidget(theme_label)

        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(30)
        for key, theme in THEMES.items():
            self.theme_combo.addItem(theme["name"], key)
        # 设置当前主题
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == self.theme_name:
                self.theme_combo.setCurrentIndex(i)
                break
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        theme_layout.addWidget(self.theme_combo, 1)

        layout.addWidget(theme_group)

        system_group = QGroupBox("系统")
        system_layout = QVBoxLayout(system_group)
        self.startup_check = QCheckBox("开机自动启动")
        self.startup_check.setChecked(self.is_startup_enabled())
        self.startup_check.setStyleSheet(f"color: {self.theme['fg']};")
        self.startup_check.stateChanged.connect(self.on_startup_changed)
        system_layout.addWidget(self.startup_check)
        startup_hint = QLabel("优先使用 pythonw 后台启动 Quick Folder")
        startup_hint.setStyleSheet(f"color: {self.theme['gray']}; font-size: 11px;")
        system_layout.addWidget(startup_hint)
        layout.addWidget(system_group)

        folder_actions_group = QGroupBox("文件夹功能项")
        folder_actions_layout = QVBoxLayout(folder_actions_group)
        self.folder_action_order_widget = FolderActionOrderWidget(self.theme)
        self.folder_action_order_widget.set_order(self.folder_action_order)
        self.folder_action_order_widget.order_changed.connect(self.set_folder_action_order)
        folder_actions_layout.addWidget(self.folder_action_order_widget)

        prefix_label = QLabel("删前缀配置:")
        prefix_label.setStyleSheet(f"color: {self.theme['fg']};")
        folder_actions_layout.addWidget(prefix_label)
        self.folder_prefix_entry = QPlainTextEdit()
        self.folder_prefix_entry.setFixedHeight(70)
        self.folder_prefix_entry.setPlaceholderText("每行一个前缀，也可用逗号或分号分隔")
        self.folder_prefix_entry.setPlainText(self.config.get("folder_remove_prefixes", ""))
        self.folder_prefix_entry.textChanged.connect(self.on_folder_prefixes_changed)
        folder_actions_layout.addWidget(self.folder_prefix_entry)
        layout.addWidget(folder_actions_group)
        layout.addStretch()

        # 关于
        about_group = QGroupBox("ℹ️ 关于")
        about_layout = QVBoxLayout(about_group)
        about_label = QLabel("Quick Folder v2.0\nPyQt5 版本\n\n一个轻量级的文件夹快捷入口面板")
        about_label.setStyleSheet(f"color: {self.theme['fg']};")
        about_layout.addWidget(about_label)
        layout.addWidget(about_group)

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)
        return tab

    def startup_registry_value(self) -> str:
        script = Path(__file__).resolve()
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if sys.platform == "win32" and pythonw.exists():
            return f'"{pythonw}" "{script}"'
        return f'"{Path(__file__).parent / "run.bat"}"'

    def is_startup_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run") as key:
                value, _ = winreg.QueryValueEx(key, "QuickFolder")
            return value == self.startup_registry_value()
        except Exception:
            return False

    def set_startup_enabled(self, enabled: bool):
        if sys.platform != "win32":
            return
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, "QuickFolder", 0, winreg.REG_SZ, self.startup_registry_value())
                else:
                    try:
                        winreg.DeleteValue(key, "QuickFolder")
                    except FileNotFoundError:
                        pass
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"开机启动设置失败:\n{e}")

    def on_startup_changed(self, state):
        self.set_startup_enabled(state == Qt.Checked)

    def on_theme_changed(self, index):
        """主题下拉框变化"""
        theme_key = self.theme_combo.itemData(index)
        if theme_key and theme_key != self.theme_name:
            self.change_theme(theme_key)

    def change_theme(self, theme_name: str):
        """切换主题"""
        self.theme_name = theme_name
        self.theme = THEMES[theme_name]
        self.setStyleSheet(generate_stylesheet(self.theme))
        self.save_config()
        # 重建 UI
        self.rebuild_ui()

    def rebuild_ui(self):
        """重建 UI"""
        # 保存当前文件夹列表
        folders_backup = self.folders.copy()

        # 清除中央部件
        central_widget = self.centralWidget()
        central_widget.deleteLater()

        # 重建
        self.init_ui()

        # 恢复文件夹列表
        self.folders = folders_backup
        self.refresh_folder_list()
        if hasattr(self, "launch_grid"):
            self.refresh_launch_grid()

    def load_launch_items(self) -> list:
        items = []
        for raw in self.config.get("launch_items", []):
            if isinstance(raw, dict) and raw.get("path"):
                items.append({
                    "name": raw.get("name") or os.path.basename(raw.get("path", "")),
                    "path": raw.get("path", ""),
                    "target_path": raw.get("target_path", "")
                })
        return items

    def resolve_lnk_target_from_file(self, path: str) -> str:
        try:
            data = Path(path).read_bytes()
        except Exception:
            return ""
        candidates = []
        for enc in ("utf-16le", "mbcs", "utf-8"):
            try:
                text = data.decode(enc, errors="ignore")
            except Exception:
                continue
            candidates.extend(re.findall(r"[A-Za-z]:\\[^<>:\"|?*\r\n\x00]+?\.exe", text, re.IGNORECASE))
        for candidate in candidates:
            if os.path.exists(candidate):
                return os.path.normcase(os.path.normpath(candidate))
        return ""

    def resolve_launch_target(self, path: str) -> str:
        if not path:
            return ""
        suffix = Path(path).suffix.lower()
        if suffix == ".lnk":
            target = self.resolve_lnk_target_from_file(path)
            if target:
                return target
        return os.path.normcase(os.path.normpath(path))

    def running_executable_paths(self) -> set:
        if sys.platform != "win32":
            return set()
        paths, pids = set(), {}
        try:
            import ctypes.wintypes as wintypes
            psapi = ctypes.WinDLL("Psapi.dll")
            kernel32 = ctypes.WinDLL("Kernel32.dll")
            arr = (wintypes.DWORD * 4096)()
            needed = wintypes.DWORD()
            if not psapi.EnumProcesses(arr, ctypes.sizeof(arr), ctypes.byref(needed)):
                return paths
            count = needed.value // ctypes.sizeof(wintypes.DWORD)
            for pid in arr[:count]:
                handle = kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
                if not handle:
                    continue
                try:
                    size = wintypes.DWORD(32768)
                    buf = ctypes.create_unicode_buffer(size.value)
                    if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                        proc_path = os.path.normcase(os.path.normpath(buf.value))
                        paths.add(proc_path)
                        pids.setdefault(proc_path, []).append(int(pid))
                finally:
                    kernel32.CloseHandle(handle)
        except Exception:
            pass
        self.running_launch_pids = pids
        return paths

    def refresh_running_launch_paths(self):
        self.running_launch_paths = self.running_executable_paths()

    def is_launch_item_running(self, item: dict) -> bool:
        path = item.get("path", "")
        if path in self.launch_processes:
            return True
        target = item.get("target_path") or ""
        if target and Path(target).suffix.lower() == ".lnk":
            target = ""
        if not target:
            target = self.resolve_launch_target(path)
        if target and item.get("target_path") != target:
            item["target_path"] = target
        if target and target in getattr(self, "running_launch_paths", set()):
            return True
        exe = os.path.basename(target or path).lower()
        return any(os.path.basename(p).lower() == exe for p in getattr(self, "running_launch_paths", set()))

    def refresh_launch_grid(self):
        if not hasattr(self, "launch_grid"):
            return
        self.refresh_running_launch_paths()
        while self.launch_grid.count():
            child = self.launch_grid.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.launch_grid_host.running_cells = set()
        self.launch_tiles = {}
        cols = 4
        visible_cells = max(16, ((len(self.launch_items) + cols - 1) // cols) * cols)
        visible_rows = max(1, (visible_cells + cols - 1) // cols)
        self.launch_grid_host.setMinimumHeight(visible_rows * 102)
        self.launch_grid_host.setMaximumHeight(16777215)
        for index, item in enumerate(self.launch_items):
            item["_grid_index"] = index
            cell = LaunchCellWidget(self.theme, index=index)
            tile = LaunchItemWidget(item, self.theme)
            tile.launch_requested.connect(self.launch_item)
            tile.close_requested.connect(self.confirm_close_launch_item)
            tile.delete_requested.connect(self.remove_launch_item)
            self.launch_tiles[item.get("path", "")] = tile
            cell.layout().insertWidget(0, tile)
            tile.update_state(self.is_launch_item_running(item))
            self.launch_grid.addWidget(cell, index // cols, index % cols)
        for index in range(len(self.launch_items), visible_cells):
            self.launch_grid.addWidget(LaunchCellWidget(self.theme, index=index), index // cols, index % cols)
        self.launch_empty_label.setVisible(len(self.launch_items) == 0)

    def reorder_launch_item(self, from_index: int, to_index: int):
        if from_index < 0 or from_index >= len(self.launch_items):
            return
        if to_index < 0:
            return
        if to_index >= len(self.launch_items):
            item = self.launch_items.pop(from_index)
            self.launch_items.append(item)
        elif from_index != to_index:
            self.launch_items[from_index], self.launch_items[to_index] = self.launch_items[to_index], self.launch_items[from_index]
        else:
            return
        self.refresh_launch_grid()
        self.save_config()

    def add_launch_item(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择应用或脚本", "", "可启动文件 (*.exe *.bat *.cmd *.lnk *.ps1);;所有文件 (*)")
        if path:
            self.add_launch_item_path(path)

    def paste_launch_item(self):
        mime = QApplication.clipboard().mimeData()
        if mime.hasUrls():
            self.add_launch_items_from_drop([u.toLocalFile() for u in mime.urls()])

    def add_launch_items_from_drop(self, paths: list):
        for path in paths:
            if path and os.path.isfile(path):
                self.add_launch_item_path(path, ask_name=False, quiet=True)

    def add_launch_item_path(self, path: str, ask_name: bool = True, quiet: bool = False):
        path = os.path.normpath(path)
        if any(i.get("path") == path for i in self.launch_items):
            return
        name = os.path.splitext(os.path.basename(path))[0] or path
        if ask_name:
            entered, ok = QInputDialog.getText(self, "快捷方式名称", "显示名称:", text=name)
            if not ok:
                return
            name = entered.strip() or name
        self.launch_items.append({"name": name, "path": path, "target_path": self.resolve_launch_target(path)})
        self.refresh_launch_grid()
        self.save_config()

    def remove_launch_item(self, item: dict):
        path = item.get("path", "")
        self.launch_items = [i for i in self.launch_items if i.get("path") != path]
        self.launch_processes.pop(path, None)
        self.refresh_launch_grid()
        self.save_config()

    def launch_item(self, item: dict):
        path = item.get("path", "")
        if not path or not os.path.exists(path):
            return
        suffix = Path(path).suffix.lower()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        if sys.platform == "win32" and suffix in (".bat", ".cmd"):
            proc = subprocess.Popen(["cmd.exe", "/c", path], cwd=os.path.dirname(path) or None, creationflags=flags)
        elif sys.platform == "win32" and suffix == ".ps1":
            proc = subprocess.Popen(["powershell.exe", "-ExecutionPolicy", "Bypass", "-File", path], cwd=os.path.dirname(path) or None, creationflags=flags)
        else:
            proc = subprocess.Popen([path], cwd=os.path.dirname(path) or None, shell=(suffix == ".lnk"))
        self.launch_processes[path] = proc
        self.check_launch_processes()

    def confirm_close_launch_item(self, item: dict):
        path = item.get("path", "")
        reply = QMessageBox.question(self, "确认关闭", f"确定关闭这个应用吗？\n{item.get('name', path)}", QMessageBox.Yes | QMessageBox.No)
        if reply != QMessageBox.Yes:
            return
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        proc = self.launch_processes.get(path)
        pids = []
        if proc:
            pids.append(proc.pid)
        else:
            target = item.get("target_path") or self.resolve_launch_target(path)
            target = os.path.normcase(os.path.normpath(target)) if target else ""
            pids = list(self.running_launch_pids.get(target, []))
        for pid in pids:
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=flags)
        self.launch_processes.pop(path, None)
        self.check_launch_processes()

    def check_launch_processes(self):
        if not hasattr(self, "launch_tiles"):
            return
        self.refresh_running_launch_paths()
        for path, proc in list(self.launch_processes.items()):
            if proc.poll() is not None:
                self.launch_processes.pop(path, None)
        for item in self.launch_items:
            tile = self.launch_tiles.get(item.get("path", ""))
            if tile:
                tile.update_state(self.is_launch_item_running(item))

    def load_folders(self):
        """从配置加载文件夹列表"""
        folders_data = self.config.get("folders", [])
        self.folders = []
        for path, is_common in folders_data:
            if os.path.exists(path):
                display_name = os.path.basename(path) or path
                self.folders.append({
                    "path": path,
                    "display_name": display_name,
                    "is_common": is_common
                })
        self.refresh_folder_list()

    def refresh_folder_list(self):
        """刷新文件夹列表"""
        self.common_list.clear()
        self.uncommon_list.clear()

        for folder in self.folders:
            widget = FolderItemWidget(
                folder["path"],
                folder["display_name"],
                folder["is_common"],
                self.theme,
                self.folder_action_order,
                self.folder_remove_prefixes
            )
            # 连接信号
            widget.delete_requested.connect(self.remove_folder)
            widget.section_toggled.connect(self.toggle_section)
            widget.rename_requested.connect(self.rename_folder)
            widget.action_slot_replaced.connect(self.move_folder_action_to_slot)

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint() + QSize(0, 10))
            item.setData(Qt.UserRole, folder)

            if folder["is_common"]:
                self.common_list.addItem(item)
                self.common_list.setItemWidget(item, widget)
                widget.clicked.connect(lambda checked=False, i=item, lst=self.common_list: lst.setCurrentItem(i))
            else:
                self.uncommon_list.addItem(item)
                self.uncommon_list.setItemWidget(item, widget)
                widget.clicked.connect(lambda checked=False, i=item, lst=self.uncommon_list: lst.setCurrentItem(i))

        self.empty_label.setVisible(len(self.folders) == 0)

        # 强制更新列表widget的size hint
        self.common_list.updateGeometry()
        self.uncommon_list.updateGeometry()
        self.common_group.updateGeometry()
        self.uncommon_group.updateGeometry()

        # 自动调整窗口高度
        self.adjust_window_height()

    def on_folder_section_toggled(self, section: str, checked: bool):
        if section == "common":
            self.common_list.setVisible(checked)
        else:
            self.uncommon_list.setVisible(checked)
        self.adjust_window_height()
        self.save_config()

    def adjust_window_height(self):
        """根据文件夹数量自动调整窗口高度"""
        if getattr(self, "current_tab_index", 0) != 0:
            return
        # 分别计算常用和非常用文件夹数量
        common_count = sum(1 for f in self.folders if f["is_common"])
        uncommon_count = sum(1 for f in self.folders if not f["is_common"])

        # 基础高度：标题栏(36) + 工具栏(36) + 间距(16)
        base_height = 88
        # 每个QGroupBox开销：margin-top(12) + padding-top(12) + border(2) = 26
        group_overhead = 26
        # 每个文件夹项高度55
        item_height = 55
        # 最小和最大高度
        min_height = 200
        max_height = 700

        total_items = 0
        if not hasattr(self, "common_group") or self.common_group.isChecked():
            total_items += common_count
        if not hasattr(self, "uncommon_group") or self.uncommon_group.isChecked():
            total_items += uncommon_count
        if total_items == 0:
            content_height = base_height + group_overhead * 2 + 45
        else:
            content_height = base_height + group_overhead * 2 + total_items * item_height
        new_height = max(min_height, min(max_height, content_height))

        # 保持窗口位置不变，只调整高度
        x = self.x()
        y = self.y()
        self.setGeometry(x, y, self.width(), new_height)

    def add_folder(self):
        """添加文件夹"""
        path = QFileDialog.getExistingDirectory(self, "选择文件夹")
        if path:
            display_name = os.path.basename(path) or path
            # 检查是否已存在
            if not any(f["path"] == path for f in self.folders):
                self.folders.append({
                    "path": path,
                    "display_name": display_name,
                    "is_common": True
                })
                self.refresh_folder_list()
                self.save_config()

    def add_folders_from_drop(self, paths: list, is_common: bool = True):
        """从拖拽添加文件夹（添加到顶部）"""
        added = 0
        for path in paths:
            if not os.path.isdir(path):
                continue
            display_name = os.path.basename(path) or path
            # 检查是否已存在
            if not any(f["path"] == path for f in self.folders):
                self.folders.insert(0, {
                    "path": path,
                    "display_name": display_name,
                    "is_common": is_common
                })
                added += 1
        if added > 0:
            self.refresh_folder_list()
            self.save_config()

    def clipboard_local_paths(self) -> list:
        mime = QApplication.clipboard().mimeData()
        paths = []
        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    if path:
                        paths.append(path)
        if mime.hasText():
            paths.extend(self.parse_clipboard_paths(mime.text()))
        normalized = []
        seen = set()
        for path in paths:
            norm = os.path.normpath(os.path.expandvars(os.path.expanduser(path)))
            key = os.path.normcase(norm)
            if key not in seen:
                seen.add(key)
                normalized.append(norm)
        return normalized

    def parse_clipboard_paths(self, text: str) -> list:
        paths = []
        for raw in text.splitlines():
            path = raw.strip().strip('"').strip("'")
            if not path:
                continue
            path = os.path.expandvars(os.path.expanduser(path))
            if os.path.exists(path):
                paths.append(os.path.normpath(path))
        return paths

    def paste_folder_tab_folders(self):
        folders = [p for p in self.clipboard_local_paths() if os.path.isdir(p)]
        before = len(self.folders)
        self.add_folders_from_drop(folders, is_common=True)
        if len(self.folders) == before:
            if folders:
                QMessageBox.information(self, "提示", "剪贴板中没有新的文件夹")
            else:
                QMessageBox.information(self, "提示", "剪贴板中没有文件夹数据")

    def move_folder_to_section(self, folder_data: dict, target_section: str, position: int):
        """将文件夹移动到指定分区"""
        path = folder_data["path"]
        is_common = (target_section == "common")

        # 从当前位置移除
        self.folders = [f for f in self.folders if f["path"] != path]

        # 更新分区
        folder_data["is_common"] = is_common

        # 计算插入位置（在目标分区中的位置）
        if is_common:
            common_folders = [f for f in self.folders if f["is_common"]]
            if position >= len(common_folders):
                # 插入到常用分区末尾
                insert_idx = len(self.folders)
                for i, f in enumerate(self.folders):
                    if not f["is_common"]:
                        insert_idx = i
                        break
            else:
                # 插入到常用分区指定位置
                insert_idx = 0
                count = 0
                for i, f in enumerate(self.folders):
                    if f["is_common"]:
                        if count == position:
                            insert_idx = i
                            break
                        count += 1
        else:
            uncommon_folders = [f for f in self.folders if not f["is_common"]]
            if position >= len(uncommon_folders):
                insert_idx = len(self.folders)
            else:
                insert_idx = 0
                count = 0
                for i, f in enumerate(self.folders):
                    if not f["is_common"]:
                        if count == position:
                            insert_idx = i
                            break
                        count += 1

        self.folders.insert(insert_idx, folder_data)
        self.refresh_folder_list()
        self.save_config()

    def toggle_section(self, path: str, is_current_common: bool):
        """切换分区（常用/非常用）"""
        for folder in self.folders:
            if folder["path"] == path:
                folder["is_common"] = not is_current_common
                break
        self.refresh_folder_list()
        self.save_config()

    def remove_folder(self, path: str):
        """删除文件夹"""
        reply = QMessageBox.question(self, "确认", f"确定要删除这个文件夹吗？\n{path}",
                                     QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.folders = [f for f in self.folders if f["path"] != path]
            self.refresh_folder_list()
            self.save_config()

    def rename_folder(self, path: str, new_name: str):
        """重命名文件夹（实际文件夹和显示名称）"""
        if not os.path.exists(path):
            QMessageBox.warning(self, "提示", f"文件夹不存在:\n{path}")
            return

        # 构建新的文件夹路径
        parent_dir = os.path.dirname(path)
        new_path = os.path.join(parent_dir, new_name)

        # 检查新路径是否已存在
        if os.path.exists(new_path) and new_path != path:
            QMessageBox.warning(self, "提示", f"目标路径已存在:\n{new_path}")
            return

        try:
            # 重命名实际文件夹
            os.rename(path, new_path)

            # 更新配置中的路径
            for folder in self.folders:
                if folder["path"] == path:
                    folder["path"] = new_path
                    folder["display_name"] = new_name
                    break

            self.refresh_folder_list()
            self.save_config()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"重命名失败:\n{e}")

    def on_folder_reordered(self):
        """文件夹重新排序"""
        # 重新收集文件夹列表
        new_folders = []
        for i in range(self.common_list.count()):
            item = self.common_list.item(i)
            folder_data = item.data(Qt.UserRole)
            if folder_data:
                folder_data["is_common"] = True
                new_folders.append(folder_data)

        for i in range(self.uncommon_list.count()):
            item = self.uncommon_list.item(i)
            folder_data = item.data(Qt.UserRole)
            if folder_data:
                folder_data["is_common"] = False
                new_folders.append(folder_data)

        self.folders = new_folders
        self.save_config()

    def dragEnterEvent(self, event):
        """拖拽进入窗口"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """拖拽移动"""
        event.acceptProposedAction()

    def dropEvent(self, event):
        """拖拽放下"""
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path:
                files.append(path)

        if not files:
            return

        if getattr(self, "current_tab_index", 0) == 3:
            self.add_launch_items_from_drop([f for f in files if os.path.isfile(f)])
            event.acceptProposedAction()
            return

        folders = [f for f in files if os.path.isdir(f)]
        archive_exts = ('.zip', '.rar', '.7z', '.tar', '.tar.gz', '.tgz', '.tar.bz2')
        archive_files = [f for f in files if os.path.isfile(f) and f.lower().endswith(archive_exts)]

        if folders:
            # 有文件夹 → 切换到合并 tab，添加文件夹
            self.switch_tab(1)
            for f in folders:
                self.merge_add_folder_path(f)
        elif archive_files:
            # 有压缩文件 → 切换到解压 tab
            self.switch_tab(2)
            for f in archive_files:
                self.extract_add_file_path(f)
        else:
            # 普通文件 → 切换到解压 tab
            self.switch_tab(2)
            for f in files:
                if os.path.isfile(f):
                    self.extract_add_file_path(f)

        event.acceptProposedAction()

    def merge_add_folder_path(self, path: str):
        """添加文件夹到合并列表（由外部拖拽调用）"""
        display_name = os.path.basename(path) or path
        if not any(self.merge_list.item(i).data(Qt.UserRole) == path
                   for i in range(self.merge_list.count())):
            item = QListWidgetItem(f"📁 {display_name}  ({path})")
            item.setData(Qt.UserRole, path)
            self.merge_list.addItem(item)
            self.update_merge_output_suggestion()

    def merge_add_folders_from_drop(self, paths: list):
        for path in paths:
            if os.path.isdir(path):
                self.merge_add_folder_path(path)

    def extract_add_file_path(self, path: str):
        """添加文件到解压列表（由外部拖拽调用）"""
        if os.path.isfile(path) and self.is_archive_file(path):
            display_name = os.path.basename(path)
            item = QListWidgetItem(f"📦 {display_name}  ({path})")
            item.setData(Qt.UserRole, path)
            self.extract_list.addItem(item)

    def is_archive_file(self, path: str) -> bool:
        return os.path.isfile(path) and os.path.basename(path).lower().endswith(ARCHIVE_EXTENSIONS)

    def archive_files_from_paths(self, paths: list) -> list:
        files = []
        seen = set()
        for path in paths:
            candidates = []
            if self.is_archive_file(path):
                candidates = [path]
            elif os.path.isdir(path):
                try:
                    candidates = [
                        os.path.join(path, name)
                        for name in os.listdir(path)
                        if self.is_archive_file(os.path.join(path, name))
                    ]
                except Exception as e:
                    print(f"读取压缩包文件夹失败: {path} -> {e}")
            for candidate in candidates:
                key = os.path.normcase(os.path.normpath(candidate))
                if key not in seen:
                    seen.add(key)
                    files.append(os.path.normpath(candidate))
        return files

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.save_config()
        event.accept()

    # ============================================================
    # 文件夹合并功能
    # ============================================================

    def merge_add_folder(self):
        """添加文件夹到合并列表"""
        path = QFileDialog.getExistingDirectory(self, "选择要合并的文件夹")
        if path:
            display_name = os.path.basename(path) or path
            # 检查是否已存在
            if not any(self.merge_list.item(i).data(Qt.UserRole, None) == path
                      for i in range(self.merge_list.count())):
                item = QListWidgetItem(f"📁 {display_name}  ({path})")
                item.setData(Qt.UserRole, path)
                self.merge_list.addItem(item)

                # 更新输出目录建议
                self.update_merge_output_suggestion()

    def merge_paste_folders(self):
        """从剪贴板粘贴文件夹"""
        paths = [p for p in self.clipboard_local_paths() if os.path.isdir(p)]

        before = self.merge_list.count()
        for path in paths:
            self.merge_add_folder_path(path)
        added = self.merge_list.count() - before
        if added == 0:
            if paths:
                QMessageBox.information(self, "提示", "剪贴板中没有新的文件夹")
            else:
                QMessageBox.information(self, "提示", "剪贴板中没有文件夹数据")

    def parse_clipboard_folder_paths(self, text: str) -> list:
        return [p for p in self.parse_clipboard_paths(text) if os.path.isdir(p)]

    def merge_clear_list(self):
        """清空合并列表"""
        self.merge_list.clear()
        self.merge_output_entry.clear()

    def update_merge_output_suggestion(self):
        """更新输出目录建议"""
        if self.merge_list.count() == 0:
            self.merge_output_entry.clear()
            return

        output = self.suggest_merge_output_dir()
        if output:
            self.merge_output_entry.setText(output)
        else:
            self.merge_output_entry.clear()

    def suggest_merge_output_dir(self) -> str:
        """根据当前合并列表和选项生成默认输出目录"""
        dirs = set()
        for i in range(self.merge_list.count()):
            path = self.merge_list.item(i).data(Qt.UserRole)
            if path:
                dirs.add(os.path.dirname(path))

        if len(dirs) == 1:
            parent_dir = dirs.pop()
        elif self.merge_list.count() > 0:
            first_path = self.merge_list.item(0).data(Qt.UserRole)
            parent_dir = os.path.dirname(first_path) if first_path else os.getcwd()
        else:
            parent_dir = os.getcwd()
        if self.merge_current_folder_check.isChecked():
            return os.path.join(parent_dir, "合并文件")
        return parent_dir

    def merge_select_output(self):
        """选择输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if path:
            self.merge_output_entry.setText(path)

    def merge_start(self):
        """开始合并"""
        if self.merge_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加要合并的文件夹")
            return

        output = self.merge_output_entry.text().strip()
        if not output:
            # 没有指定输出目录
            output = self.suggest_merge_output_dir()
        elif self.merge_current_folder_check.isChecked():
            # 兼容旧状态：如果输出框里还是源文件夹父目录，勾选时改为父目录下的"合并文件"。
            first_path = self.merge_list.item(0).data(Qt.UserRole)
            parent_dir = os.path.dirname(first_path) if first_path else os.getcwd()
            if os.path.normcase(os.path.normpath(output)) == os.path.normcase(os.path.normpath(parent_dir)):
                output = os.path.join(parent_dir, "合并文件")

        # 确保输出目录存在
        os.makedirs(output, exist_ok=True)

        # 收集所有文件夹路径
        folders = []
        for i in range(self.merge_list.count()):
            path = self.merge_list.item(i).data(Qt.UserRole)
            if path and os.path.exists(path):
                display_name = os.path.basename(path) or path
                folders.append((path, display_name))

        if not folders:
            QMessageBox.warning(self, "提示", "没有有效的文件夹可合并")
            return
        self._last_merge_source_folders = [path for path, _ in folders]
        self._last_merge_output = os.path.normcase(os.path.normpath(output))

        # 显示进度条
        self.merge_progress.setVisible(True)
        self.merge_progress.setValue(0)

        # 启动合并线程
        self.merge_worker = MergeWorker(folders, output)
        self.merge_worker.progress.connect(self.on_merge_progress)
        self.merge_worker.finished.connect(self.on_merge_finished)
        self.merge_worker.error.connect(self.on_merge_error)
        self.merge_worker.start()

    def on_merge_progress(self, current: int, total: int, filename: str):
        """合并进度更新"""
        self.merge_progress.setMaximum(total)
        self.merge_progress.setValue(current)

    def on_merge_finished(self, copied: int, renamed: int):
        """合并完成"""
        self.merge_progress.setVisible(False)
        deleted_folders = 0
        delete_errors = 0
        if copied > 0 and getattr(self, "merge_delete_source_check", None) and self.merge_delete_source_check.isChecked():
            for folder in getattr(self, "_last_merge_source_folders", []):
                try:
                    normalized = os.path.normcase(os.path.normpath(folder))
                    if normalized != getattr(self, "_last_merge_output", "") and os.path.isdir(folder):
                        shutil.rmtree(folder)
                        deleted_folders += 1
                except Exception as e:
                    delete_errors += 1
                    print(f"删除旧文件夹失败: {folder} -> {e}")
        msg = f"已合并 {copied} 个文件"
        if renamed > 0:
            msg += f"\n{renamed} 个文件被重命名"
        if deleted_folders > 0:
            msg += f"\n已删除 {deleted_folders} 个旧文件夹"
        if delete_errors > 0:
            msg += f"\n{delete_errors} 个旧文件夹删除失败"
        QMessageBox.information(self, "合并完成", msg)

    def on_merge_error(self, error: str):
        """合并错误"""
        QMessageBox.warning(self, "错误", error)

    # ============================================================
    # 文件解压功能
    # ============================================================

    def extract_add_files(self):
        """添加文件到解压列表"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择要解压的文件", "",
            "压缩文件 (*.zip *.tar.gz *.tgz *.tar.bz2 *.tar *.rar *.7z);;所有文件 (*)"
        )
        for file in files:
            display_name = os.path.basename(file)
            item = QListWidgetItem(f"📦 {display_name}  ({file})")
            item.setData(Qt.UserRole, file)
            self.extract_list.addItem(item)

    def extract_paste_files(self):
        """从剪贴板粘贴文件"""
        files = self.archive_files_from_paths(self.clipboard_local_paths())
        before = self.extract_list.count()
        existing = {
            os.path.normcase(os.path.normpath(self.extract_list.item(i).data(Qt.UserRole)))
            for i in range(self.extract_list.count())
            if self.extract_list.item(i).data(Qt.UserRole)
        }
        for file in files:
            key = os.path.normcase(os.path.normpath(file))
            if key not in existing:
                self.extract_add_file_path(file)
                existing.add(key)
        added = self.extract_list.count() - before
        if added == 0:
            if files:
                QMessageBox.information(self, "提示", "剪贴板中没有新的压缩包")
            else:
                QMessageBox.information(self, "提示", "剪贴板中没有压缩包或包含压缩包的文件夹")

    def extract_clear(self):
        """清空解压列表"""
        self.extract_list.clear()
        self.extract_output_entry.clear()

    def extract_select_output(self):
        """选择解压输出目录"""
        path = QFileDialog.getExistingDirectory(self, "选择解压目录")
        if path:
            self.extract_output_entry.setText(path)

    def extract_start(self):
        """开始解压"""
        if self.extract_list.count() == 0:
            QMessageBox.warning(self, "提示", "请先添加要解压的文件")
            return

        output = self.extract_output_entry.text().strip()
        if not output:
            # 使用文件所在目录
            first_file = self.extract_list.item(0).data(Qt.UserRole)
            if first_file:
                output = os.path.dirname(first_file)
            else:
                output = os.path.expanduser("~/Desktop")

        # 确保输出目录存在
        os.makedirs(output, exist_ok=True)

        # 收集所有文件
        files = []
        for i in range(self.extract_list.count()):
            file_path = self.extract_list.item(i).data(Qt.UserRole)
            if file_path and os.path.exists(file_path):
                files.append(file_path)

        if not files:
            QMessageBox.warning(self, "提示", "没有有效的文件可解压")
            return

        # 检查是否启用独立文件夹
        separate_mode = self.extract_separate_check.isChecked()
        delete_archive = self.extract_delete_archive_check.isChecked()

        # 显示进度条
        self.extract_progress.setVisible(True)
        self.extract_progress.setMaximum(len(files))
        self.extract_progress.setValue(0)

        # 执行解压
        success = 0
        errors = 0
        extracted_files = []
        deleted_archives = 0
        delete_errors = 0
        for i, file_path in enumerate(files):
            try:
                if separate_mode:
                    # 独立文件夹模式：创建以压缩包名称命名的文件夹
                    base_name = os.path.splitext(os.path.basename(file_path))[0]
                    extract_dir = os.path.join(output, base_name)
                    os.makedirs(extract_dir, exist_ok=True)
                else:
                    # 普通模式：解压到输出目录
                    extract_dir = output

                self.do_extract(file_path, extract_dir)
                success += 1
                extracted_files.append(file_path)
            except Exception as e:
                errors += 1
                print(f"解压失败: {file_path} -> {e}")

            self.extract_progress.setValue(i + 1)

        self.extract_progress.setVisible(False)

        if delete_archive:
            for file_path in extracted_files:
                try:
                    os.remove(file_path)
                    deleted_archives += 1
                except Exception as e:
                    delete_errors += 1
                    print(f"删除压缩包失败: {file_path} -> {e}")

        msg = f"解压完成：{success} 个成功"
        if errors > 0:
            msg += f"，{errors} 个失败"
        if deleted_archives > 0:
            msg += f"\n已删除 {deleted_archives} 个压缩包"
        if delete_errors > 0:
            msg += f"\n{delete_errors} 个压缩包删除失败"
        QMessageBox.information(self, "完成", msg)

        # 解压成功后打开目录
        if success > 0:
            if sys.platform == "win32":
                os.startfile(output)
            elif sys.platform == "darwin":
                subprocess.run(["open", output])
            else:
                subprocess.run(["xdg-open", output])

    def do_extract(self, filepath: str, outdir: str):
        """根据文件类型执行解压"""
        lower = filepath.lower()

        if lower.endswith(".zip"):
            with zipfile.ZipFile(filepath, "r") as zf:
                zf.extractall(outdir)
        elif lower.endswith(".tar.gz") or lower.endswith(".tgz"):
            with tarfile.open(filepath, "r:gz") as tf:
                tf.extractall(outdir)
        elif lower.endswith(".tar.bz2"):
            with tarfile.open(filepath, "r:bz2") as tf:
                tf.extractall(outdir)
        elif lower.endswith(".tar"):
            with tarfile.open(filepath, "r:") as tf:
                tf.extractall(outdir)
        elif lower.endswith(".rar") or lower.endswith(".7z"):
            # 尝试用 7z 命令行解压
            self.extract_with_7z(filepath, outdir)
        else:
            raise ValueError(f"不支持的文件格式: {filepath}")

    def extract_with_7z(self, filepath: str, outdir: str):
        """使用 7z 命令行解压"""
        # 尝试常见路径
        sevenz_paths = [
            "7z",
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
        ]

        for cmd in sevenz_paths:
            try:
                result = subprocess.run(
                    [cmd, "x", filepath, f"-o{outdir}", "-y"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    return
            except FileNotFoundError:
                continue

        raise RuntimeError("未找到 7z 命令，请安装 7-Zip")


# ============================================================
# 启动
# ============================================================


class DragFilter(QObject):
    """Application-level event filter to detect drag gestures on DraggableListWidget items,
    bypassing child widgets (buttons, labels) that consume mouse events."""

    def __init__(self):
        super().__init__()
        self._press_pos = None
        self._drag_list = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
            self._press_pos = event.globalPos()
            self._drag_list = None
            w = QApplication.widgetAt(event.globalPos())
            while w:
                if isinstance(w, DraggableListWidget):
                    self._drag_list = w
                    break
                w = w.parentWidget()

        elif event.type() == QEvent.MouseMove and self._press_pos is not None and self._drag_list is not None:
            if event.buttons() & Qt.LeftButton:
                dist = (event.globalPos() - self._press_pos).manhattanLength()
                if dist >= QApplication.startDragDistance():
                    pos = self._drag_list.mapFromGlobal(self._press_pos)
                    item = self._drag_list.itemAt(pos)
                    if item:
                        self._drag_list.setCurrentItem(item)
                        self._drag_list.startDrag(Qt.MoveAction)
                    self._press_pos = None
                    self._drag_list = None
                    return True

        elif event.type() == QEvent.MouseButtonRelease:
            self._press_pos = None
            self._drag_list = None

        return False


def main():
    # Windows 任务栏图标支持
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('com.quickfolder.app')
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Quick Folder")
    app.installEventFilter(DragFilter())

    # 设置应用程序图标
    icon_path = Path(__file__).parent / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # 设置应用程序属性
    app.setQuitOnLastWindowClosed(True)

    window = QuickFolderPanel()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
