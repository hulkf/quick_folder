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
    QStyle, QDesktopWidget, QScrollArea, QSizePolicy, QComboBox, QCheckBox
)
from PyQt5.QtCore import (
    Qt, QSize, QPoint, QTimer, QThread, pyqtSignal, QMimeData,
    QUrl, QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import (
    QFont, QColor, QPalette, QIcon, QPixmap, QPainter,
    QDragEnterEvent, QDropEvent, QMouseEvent, QCursor,
    QLinearGradient, QBrush, QPen, QFontMetrics
)
import json
import os
import sys
import subprocess
import shutil
import ctypes
import zipfile
import tarfile
from pathlib import Path
from typing import List, Tuple, Optional

# ============================================================
# 配置
# ============================================================
CONFIG_FILE = Path(__file__).parent / "config.json"

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
        padding: 4px;
    }}
    QListWidget::item {{
        padding: 8px;
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
    """支持拖拽排序的列表控件，无滚动条，自动扩展"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QListWidget.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._item_height = 55

    def sizeHint(self):
        count = self.count()
        h = max(50, count * self._item_height + 10)
        return QSize(super().sizeHint().width(), h)

    def minimumSizeHint(self):
        count = self.count()
        h = max(50, count * self._item_height + 10)
        return QSize(100, h)


class FolderItemWidget(QWidget):
    """文件夹项组件"""

    def __init__(self, path: str, display_name: str, is_common: bool, theme: dict, parent=None):
        super().__init__(parent)
        self.path = path
        self.display_name = display_name
        self.is_common = is_common
        self.theme = theme

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)

        # 分区切换图标（⭐ / 📦）
        self.sec_icon = QLabel("⭐" if is_common else "📦")
        self.sec_icon.setFont(QFont("Segoe UI Emoji", 11))
        self.sec_icon.setCursor(Qt.PointingHandCursor)
        self.sec_icon.setStyleSheet("background: transparent; padding: 2px;")
        self.sec_icon.mousePressEvent = lambda e: self.toggle_section()
        layout.addWidget(self.sec_icon)

        # 文件夹图标
        exists = os.path.exists(path)
        folder_icon = QLabel("📂" if exists else "⚠️")
        folder_icon.setFont(QFont("Segoe UI Emoji", 11))
        layout.addWidget(folder_icon)

        # 名称
        name_label = QLabel(display_name)
        name_label.setFont(QFont("Segoe UI", 10))
        name_label.setStyleSheet(f"color: {theme['fg'] if exists else theme['danger']}; background: transparent;")
        name_label.setMinimumWidth(100)
        layout.addWidget(name_label, 1)

        # 操作按钮
        open_btn = QPushButton("打开")
        open_btn.setFixedSize(50, 30)
        open_btn.clicked.connect(lambda: self.open_folder())
        layout.addWidget(open_btn)

        close_btn = QPushButton("关闭")
        close_btn.setFixedSize(50, 30)
        close_btn.clicked.connect(lambda: self.close_folder())
        layout.addWidget(close_btn)

        paste_btn = QPushButton("粘贴")
        paste_btn.setFixedSize(50, 30)
        paste_btn.clicked.connect(lambda: self.paste_to())
        layout.addWidget(paste_btn)

        # 重排序按钮
        reorder_btn = QPushButton("排序")
        reorder_btn.setFixedSize(50, 30)
        reorder_btn.setStyleSheet(f"""
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
        """)
        reorder_btn.clicked.connect(lambda: self.reorder_files())
        layout.addWidget(reorder_btn)

        # 删除按钮
        del_btn = QPushButton("🗑")
        del_btn.setFixedSize(30, 30)
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {theme['btn_bg']};
                color: {theme['fg']};
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {theme['danger']};
                color: white;
            }}
        """)
        del_btn.clicked.connect(lambda: self.parent().parent().parent().remove_folder(self.path))
        layout.addWidget(del_btn)

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

    def close_folder(self):
        """关闭文件夹（在资源管理器中选中）"""
        if os.path.exists(self.path):
            if sys.platform == "win32":
                subprocess.run(["explorer", "/select,", self.path])
            elif sys.platform == "darwin":
                subprocess.run(["open", "-R", self.path])
            else:
                subprocess.run(["xdg-open", os.path.dirname(self.path)])

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

    def toggle_section(self):
        """切换分区"""
        parent_widget = self.window()
        if hasattr(parent_widget, 'toggle_section'):
            parent_widget.toggle_section(self.path, self.is_common)

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

        # 设置窗口图标（使用系统文件夹图标）
        self.setWindowIcon(QIcon.fromTheme("folder", QIcon(":/qt-project.org/styles/commonstyle/images/directory-open-128.png")))

        # 加载配置
        self.config = self.load_config()
        self.theme_name = self.config.get("theme", "dark_teal")
        self.theme = THEMES.get(self.theme_name, THEMES["dark_teal"])

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
        self.settings_tab = self.create_settings_tab()

        self.content_layout.addWidget(self.folder_tab)
        self.content_layout.addWidget(self.merge_tab)
        self.content_layout.addWidget(self.extract_tab)
        self.content_layout.addWidget(self.settings_tab)

        # 隐藏非活动 tab
        self.merge_tab.hide()
        self.extract_tab.hide()
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
        self.pin_btn.setFixedSize(28, 28)
        self.pin_btn.setCheckable(True)
        self.pin_btn.setChecked(True)
        self.pin_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['tab_inactive']};
                color: {self.theme['gray']};
                border: none;
                font-size: 14px;
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
            ("⚙️ 设置", 3),
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
        tabs = [self.folder_tab, self.merge_tab, self.extract_tab, self.settings_tab]
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
        add_btn = QPushButton("+ 添加文件夹")
        add_btn.clicked.connect(self.add_folder)
        toolbar.addWidget(add_btn)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # 可滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(8)

        # 分区：常用
        self.common_group = QGroupBox("⭐ 常用")
        self.common_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                color: {self.theme['gold']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        common_layout = QVBoxLayout(self.common_group)
        common_layout.setContentsMargins(4, 4, 4, 4)
        common_layout.setSpacing(2)
        self.common_list = DraggableListWidget()
        self.common_list.setDragDropMode(QListWidget.InternalMove)
        self.common_list.model().rowsMoved.connect(self.on_folder_reordered)
        common_layout.addWidget(self.common_list)
        scroll_layout.addWidget(self.common_group)

        # 分区：非常用
        self.uncommon_group = QGroupBox("📦 非常用")
        self.uncommon_group.setStyleSheet(f"""
            QGroupBox {{
                border: 1px solid {self.theme['border']};
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 12px;
                color: {self.theme['gray']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        uncommon_layout = QVBoxLayout(self.uncommon_group)
        uncommon_layout.setContentsMargins(4, 4, 4, 4)
        uncommon_layout.setSpacing(2)
        self.uncommon_list = DraggableListWidget()
        self.uncommon_list.setDragDropMode(QListWidget.InternalMove)
        self.uncommon_list.model().rowsMoved.connect(self.on_folder_reordered)
        uncommon_layout.addWidget(self.uncommon_list)
        scroll_layout.addWidget(self.uncommon_group)

        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll, 1)

        # 空状态提示
        self.empty_label = QLabel("✨ 点击「+ 添加文件夹」按钮添加快捷文件夹")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 14px;")
        layout.addWidget(self.empty_label)

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

        clear_btn = QPushButton("🗑 清空列表")
        clear_btn.clicked.connect(self.merge_clear_list)
        header.addWidget(clear_btn)

        merge_btn = QPushButton("▶ 开始合并")
        merge_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent']};
                color: white;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.theme['accent_hover']};
            }}
        """)
        merge_btn.clicked.connect(self.merge_start)
        header.addWidget(merge_btn)

        layout.addLayout(header)

        # 文件夹列表
        self.merge_list = DraggableListWidget()
        self.merge_list.setDragDropMode(QListWidget.InternalMove)
        layout.addWidget(self.merge_list, 1)

        # 输出目录
        output_layout = QHBoxLayout()
        output_label = QLabel("输出目录:")
        output_label.setStyleSheet(f"color: {self.theme['fg']};")
        output_layout.addWidget(output_label)

        self.merge_output_entry = QLineEdit()
        self.merge_output_entry.setPlaceholderText("当前目录")
        output_layout.addWidget(self.merge_output_entry, 1)

        select_btn = QPushButton("📂 选择目录")
        select_btn.clicked.connect(self.merge_select_output)
        output_layout.addWidget(select_btn)

        layout.addLayout(output_layout)

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

        add_btn = QPushButton("+ 添加文件")
        add_btn.clicked.connect(self.extract_add_files)
        header.addWidget(add_btn)

        paste_btn = QPushButton("📋 粘贴文件")
        paste_btn.clicked.connect(self.extract_paste_files)
        header.addWidget(paste_btn)

        clear_btn = QPushButton("🗑 清空")
        clear_btn.clicked.connect(self.extract_clear)
        header.addWidget(clear_btn)

        layout.addLayout(header)

        # 文件列表
        self.extract_list = QListWidget()
        layout.addWidget(self.extract_list, 1)

        # 底部：输出目录和解压按钮
        bottom_layout = QHBoxLayout()

        output_label = QLabel("解压到:")
        output_label.setStyleSheet(f"color: {self.theme['fg']};")
        bottom_layout.addWidget(output_label)

        self.extract_output_entry = QLineEdit()
        self.extract_output_entry.setPlaceholderText("同目录")
        bottom_layout.addWidget(self.extract_output_entry, 1)

        select_btn = QPushButton("📂 选择目录")
        select_btn.clicked.connect(self.extract_select_output)
        bottom_layout.addWidget(select_btn)

        layout.addLayout(bottom_layout)

        # 选项行：独立文件夹 + 解压按钮
        option_layout = QHBoxLayout()

        # 独立文件夹选项
        self.extract_separate_check = QCheckBox("独立文件夹")
        self.extract_separate_check.setChecked(False)
        self.extract_separate_check.setStyleSheet(f"color: {self.theme['fg']};")
        option_layout.addWidget(self.extract_separate_check)

        # 提示文字
        hint_label = QLabel("（每个压缩包解压到对应名称文件夹）")
        hint_label.setStyleSheet(f"color: {self.theme['gray']}; font-size: 11px;")
        option_layout.addWidget(hint_label)

        option_layout.addStretch()

        # 解压按钮
        extract_btn = QPushButton("▶ 开始解压")
        extract_btn.setMinimumHeight(30)
        extract_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.theme['accent']};
                color: white;
                font-weight: bold;
                border-radius: 4px;
                padding: 6px 16px;
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
        layout = QVBoxLayout(tab)
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
        layout.addStretch()

        # 关于
        about_group = QGroupBox("ℹ️ 关于")
        about_layout = QVBoxLayout(about_group)
        about_label = QLabel("Quick Folder v2.0\nPyQt5 版本\n\n一个轻量级的文件夹快捷入口面板")
        about_label.setStyleSheet(f"color: {self.theme['fg']};")
        about_layout.addWidget(about_label)
        layout.addWidget(about_group)

        return tab

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
                self.theme
            )

            item = QListWidgetItem()
            item.setSizeHint(widget.sizeHint() + QSize(0, 10))
            item.setData(Qt.UserRole, folder)

            if folder["is_common"]:
                self.common_list.addItem(item)
                self.common_list.setItemWidget(item, widget)
            else:
                self.uncommon_list.addItem(item)
                self.uncommon_list.setItemWidget(item, widget)

        self.empty_label.setVisible(len(self.folders) == 0)

        # 自动调整窗口高度
        self.adjust_window_height()

    def adjust_window_height(self):
        """根据文件夹数量自动调整窗口高度"""
        folder_count = len(self.folders)
        # 基础高度：标题栏(36) + tab栏(36) + 工具栏(36) + 分区标题(30) + 间距(20)
        base_height = 160
        # 每个文件夹项高度55
        item_height = 55
        # 最小和最大高度
        min_height = 250
        max_height = 700

        content_height = base_height + folder_count * item_height
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

    def extract_add_file_path(self, path: str):
        """添加文件到解压列表（由外部拖拽调用）"""
        if os.path.isfile(path):
            display_name = os.path.basename(path)
            item = QListWidgetItem(f"📦 {display_name}  ({path})")
            item.setData(Qt.UserRole, path)
            self.extract_list.addItem(item)

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

    def merge_clear_list(self):
        """清空合并列表"""
        self.merge_list.clear()
        self.merge_output_entry.clear()

    def update_merge_output_suggestion(self):
        """更新输出目录建议"""
        if self.merge_list.count() == 0:
            self.merge_output_entry.clear()
            return

        dirs = set()
        for i in range(self.merge_list.count()):
            path = self.merge_list.item(i).data(Qt.UserRole)
            if path:
                dirs.add(os.path.dirname(path))

        if len(dirs) == 1:
            self.merge_output_entry.setText(dirs.pop())
        else:
            self.merge_output_entry.clear()

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
            # 没有指定输出目录，在第一个文件夹的父目录下创建"合并文件"文件夹
            first_path = self.merge_list.item(0).data(Qt.UserRole)
            if first_path:
                parent_dir = os.path.dirname(first_path)
                output = os.path.join(parent_dir, "合并文件")
            else:
                output = os.path.join(os.getcwd(), "合并文件")

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
        msg = f"已合并 {copied} 个文件"
        if renamed > 0:
            msg += f"\n{renamed} 个文件被重命名"
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
        clipboard = QApplication.clipboard()
        mime = clipboard.mimeData()

        if mime.hasUrls():
            for url in mime.urls():
                if url.isLocalFile():
                    file = url.toLocalFile()
                    if os.path.isfile(file):
                        display_name = os.path.basename(file)
                        item = QListWidgetItem(f"📦 {display_name}  ({file})")
                        item.setData(Qt.UserRole, file)
                        self.extract_list.addItem(item)

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

        # 显示进度条
        self.extract_progress.setVisible(True)
        self.extract_progress.setMaximum(len(files))
        self.extract_progress.setValue(0)

        # 执行解压
        success = 0
        errors = 0
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
            except Exception as e:
                errors += 1
                print(f"解压失败: {file_path} -> {e}")

            self.extract_progress.setValue(i + 1)

        self.extract_progress.setVisible(False)

        msg = f"解压完成：{success} 个成功"
        if errors > 0:
            msg += f"，{errors} 个失败"
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

    # 设置应用程序属性
    app.setQuitOnLastWindowClosed(True)

    window = QuickFolderPanel()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
