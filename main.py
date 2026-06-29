#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Quick Folder - 快捷文件夹面板
一个可以固定在最顶层的文件夹快捷入口面板

功能:
  - 始终置顶的轻量面板（可取消置顶）
  - 常用 / 非常用分区
  - 每个文件夹：打开 / 关闭 / 粘贴 / 分区切换
  - 拖拽调整文件夹顺序
  - 粘贴文件到文件夹（带进度条）
  - 自动保存配置，重启后恢复
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import json
import os
import sys
import subprocess
import shutil
import ctypes
import zipfile
import tarfile
from pathlib import Path

# ============================================================
# 配置
# ============================================================
CONFIG_FILE = Path(__file__).parent / "config.json"

# ----- 主题定义 -----
THEMES = {
    "dark_teal": {
        "name": "暗色 teal",
        "bg":           "#2b2b2b",
        "fg":           "#e0e0e0",
        "title_bg":     "#1a1a1a",
        "section_bg":   "#333333",
        "item_bg":      "#3c3c3c",
        "item_hover":   "#484848",
        "btn_bg":       "#505050",
        "btn_hover":    "#606060",
        "accent":       "#26a69a",
        "accent_hover": "#2bbbad",
        "danger":       "#ef5350",
        "success":      "#66bb6a",
        "gold":         "#ffd54f",
        "gray":         "#9e9e9e",
        "border":       "#444444",
        "tab_active":   "#26a69a",
        "tab_inactive": "#252525",
        "tab_hover":    "#3a3a3a",
    },
    "dark_blue": {
        "name": "暗色 blue",
        "bg":           "#1e1e2e",
        "fg":           "#cdd6f4",
        "title_bg":     "#11111b",
        "section_bg":   "#313244",
        "item_bg":      "#45475a",
        "item_hover":   "#585b70",
        "btn_bg":       "#585b70",
        "btn_hover":    "#6c7086",
        "accent":       "#89b4fa",
        "accent_hover": "#b4d0fb",
        "danger":       "#f38ba8",
        "success":      "#a6e3a1",
        "gold":         "#f9e2af",
        "gray":         "#6c7086",
        "border":       "#45475a",
        "tab_active":   "#89b4fa",
        "tab_inactive": "#1e1e2e",
        "tab_hover":    "#313244",
    },
    "dark_purple": {
        "name": "暗色 purple",
        "bg":           "#20202a",
        "fg":           "#e0d4f5",
        "title_bg":     "#15151f",
        "section_bg":   "#2d2d3d",
        "item_bg":      "#38384a",
        "item_hover":   "#484860",
        "btn_bg":       "#4a4a62",
        "btn_hover":    "#5c5c78",
        "accent":       "#b48ead",
        "accent_hover": "#c8a8d0",
        "danger":       "#bf616a",
        "success":      "#a3be8c",
        "gold":         "#ebcb8b",
        "gray":         "#81a1c1",
        "border":       "#3d3d52",
        "tab_active":   "#b48ead",
        "tab_inactive": "#20202a",
        "tab_hover":    "#2d2d3d",
    },
    "light": {
        "name": "浅色",
        "bg":           "#f5f5f5",
        "fg":           "#333333",
        "title_bg":     "#e8e8e8",
        "section_bg":   "#e0e0e0",
        "item_bg":      "#ffffff",
        "item_hover":   "#e8f5e9",
        "btn_bg":       "#e0e0e0",
        "btn_hover":    "#d0d0d0",
        "accent":       "#00897b",
        "accent_hover": "#00796b",
        "danger":       "#d32f2f",
        "success":      "#388e3c",
        "gold":         "#f9a825",
        "gray":         "#757575",
        "border":       "#cccccc",
        "tab_active":   "#00897b",
        "tab_inactive": "#e8e8e8",
        "tab_hover":    "#d5d5d5",
    },
}

# 当前主题色板（可切换）
C = dict(THEMES["dark_teal"])

# ----- Windows API 常量 -----
_CF_HDROP = 15
_MAX_PATH = 260
_WM_DROPFILES = 0x004D

# ============================================================
# 主应用
# ============================================================
class QuickFolderPanel:
    """"""

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Quick Folder")
        self.topmost = True
        self.root.attributes("-topmost", True)

        # ---- 窗口样式（后续用 Win32 API 去掉边框，保留任务栏） ----
        self._hwnd = None

        # 先透明隐藏，等 _apply_borderless 去掉边框后再显示（避免闪烁）
        if sys.platform == "win32":
            self.root.attributes("-alpha", 0)

        # ---- 数据 ----
        self.folders: list[tuple[str, bool]] = []   # [(path, is_common), ...]

        # 行控件引用，供拖拽定位使用  path -> tk.Frame
        self._rows: dict[str, tk.Frame] = {}

        # ---- 拖拽状态 ----
        self._drag = {
            "active": False, "path": None,
            "src_idx": -1, "start_y": 0,
        }

        # ---- 窗口拖动 ----
        self._win_x = 0
        self._win_y = 0

        # ---- 构建 ----
        self.load_config()
        self._build_ui()
        self.refresh()
        self._position_window()

        # 窗口显示后通过 Win32 API 去掉边框（保留任务栏图标）
        if sys.platform == "win32":
            self.root.after(50, self._apply_borderless)

    # ============================================================
    # 持久化
    # ============================================================

    def load_config(self):
        self._theme_key = "dark_teal"
        if not CONFIG_FILE.exists():
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "order" in data and isinstance(data["order"], list):
                self.folders = [(p, c) for p, c in data["order"]]
            else:
                common = data.get("common", [])
                uncommon = data.get("uncommon", [])
                self.folders = [(p, True) for p in common] + [(p, False) for p in uncommon]
            # 加载主题
            saved_theme = data.get("theme", "dark_teal")
            if saved_theme in THEMES:
                self._theme_key = saved_theme
        except Exception:
            self.folders = []

        # 应用主题
        C.update(THEMES[self._theme_key])

        # 去重
        seen, deduped = set(), []
        for p, c in reversed(self.folders):
            if p not in seen:
                seen.add(p)
                deduped.append((p, c))
        self.folders = list(reversed(deduped))

    def save_config(self):
        data = {
            "common":  [p for p, c in self.folders if c],
            "uncommon":[p for p, c in self.folders if not c],
            "order":   self.folders,
            "theme":   self._theme_key,
        }
        try:
            CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[QuickFolder] save error: {e}")

    # ============================================================
    # UI 构建
    # ============================================================

    def _build_ui(self):
        self.root.configure(bg=C["bg"])

        self.main = tk.Frame(self.root, bg=C["bg"], bd=1, relief=tk.RAISED)
        self.main.pack(fill=tk.BOTH, expand=True)

        self._tab_buttons = {}
        self._build_titlebar()

        # Tab content container
        self.tab_container = tk.Frame(self.main, bg=C["bg"])
        self.tab_container.pack(fill=tk.BOTH, expand=True)

        # ---- Tab 1: 快捷文件夹 ----
        self.tab_folder = tk.Frame(self.tab_container, bg=C["bg"])

        # 工具栏（添加）
        folder_toolbar = tk.Frame(self.tab_folder, bg=C["bg"])
        folder_toolbar.pack(fill=tk.X, padx=6, pady=(6, 0))

        tk.Button(folder_toolbar, text="+ 添加",
                  command=self.add_folder,
                  bg=C["accent"], fg=C["fg"], bd=0,
                  padx=10, pady=2, cursor="hand2",
                  font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)

        self.body = tk.Frame(self.tab_folder, bg=C["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=2, pady=(4, 2))

        self._sec_common, self._inner_common = self._make_section(
            self.body, "⭐ 常用", C["gold"])
        self._sec_uncommon, self._inner_uncommon = self._make_section(
            self.body, "📦 非常用", C["gray"])

        self._empty = tk.Label(
            self.body,
            text="✨ 点击「+ 添加」按钮添加快捷文件夹",
            bg=C["bg"], fg=C["gray"],
            font=("Segoe UI", 10), pady=12,
        )

        # ---- Tab 2: 文件夹合并 ----
        self.tab_merge = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_merge_tab()

        # ---- Tab 3: 文件解压 ----
        self.tab_extract = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_extract_tab()

        # ---- Tab 4: 设置 ----
        self.tab_settings = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_settings_tab()

        # Setup drag-and-drop for the whole window (Windows only)
        if sys.platform == "win32":
            self.root.after(100, self._setup_drag_drop)

        # Register tabs and show default
        self._tabs = {"folder": self.tab_folder, "merge": self.tab_merge, "extract": self.tab_extract, "settings": self.tab_settings}
        self._active_tab = None
        self._show_tab("folder")

    # ---------- 标题栏 ----------

    def _build_titlebar(self):
        bar = tk.Frame(self.main, bg=C["title_bg"], height=36)
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # 左侧 accent 色条
        accent_bar = tk.Frame(bar, bg=C["accent"], width=4)
        accent_bar.pack(side=tk.LEFT, fill=tk.Y)

        # 左侧图标 + 标题
        self._title_lbl = tk.Label(bar, text="📁 Quick Folder",
                                   bg=C["title_bg"], fg=C["fg"],
                                   font=("Segoe UI", 10, "bold"))
        self._title_lbl.pack(side=tk.LEFT, padx=(8, 16))

        # 窗口拖动
        for w in (bar, self._title_lbl):
            w.bind("<ButtonPress-1>", self._win_drag_start)
            w.bind("<B1-Motion>", self._win_drag_move)

        # Tab 按钮（嵌入标题栏）
        self._tab_buttons = {}
        tabs = [
            ("folder", "📂 文件夹"),
            ("merge", "📁 合并"),
            ("extract", "📦 解压"),
            ("settings", "⚙️ 设置"),
        ]

        for key, label in tabs:
            btn = tk.Button(bar, text=label,
                            command=lambda k=key: self._show_tab(k),
                            bg=C["tab_inactive"], fg=C["gray"], bd=0,
                            padx=10, pady=0, cursor="hand2",
                            font=("Segoe UI", 9),
                            activebackground=C["tab_hover"],
                            activeforeground=C["fg"])
            btn.pack(side=tk.LEFT, padx=1, pady=4)
            self._tab_buttons[key] = btn

        # 右侧按钮
        bf = tk.Frame(bar, bg=C["title_bg"])
        bf.pack(side=tk.RIGHT, padx=6)

        # 置顶切换
        self._pin_btn = self._tb_btn(bf, "📌", self.toggle_topmost)
        self._pin_btn.pack(side=tk.LEFT, padx=2)

        # 关闭
        self._tb_btn(bf, "✕", self.root.quit, hover_bg=C["danger"]).pack(side=tk.LEFT, padx=2)

    def _show_tab(self, key: str):
        if key == self._active_tab:
            return
        # Hide current
        if self._active_tab and self._active_tab in self._tabs:
            self._tabs[self._active_tab].pack_forget()
            self._tab_buttons[self._active_tab].config(bg=C["tab_inactive"], fg=C["gray"])
        # Show new
        self._active_tab = key
        self._tabs[key].pack(fill=tk.BOTH, expand=True)
        self._tab_buttons[key].config(bg=C["tab_active"], fg=C["fg"])
        # Refresh folder tab if switching to it (no auto_size to avoid flicker)
        if key == "folder":
            self.refresh(auto_size=False)

    # ---------- 文件夹合并 Tab ----------

    def _build_merge_tab(self):
        self._merge_folders = []  # [(path, display_name), ...]
        self._merge_output_dir = ""

        # Top bar with title and buttons
        top = tk.Frame(self.tab_merge, bg=C["bg"])
        top.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(top, text="📁 文件夹合并", bg=C["bg"], fg=C["fg"],
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = tk.Frame(top, bg=C["bg"])
        btn_frame.pack(side=tk.RIGHT)

        btn_add = tk.Button(btn_frame, text="📁 添加文件夹",
                           command=self._merge_add_folder,
                           bg=C["accent"], fg=C["fg"], bd=0,
                           padx=12, pady=4, cursor="hand2",
                           font=("Segoe UI", 9))
        btn_add.pack(side=tk.LEFT, padx=4)
        btn_add.bind("<Enter>", lambda e: btn_add.config(bg=C["accent_hover"]))
        btn_add.bind("<Leave>", lambda e: btn_add.config(bg=C["accent"]))

        btn_clear = tk.Button(btn_frame, text="🗑 清空列表",
                             command=self._merge_clear_list,
                             bg=C["btn_bg"], fg=C["fg"], bd=0,
                             padx=12, pady=4, cursor="hand2",
                             font=("Segoe UI", 9))
        btn_clear.pack(side=tk.LEFT, padx=4)
        btn_clear.bind("<Enter>", lambda e: btn_clear.config(bg=C["danger"]))
        btn_clear.bind("<Leave>", lambda e: btn_clear.config(bg=C["btn_bg"]))

        btn_start = tk.Button(btn_frame, text="▶ 开始合并",
                             command=self._merge_start,
                             bg=C["accent"], fg=C["fg"], bd=0,
                             padx=12, pady=4, cursor="hand2",
                             font=("Segoe UI", 9))
        btn_start.pack(side=tk.LEFT, padx=4)
        btn_start.bind("<Enter>", lambda e: btn_start.config(bg=C["accent_hover"]))
        btn_start.bind("<Leave>", lambda e: btn_start.config(bg=C["accent"]))

        # Folder list
        list_frame = tk.Frame(self.tab_merge, bg=C["item_bg"], bd=0)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._merge_listbox = tk.Listbox(list_frame, bg=C["item_bg"], fg=C["fg"],
                                          selectbackground=C["accent"], selectforeground="white",
                                          font=("Segoe UI", 9), bd=0, highlightthickness=0)
        scrollbar = tk.Scrollbar(list_frame, command=self._merge_listbox.yview)
        self._merge_listbox.configure(yscrollcommand=scrollbar.set)
        self._merge_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Output dir section
        output_frame = tk.Frame(self.tab_merge, bg=C["bg"])
        output_frame.pack(fill=tk.X, padx=8, pady=(0, 8))

        tk.Label(output_frame, text="输出目录:", bg=C["bg"], fg=C["fg"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))

        self._merge_output_var = tk.StringVar(value="当前目录")
        self._merge_output_entry = tk.Entry(output_frame, textvariable=self._merge_output_var,
                                             bg=C["item_bg"], fg=C["fg"], font=("Segoe UI", 9),
                                             bd=0, highlightthickness=1, highlightbackground=C["border"])
        self._merge_output_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))

        btn_select = tk.Button(output_frame, text="📂 选择目录",
                              command=self._merge_select_output,
                              bg=C["btn_bg"], fg=C["fg"], bd=0,
                              padx=12, pady=4, cursor="hand2",
                              font=("Segoe UI", 9))
        btn_select.pack(side=tk.LEFT)
        btn_select.bind("<Enter>", lambda e: btn_select.config(bg=C["btn_hover"]))
        btn_select.bind("<Leave>", lambda e: btn_select.config(bg=C["btn_bg"]))

        # Drag and drop support for the listbox
        self._merge_listbox.bind("<ButtonPress-1>", self._merge_drag_start)
        self._merge_listbox.bind("<B1-Motion>", self._merge_drag_move)
        self._merge_listbox.bind("<ButtonRelease-1>", self._merge_drag_end)
        self._merge_drag = {"active": False, "start_idx": None}

    def _merge_add_folder(self):
        folder = filedialog.askdirectory(title="选择要合并的文件夹")
        if folder:
            self._merge_add_folder_path(folder)

    def _merge_add_folder_path(self, folder):
        if folder and os.path.isdir(folder) and folder not in [f[0] for f in self._merge_folders]:
            display = os.path.basename(folder) or folder
            self._merge_folders.append((folder, display))
            self._merge_listbox.insert(tk.END, display)
            self._merge_update_output_suggestion()

    def _merge_clear_list(self):
        self._merge_folders.clear()
        self._merge_listbox.delete(0, tk.END)
        self._merge_output_var.set("当前目录")

    def _merge_update_output_suggestion(self):
        if not self._merge_folders:
            self._merge_output_var.set("当前目录")
            return
        dirs = [os.path.dirname(f[0]) for f in self._merge_folders]
        if len(set(dirs)) == 1:
            self._merge_output_var.set(dirs[0])
        else:
            self._merge_output_var.set("当前目录")

    def _merge_select_output(self):
        folder = filedialog.askdirectory(title="选择输出目录")
        if folder:
            self._merge_output_var.set(folder)

    def _merge_drag_start(self, event):
        idx = self._merge_listbox.nearest(event.y)
        self._merge_drag["active"] = True
        self._merge_drag["start_idx"] = idx

    def _merge_drag_move(self, event):
        pass

    def _merge_drag_end(self, event):
        if not self._merge_drag["active"]:
            return
        start_idx = self._merge_drag["start_idx"]
        end_idx = self._merge_listbox.nearest(event.y)
        if start_idx is not None and end_idx is not None and start_idx != end_idx:
            item = self._merge_folders.pop(start_idx)
            self._merge_folders.insert(end_idx, item)
            self._merge_listbox.delete(0, tk.END)
            for _, display in self._merge_folders:
                self._merge_listbox.insert(tk.END, display)
            self._merge_listbox.selection_set(end_idx)
        self._merge_drag["active"] = False
        self._merge_drag["start_idx"] = None

    def _merge_start(self):
        if not self._merge_folders:
            messagebox.showwarning("提示", "请先添加要合并的文件夹")
            return

        output = self._merge_output_var.get().strip()
        if not output or output == "当前目录":
            output = os.path.dirname(self._merge_folders[0][0])

        os.makedirs(output, exist_ok=True)

        copied = 0
        skipped = 0
        for folder_path, _ in self._merge_folders:
            for root, dirs, files in os.walk(folder_path):
                for fname in files:
                    src = os.path.join(root, fname)
                    rel = os.path.relpath(src, folder_path)
                    dst = os.path.join(output, rel)

                    # Auto-rename if file exists
                    if os.path.exists(dst):
                        base, ext = os.path.splitext(dst)
                        counter = 1
                        while os.path.exists(f"{base}_{counter}{ext}"):
                            counter += 1
                        dst = f"{base}_{counter}{ext}"
                        skipped += 1

                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
                    copied += 1

        messagebox.showinfo("合并完成", f"已合并 {copied} 个文件\n{skipped} 个文件被重命名")

    # ---------- 文件解压 Tab ----------

    def _build_extract_tab(self):
        self._extract_files = []  # [(path, display_name), ...]

        # Top bar with buttons
        top = tk.Frame(self.tab_extract, bg=C["bg"])
        top.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(top, text="📦 文件解压", bg=C["bg"], fg=C["fg"],
                 font=("Segoe UI", 11, "bold")).pack(side=tk.LEFT, padx=4)

        # Buttons
        btn_frame = tk.Frame(top, bg=C["bg"])
        btn_frame.pack(side=tk.RIGHT)

        self._ext_btn_add = tk.Button(btn_frame, text="+ 添加文件",
                                       command=self._extract_add_files,
                                       bg=C["accent"], fg=C["fg"], bd=0,
                                       padx=12, pady=4, cursor="hand2",
                                       font=("Segoe UI", 9))
        self._ext_btn_add.pack(side=tk.LEFT, padx=4)
        self._ext_btn_add.bind("<Enter>", lambda e: self._ext_btn_add.config(bg=C["accent_hover"]))
        self._ext_btn_add.bind("<Leave>", lambda e: self._ext_btn_add.config(bg=C["accent"]))

        self._ext_btn_paste = tk.Button(btn_frame, text="📋 粘贴文件",
                                         command=self._extract_paste_files,
                                         bg=C["btn_bg"], fg=C["fg"], bd=0,
                                         padx=12, pady=4, cursor="hand2",
                                         font=("Segoe UI", 9))
        self._ext_btn_paste.pack(side=tk.LEFT, padx=4)
        self._ext_btn_paste.bind("<Enter>", lambda e: self._ext_btn_paste.config(bg=C["btn_hover"]))
        self._ext_btn_paste.bind("<Leave>", lambda e: self._ext_btn_paste.config(bg=C["btn_bg"]))

        self._ext_btn_clear = tk.Button(btn_frame, text="🗑 清空",
                                         command=self._extract_clear,
                                         bg=C["btn_bg"], fg=C["fg"], bd=0,
                                         padx=12, pady=4, cursor="hand2",
                                         font=("Segoe UI", 9))
        self._ext_btn_clear.pack(side=tk.LEFT, padx=4)
        self._ext_btn_clear.bind("<Enter>", lambda e: self._ext_btn_clear.config(bg=C["danger"]))
        self._ext_btn_clear.bind("<Leave>", lambda e: self._ext_btn_clear.config(bg=C["btn_bg"]))

        # File list area (scrollable)
        list_frame = tk.Frame(self.tab_extract, bg=C["item_bg"], bd=0)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        self._ext_listbox = tk.Listbox(list_frame, bg=C["item_bg"], fg=C["fg"],
                                        selectbackground=C["accent"],
                                        selectforeground=C["fg"],
                                        font=("Consolas", 9),
                                        bd=0, highlightthickness=0,
                                        activestyle="none",
                                        selectborderwidth=0)
        scrollbar = tk.Scrollbar(list_frame, command=self._ext_listbox.yview,
                                  bg=C["item_bg"], troughcolor=C["bg"])
        self._ext_listbox.config(yscrollcommand=scrollbar.set)
        self._ext_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Right-click menu for listbox
        self._ext_menu = tk.Menu(self.root, tearoff=0, bg=C["item_bg"], fg=C["fg"],
                                  font=("Segoe UI", 9), activebackground=C["accent"],
                                  activeforeground=C["fg"])
        self._ext_menu.add_command(label="移除选中", command=self._extract_remove_selected)
        self._ext_menu.add_command(label="清空列表", command=self._extract_clear)
        self._ext_listbox.bind("<Button-3>", self._extract_show_menu)

        # Bottom bar: output dir + extract button
        bottom = tk.Frame(self.tab_extract, bg=C["bg"])
        bottom.pack(fill=tk.X, padx=8, pady=8)

        tk.Label(bottom, text="解压到:", bg=C["bg"], fg=C["gray"],
                 font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 8))

        self._ext_outdir = tk.StringVar(value=str(Path.home() / "Desktop"))
        out_entry = tk.Entry(bottom, textvariable=self._ext_outdir,
                              bg=C["item_bg"], fg=C["fg"], bd=0,
                              font=("Segoe UI", 9), width=30,
                              insertbackground=C["fg"])
        out_entry.pack(side=tk.LEFT, padx=(0, 8))

        tk.Button(bottom, text="📁", command=self._extractChooseDir,
                  bg=C["btn_bg"], fg=C["fg"], bd=0, padx=6,
                  cursor="hand2", font=("Segoe UI Emoji", 9)).pack(side=tk.LEFT, padx=(0, 12))

        self._ext_btn_extract = tk.Button(bottom, text="📦 解压",
                                           command=self._extractRun,
                                           bg=C["accent"], fg=C["fg"], bd=0,
                                           padx=20, pady=4, cursor="hand2",
                                           font=("Segoe UI", 10, "bold"))
        self._ext_btn_extract.pack(side=tk.RIGHT)
        self._ext_btn_extract.bind("<Enter>", lambda e: self._ext_btn_extract.config(bg=C["accent_hover"]))
        self._ext_btn_extract.bind("<Leave>", lambda e: self._ext_btn_extract.config(bg=C["accent"]))

        # Status
        self._ext_status = tk.Label(bottom, text="", bg=C["bg"], fg=C["gray"],
                                     font=("Segoe UI", 9))
        self._ext_status.pack(side=tk.RIGHT, padx=12)

    # ---------- 辅助：标题栏按钮 ----------

    def _tb_btn(self, parent, text, cmd, hover_bg=None):
        btn = tk.Button(parent, text=text, command=cmd,
                        bg=C["title_bg"], fg=C["fg"], bd=0, padx=8, pady=2,
                        cursor="hand2", font=("Segoe UI", 9),
                        activebackground=C["item_bg"], activeforeground=C["fg"])
        hb = hover_bg or C["tab_hover"]
        btn.bind("<Enter>", lambda e: btn.config(bg=hb))
        btn.bind("<Leave>", lambda e: btn.config(bg=C["title_bg"]))
        return btn

    # ---------- 分区容器 ----------

    def _make_section(self, parent, title, fg_color):
        outer = tk.Frame(parent, bg=C["section_bg"], bd=0)

        hdr = tk.Frame(outer, bg=C["section_bg"])
        hdr.pack(fill=tk.X, padx=6, pady=(4, 2))
        tk.Label(hdr, text=title, bg=C["section_bg"], fg=fg_color,
                 font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)

        inner = tk.Frame(outer, bg=C["bg"])
        inner.pack(fill=tk.X, padx=4, pady=(0, 4))
        return outer, inner

    # ============================================================
    # 刷新面板
    # ============================================================

    def refresh(self, auto_size=True):
        self._rows.clear()
        for w in self._inner_common.winfo_children():
            w.destroy()
        for w in self._inner_uncommon.winfo_children():
            w.destroy()

        if self.folders:
            self._empty.pack_forget()
        else:
            self._empty.pack(fill=tk.X, pady=20)

        for idx, (path, is_common) in enumerate(self.folders):
            parent = self._inner_common if is_common else self._inner_uncommon
            self._add_row(parent, path, idx)

        # 始终显示两个分区
        self._sec_common.pack(fill=tk.X, pady=(0, 1))
        self._sec_uncommon.pack(fill=tk.X)

        if auto_size:
            self.root.after(10, self._auto_size)

    def _auto_size(self):
        try:
            if not self.main.winfo_ismapped():
                return
            w = max(620, self.main.winfo_reqwidth() + 10)
            h = max(80, min(self.main.winfo_reqheight(), 600))
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    # ============================================================
    # 单行
    # ============================================================

    def _add_row(self, parent, path: str, index: int):
        """创建一行文件夹快捷项"""
        exists = os.path.exists(path)
        display = (os.path.basename(path) or path).strip()
        if len(display) > 20:
            display = display[:18] + "…"

        bg = C["item_bg"]
        fg_path = C["fg"] if exists else C["danger"]

        row = tk.Frame(parent, bg=bg, height=34)
        row.pack(fill=tk.X, pady=1)
        row.pack_propagate(False)

        row.bind("<Enter>", lambda e: row.config(bg=C["item_hover"]))
        row.bind("<Leave>", lambda e: row.config(bg=bg))

        # ---- 分区切换图标（⭐ / 📦） ----
        is_common = self._is_common(path)
        sec_icon = "⭐" if is_common else "📦"
        sec_btn = tk.Label(row, text=sec_icon, bg=bg,
                           font=("Segoe UI Emoji", 9),
                           cursor="hand2")
        sec_btn.pack(side=tk.LEFT, padx=(4, 0))
        sec_btn.bind("<Button-1>", lambda e, p=path: self.toggle_section(p))
        sec_btn.bind("<Enter>", lambda e: sec_btn.config(bg=C["item_hover"]))
        sec_btn.bind("<Leave>", lambda e: sec_btn.config(bg=bg))

        # ---- 文件夹图标 ----
        icon = "📂" if exists else "⚠️"
        tk.Label(row, text=icon, bg=bg, fg=C["fg"],
                 font=("Segoe UI Emoji", 9)).pack(side=tk.LEFT, padx=(2, 4))

        # ---- 名称 ----
        name = tk.Label(row, text=display, bg=bg, fg=fg_path,
                        font=("Segoe UI", 9),
                        anchor=tk.W, width=18)
        name.pack(side=tk.LEFT, padx=2)

        # ---- 按钮工厂 ----
        def _btn(text, cmd, hb=None):
            if hb is None:
                hb = C["accent"]
            b = tk.Button(row, text=text, command=cmd,
                          font=("Segoe UI", 8),
                          bd=0, padx=8, pady=2, height=1,
                          cursor="hand2",
                          bg=C["btn_bg"], fg=C["fg"],
                          activebackground=hb, activeforeground="white")
            b.bind("<Enter>", lambda e: b.config(bg=hb))
            b.bind("<Leave>", lambda e: b.config(bg=C["btn_bg"]))
            b.pack(side=tk.LEFT, padx=2)
            return b

        # ---- 操作按钮 ----
        _btn("打开", lambda p=path: self.open_folder(p))
        _btn("关闭", lambda p=path: self.close_folder(p))
        _btn("粘贴", lambda p=path: self.paste_to(p))
        _btn("删除zip", lambda p=path: self.delete_archives(p), hb=C["danger"])

        # 删除
        _del = tk.Button(row, text="🗑",
                         command=lambda p=path: self.remove_folder(p),
                         font=("Segoe UI Emoji", 8),
                         bd=0, padx=4, pady=2, height=1,
                         cursor="hand2",
                         bg=C["btn_bg"], fg=C["fg"],
                         activebackground=C["danger"], activeforeground="white")
        _del.bind("<Enter>", lambda e: _del.config(bg=C["danger"]))
        _del.bind("<Leave>", lambda e: _del.config(bg=C["btn_bg"]))
        _del.pack(side=tk.LEFT, padx=2)

        # ---- 拖拽手柄 ----
        drag = tk.Label(row, text="⋮⋮", bg=bg, fg="#666666",
                        cursor="fleur", font=("Segoe UI", 8))
        drag.pack(side=tk.RIGHT, padx=(4, 4))

        for w in (drag, row):
            w.bind("<ButtonPress-1>", lambda e, p=path: self._drag_start(e, p))
            w.bind("<B1-Motion>",     lambda e, p=path: self._drag_move(e, p))
            w.bind("<ButtonRelease-1>", lambda e: self._drag_end(e))

        self._rows[path] = row

    # ---------- 辅助 ----------

    def _is_common(self, path: str) -> bool:
        for p, c in self.folders:
            if p == path:
                return c
        return True

    # ============================================================
    # 文件夹操作
    # ============================================================

    def open_folder(self, path: str):
        """在资源管理器中打开"""
        if not os.path.exists(path):
            messagebox.showwarning("提示", f"文件夹不存在:\n{path}")
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            else:
                subprocess.run(["xdg-open", path], check=False)
        except Exception as e:
            messagebox.showerror("错误", f"打开失败:\n{e}")

    def close_folder(self, path: str):
        """关闭正在显示此文件夹的资源管理器窗口（EnumWindows 模糊匹配）"""
        if sys.platform != "win32":
            return

        folder_name = os.path.basename(path)
        if not folder_name:
            return

        user32 = ctypes.windll.user32
        found = []

        # EnumWindows 回调：匹配窗口标题 + Explorer 类名
        WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool,
                                         ctypes.c_void_p,  # HWND
                                         ctypes.c_void_p)  # LPARAM

        def enum_proc(hwnd, lparam):
            if not user32.IsWindowVisible(hwnd):
                return True

            # 窗口类名必须是 Explorer 相关
            cls_buf = ctypes.create_unicode_buffer(64)
            user32.GetClassNameW(hwnd, cls_buf, 64)
            if cls_buf.value not in ("CabinetWClass", "ExploreWClass"):
                return True

            # 读取窗口标题
            length = user32.GetWindowTextLengthW(hwnd)
            if length <= 0:
                return True

            title_buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, title_buf, length + 1)
            title = title_buf.value

            # 模糊匹配：标题包含文件夹名即可
            if folder_name.lower() in title.lower():
                found.append(hwnd)

            return True

        callback = WNDENUMPROC(enum_proc)
        user32.EnumWindows(callback, 0)

        # 关闭所有匹配的窗口
        for hwnd in found:
            user32.PostMessageW(hwnd, 0x0010, 0, 0)  # WM_CLOSE

        # 如果没找到，后台静默尝试 taskkill
        if not found:
            try:
                subprocess.Popen(
                    ["taskkill", "/f",
                     "/fi", f"WINDOWTITLE eq {folder_name}*",
                     "/fi", "IMAGENAME eq explorer.exe"],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    startupinfo=self._hide_window(),
                )
            except Exception:
                pass

    # ---------- 剪贴板读取 ----------

    def _get_clipboard_files(self) -> list[str]:
        """从 Windows 剪贴板读取文件列表（ctypes + PowerShell 双保险）"""
        # ---- 方法 1：ctypes 直接读取（微秒级） ----
        try:
            files = self._get_clipboard_files_ctypes()
            if files:
                return files
        except Exception as e:
            print(f"[QuickFolder] ctypes clipboard failed: {e}")

        # ---- 方法 2：PowerShell 兜底 ----
        try:
            files = self._get_clipboard_files_ps()
            if files:
                return files
        except Exception as e:
            print(f"[QuickFolder] PS clipboard failed: {e}")

        return []

    def _get_clipboard_files_ctypes(self) -> list[str]:
        """ctypes 方式读取剪贴板文件列表（速度快）"""
        user32 = ctypes.windll.user32
        shell32 = ctypes.windll.shell32

        # 正确设置返回类型和参数类型（64 位兼容）
        user32.GetClipboardData.restype = ctypes.c_void_p
        user32.GetClipboardData.argtypes = [ctypes.c_uint]

        shell32.DragQueryFileW.argtypes = [
            ctypes.c_void_p,   # HDROP (指针大小)
            ctypes.c_uint,     # UINT iFile
            ctypes.c_void_p,   # LPTSTR lpszFile
            ctypes.c_uint,     # UINT cch
        ]
        shell32.DragQueryFileW.restype = ctypes.c_uint

        if not user32.OpenClipboard(None):
            return []

        try:
            if not user32.IsClipboardFormatAvailable(_CF_HDROP):
                return []

            handle = user32.GetClipboardData(_CF_HDROP)
            if not handle:
                return []

            # DragQueryFileW: index=-1 返回文件数
            count = shell32.DragQueryFileW(handle, -1, None, 0)
            if count <= 0:
                return []

            files = []
            for i in range(count):
                buf = ctypes.create_unicode_buffer(_MAX_PATH)
                shell32.DragQueryFileW(handle, i, buf, _MAX_PATH)
                files.append(buf.value)
            return files
        finally:
            user32.CloseClipboard()

    def _get_clipboard_files_ps(self) -> list[str]:
        """PowerShell 方式读取剪贴板（兜底）"""
        ps = """
        Add-Type -AssemblyName System.Windows.Forms
        if ([System.Windows.Forms.Clipboard]::ContainsFileDropList()) {
            $files = [System.Windows.Forms.Clipboard]::GetFileDropList()
            foreach ($f in $files) { Write-Output "FILE:$f" }
        } else {
            Write-Output "NOFILES"
        }
        """
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=8,
            startupinfo=self._hide_window(),
        )

        lines = [x.strip() for x in r.stdout.strip().split("\n") if x.strip()]
        if not lines or lines[0] == "NOFILES":
            return []

        return [x[5:].strip() for x in lines if x.startswith("FILE:")]

    def _hide_window(self):
        """返回一个不显示窗口的 STARTUPINFO"""
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        return si

    # ---------- 粘贴（带进度条） ----------

    def paste_to(self, path: str):
        """将剪贴板中的文件粘贴到此文件夹（带进度条）"""
        if not os.path.exists(path):
            messagebox.showwarning("提示", f"文件夹不存在:\n{path}")
            return

        # 读取剪贴板文件列表
        files = self._get_clipboard_files()
        if not files:
            messagebox.showinfo("提示", "剪贴板中没有文件数据")
            return

        total = len(files)

        # ---- 进度对话框 ----
        dlg = tk.Toplevel(self.root)
        dlg.title("粘贴文件")
        dlg.geometry("420x160")
        dlg.attributes("-topmost", True)
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        # 居中
        dlg.update_idletasks()
        x = dlg.winfo_screenwidth() // 2 - 210
        y = dlg.winfo_screenheight() // 2 - 80
        dlg.geometry(f"+{x}+{y}")

        # 当前文件名
        lbl_file = tk.Label(dlg, text="", bg=C["bg"], fg=C["fg"],
                            font=("Segoe UI", 9),
                            anchor=tk.W, wraplength=400)
        lbl_file.pack(fill=tk.X, padx=15, pady=(12, 4))

        # 进度条
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor=C["item_bg"],
                        background=C["accent"],
                        thickness=8)
        prog = ttk.Progressbar(dlg, length=380, mode="determinate",
                               maximum=total, style="Custom.Horizontal.TProgressbar")
        prog.pack(pady=4, padx=15)

        # 计数
        lbl_count = tk.Label(dlg, text=f"0 / {total}", bg=C["bg"], fg=C["gray"],
                             font=("Segoe UI", 9))
        lbl_count.pack()

        # 取消标记
        cancelled = [False]

        def cancel():
            cancelled[0] = True

        btn_cancel = tk.Button(dlg, text="取消", command=cancel,
                               bg=C["btn_bg"], fg=C["fg"],
                               font=("Segoe UI", 9),
                               bd=0, padx=20, pady=4, cursor="hand2",
                               activebackground=C["danger"])
        btn_cancel.pack(pady=6)

        # ---- 执行复制 ----
        copied = 0
        errors = 0

        for i, src in enumerate(files):
            if cancelled[0]:
                break

            name = os.path.basename(src)
            lbl_file.config(text=f"正在复制: {name}")
            prog["value"] = i
            lbl_count.config(text=f"{i} / {total}")
            dlg.update()

            try:
                dest = os.path.join(path, name)
                if os.path.isdir(src):
                    shutil.copytree(src, dest, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, dest)
                copied += 1
            except Exception:
                errors += 1

        # 最后更新
        prog["value"] = copied
        lbl_count.config(text=f"{copied} / {total}")
        dlg.update()

        dlg.destroy()

        # ---- 结果 ----
        if cancelled[0]:
            if copied:
                messagebox.showinfo("已取消", f"已复制 {copied} 个文件，已取消")
        else:
            msg = f"已完成：{copied} 个文件"
            if errors:
                msg += f"，{errors} 个失败"
            messagebox.showinfo("完成", msg)

    # ---------- 删除压缩文件 ----------

    def delete_archives(self, path: str):
        """删除指定文件夹中的所有压缩文件"""
        if not os.path.exists(path):
            messagebox.showwarning("提示", f"文件夹不存在:\n{path}")
            return

        # 支持的压缩格式
        archive_extensions = {
            '.zip', '.rar', '.7z', 
            '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tar.xz',
            '.gz', '.bz2', '.xz',
            '.cab', '.iso', '.dmg',
        }

        # 扫描压缩文件
        archives = []
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if any(f.lower().endswith(ext) for ext in archive_extensions):
                        archives.append(os.path.join(root, f))
        except Exception as e:
            messagebox.showerror("错误", f"扫描文件夹失败:\n{e}")
            return

        if not archives:
            messagebox.showinfo("提示", "未找到压缩文件")
            return

        # 显示确认对话框
        msg = f"找到 {len(archives)} 个压缩文件，确定要删除吗？\n\n"
        # 显示前10个文件
        for i, f in enumerate(archives[:10]):
            msg += f"• {os.path.basename(f)}\n"
        if len(archives) > 10:
            msg += f"... 还有 {len(archives) - 10} 个文件\n"
        msg += "\n⚠️ 此操作不可恢复！"

        if not messagebox.askyesno("确认删除", msg, icon="warning"):
            return

        # 执行删除
        deleted = 0
        errors = 0
        for f in archives:
            try:
                os.remove(f)
                deleted += 1
            except Exception:
                errors += 1

        # 显示结果
        result_msg = f"已删除 {deleted} 个压缩文件"
        if errors:
            result_msg += f"\n{errors} 个文件删除失败"
        messagebox.showinfo("完成", result_msg)

    # ---------- 分区切换 ----------

    def toggle_section(self, path: str):
        """在常用/非常用之间切换"""
        for i, (p, c) in enumerate(self.folders):
            if p == path:
                self.folders[i] = (path, not c)
                break
        self.save_config()
        self.refresh()

    # ---------- 置顶切换 ----------

    def toggle_topmost(self):
        """切换窗口置顶状态"""
        self.topmost = not self.topmost
        self.root.attributes("-topmost", self.topmost)
        icon = "📌" if self.topmost else "📍"
        color = C["accent"] if self.topmost else C["gray"]
        self._pin_btn.config(text=icon, fg=color)
        self._title_lbl.config(text=f"📁 Quick Folder{'  (已取消置顶)' if not self.topmost else ''}")

    # ---------- 添加 / 删除 ----------

    def add_folder(self):
        """选择并添加新文件夹（默认进常用）"""
        path = filedialog.askdirectory(title="选择要添加的文件夹")
        if not path:
            return
        path = os.path.normpath(path)
        if any(p == path for p, _ in self.folders):
            messagebox.showinfo("提示", "该文件夹已在列表中")
            return
        # 默认添加到常用分区；可通过面板上的 ⭐/📦 切换
        self.folders.append((path, True))
        self.save_config()
        self.refresh()

    def remove_folder(self, path: str):
        """从列表中移除"""
        if not messagebox.askyesno("确认", f"确定移除该文件夹吗？\n{path}"):
            return
        self.folders = [(p, c) for p, c in self.folders if p != path]
        self.save_config()
        self.refresh()

    # ============================================================
    # 拖拽排序
    # ============================================================

    def _drag_start(self, event, path: str):
        self._drag["active"] = True
        self._drag["path"] = path
        self._drag["start_y"] = event.y_root
        self._drag["src_idx"] = self._find_idx(path)

        row = self._rows.get(path)
        if row:
            row.config(bg=C["accent"])

    def _drag_move(self, event, path: str):
        if not self._drag["active"]:
            return
        target_idx = self._calc_drop_idx(event.y_root)
        self._show_indicator(target_idx)

    def _drag_end(self, event):
        if not self._drag["active"]:
            return

        src_idx = self._drag["src_idx"]
        target_idx = self._calc_drop_idx(event.y_root)

        row = self._rows.get(self._drag["path"])
        if row:
            row.config(bg=C["item_bg"])
        self._hide_indicator()

        if target_idx is not None and target_idx != src_idx:
            item = self.folders.pop(src_idx)
            if target_idx > src_idx:
                target_idx -= 1
            self.folders.insert(target_idx, item)
            self.save_config()

        self._drag["active"] = False
        self._drag["path"] = None
        self.refresh()

    def _find_idx(self, path: str) -> int:
        for i, (p, _) in enumerate(self.folders):
            if p == path:
                return i
        return -1

    def _calc_drop_idx(self, y_root: int) -> int:
        positions = []
        for i, (path, _) in enumerate(self.folders):
            w = self._rows.get(path)
            if w and w.winfo_viewable():
                y = w.winfo_rooty()
                h = w.winfo_height()
                positions.append((y + h // 2, i))

        if not positions:
            return 0

        positions.sort(key=lambda x: x[0])
        first_y = positions[0][0]
        last_y  = positions[-1][0]

        if y_root <= first_y:
            return 0
        if y_root >= last_y:
            return len(self.folders)

        for (y1, i1), (y2, i2) in zip(positions, positions[1:]):
            mid = (y1 + y2) // 2
            if y_root <= mid:
                return i1
        return positions[-1][1] + 1

    # ---------- 指示器 ----------

    def _show_indicator(self, target_idx: int):
        self._hide_indicator()
        if target_idx is None or target_idx < 0:
            return

        if not hasattr(self, "_indicator") or not self._indicator.winfo_exists():
            self._indicator = tk.Frame(self.body, bg=C["accent"], height=2)

        body_rooty = self.body.winfo_rooty()

        if target_idx < len(self.folders):
            w = self._rows.get(self.folders[target_idx][0])
            if w and w.winfo_exists():
                y_pos = w.winfo_rooty() - body_rooty
            else:
                return
        else:
            if self.folders:
                w = self._rows.get(self.folders[-1][0])
                if w and w.winfo_exists():
                    y_pos = w.winfo_rooty() + w.winfo_height() - body_rooty
                else:
                    return
            else:
                return

        self._indicator.place(x=5, y=y_pos, relwidth=1, width=-10)

    def _hide_indicator(self):
        if hasattr(self, "_indicator") and self._indicator.winfo_exists():
            self._indicator.place_forget()

    # ============================================================
    # 拖拽支持（Windows DragAcceptFiles API）
    # ============================================================

    def _setup_drag_drop(self):
        """设置窗口接受文件拖拽"""
        if sys.platform != "win32":
            return
        try:
            hwnd = self.root.winfo_id()
            # DragAcceptFiles: 启用拖拽接收
            ctypes.windll.user32.DragAcceptFiles(hwnd, True)
            # 挂钩窗口过程拦截 WM_DROPFILES
            self._pending_drops = []
            self._original_wndproc = None
            self._hook_wndproc(hwnd)
        except Exception as e:
            print(f"[QuickFolder] drag-drop setup failed: {e}")

    def _hook_wndproc(self, hwnd):
        """挂钩窗口过程，拦截 WM_DROPFILES"""
        try:
            GWL_WNDPROC = -4
            # 保存原始 WndProc
            self._original_wndproc = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_WNDPROC)

            # 新的 WndProc
            WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p)

            def new_wndproc(hwnd, msg, wparam, lparam):
                if msg == _WM_DROPFILES:
                    self._handle_drop_files(wparam)
                    return 0
                # 调用原始 WndProc
                return ctypes.windll.user32.CallWindowProcW(self._original_wndproc, hwnd, msg, wparam, lparam)

            self._wndproc_ref = WNDPROC(new_wndproc)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_WNDPROC, self._wndproc_ref)
        except Exception as e:
            print(f"[QuickFolder] wndproc hook failed: {e}")

    def _handle_drop_files(self, wparam):
        """处理 WM_DROPFILES: 从 HDROP 读取文件列表"""
        try:
            shell32 = ctypes.windll.shell32
            shell32.DragQueryFileW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_uint]
            shell32.DragQueryFileW.restype = ctypes.c_uint

            count = shell32.DragQueryFileW(wparam, -1, None, 0)
            files = []
            for i in range(count):
                buf = ctypes.create_unicode_buffer(_MAX_PATH)
                shell32.DragQueryFileW(wparam, i, buf, _MAX_PATH)
                files.append(buf.value)

            # 释放 HDROP
            ctypes.windll.shell32.DragFinish(wparam)

            if files:
                # 延迟到主线程处理
                self.root.after(0, lambda: self._process_dropped_files(files))
        except Exception as e:
            print(f"[QuickFolder] handle drop error: {e}")

    def _process_dropped_files(self, files):
        """在主线程中处理拖入的文件"""
        folders = [f for f in files if os.path.isdir(f)]
        archive_exts = ('.zip', '.rar', '.7z', '.tar', '.tar.gz', '.tgz', '.tar.bz2')
        archive_files = [f for f in files if os.path.isfile(f) and f.lower().endswith(archive_exts)]

        if folders:
            # 有文件夹 → 切换到合并 tab，添加文件夹
            self._show_tab("merge")
            for f in folders:
                self._merge_add_folder_path(f)
        elif archive_files:
            # 有压缩文件 → 切换到解压 tab
            self._show_tab("extract")
            for f in archive_files:
                self._extract_add_file(f)
            self._extract_refresh_list()
        else:
            # 普通文件 → 切换到解压 tab
            self._show_tab("extract")
            for f in files:
                if os.path.isfile(f):
                    self._extract_add_file(f)
            self._extract_refresh_list()

    # ============================================================
    # 文件解压 Tab 方法
    # ============================================================

    def _extract_add_files(self):
        """通过文件对话框添加压缩文件"""
        filetypes = [
            ("压缩文件", "*.zip *.rar *.7z *.tar *.tgz *.tar.gz *.tar.bz2"),
            ("ZIP 文件", "*.zip"),
            ("RAR 文件", "*.rar"),
            ("7Z 文件", "*.7z"),
            ("所有文件", "*.*"),
        ]
        paths = filedialog.askopenfilenames(title="选择压缩文件", filetypes=filetypes)
        for p in paths:
            self._extract_add_file(p)
        self._extract_refresh_list()

    def _extract_paste_files(self):
        """从剪贴板粘贴文件"""
        files = self._get_clipboard_files()
        if not files:
            messagebox.showinfo("提示", "剪贴板中没有文件数据")
            return
        for f in files:
            self._extract_add_file(f)
        self._extract_refresh_list()

    def _extract_add_file(self, path: str):
        """添加单个文件到列表（去重）"""
        path = os.path.normpath(path)
        if not os.path.isfile(path):
            return
        for p, _ in self._extract_files:
            if p == path:
                return
        name = os.path.basename(path)
        self._extract_files.append((path, name))

    def _extract_refresh_list(self):
        """刷新列表显示"""
        self._ext_listbox.delete(0, tk.END)
        for path, name in self._extract_files:
            size = self._format_size(os.path.getsize(path))
            self._ext_listbox.insert(tk.END, f"  {name}  ({size})")
        count = len(self._extract_files)
        self._ext_status.config(text=f"{count} 个文件" if count else "")

    def _format_size(self, size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.0f}{unit}" if unit == "B" else f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"

    def _extract_remove_selected(self):
        """移除选中文件"""
        sel = self._ext_listbox.curselection()
        if not sel:
            return
        for i in reversed(sel):
            self._extract_files.pop(i)
        self._extract_refresh_list()

    def _extract_clear(self):
        """清空文件列表"""
        self._extract_files.clear()
        self._extract_refresh_list()

    def _extract_show_menu(self, event):
        """右键菜单"""
        self._ext_menu.tk_popup(event.x_root, event.y_root)

    def _extractChooseDir(self):
        """选择解压输出目录"""
        d = filedialog.askdirectory(title="选择解压输出目录")
        if d:
            self._ext_outdir.set(d)

    def _extractRun(self):
        """执行解压"""
        if not self._extract_files:
            messagebox.showinfo("提示", "请先添加压缩文件")
            return

        outdir = self._ext_outdir.get().strip()
        if not outdir:
            messagebox.showwarning("提示", "请选择解压输出目录")
            return

        os.makedirs(outdir, exist_ok=True)

        # 进度对话框
        total = len(self._extract_files)
        dlg = tk.Toplevel(self.root)
        dlg.title("解压文件")
        dlg.geometry("420x160")
        dlg.attributes("-topmost", True)
        dlg.configure(bg=C["bg"])
        dlg.resizable(False, False)
        dlg.transient(self.root)
        dlg.grab_set()

        dlg.update_idletasks()
        x = dlg.winfo_screenwidth() // 2 - 210
        y = dlg.winfo_screenheight() // 2 - 80
        dlg.geometry(f"+{x}+{y}")

        lbl_file = tk.Label(dlg, text="", bg=C["bg"], fg=C["fg"],
                            font=("Segoe UI", 9),
                            anchor=tk.W, wraplength=400)
        lbl_file.pack(fill=tk.X, padx=15, pady=(12, 4))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Extract.Horizontal.TProgressbar",
                        troughcolor=C["item_bg"],
                        background=C["accent"],
                        thickness=8)
        prog = ttk.Progressbar(dlg, length=380, mode="determinate",
                               maximum=total, style="Extract.Horizontal.TProgressbar")
        prog.pack(pady=4, padx=15)

        lbl_count = tk.Label(dlg, text=f"0 / {total}", bg=C["bg"], fg=C["gray"],
                             font=("Segoe UI", 9))
        lbl_count.pack()

        cancelled = [False]

        def cancel():
            cancelled[0] = True

        btn_cancel = tk.Button(dlg, text="取消", command=cancel,
                               bg=C["btn_bg"], fg=C["fg"],
                               font=("Segoe UI", 9),
                               bd=0, padx=20, pady=4, cursor="hand2",
                               activebackground=C["danger"])
        btn_cancel.pack(pady=6)

        success = 0
        errors = 0

        for i, (fpath, fname) in enumerate(self._extract_files):
            if cancelled[0]:
                break

            lbl_file.config(text=f"正在解压: {fname}")
            prog["value"] = i
            lbl_count.config(text=f"{i+1} / {total}")
            dlg.update()

            try:
                self._do_extract(fpath, outdir)
                success += 1
            except Exception as e:
                errors += 1
                print(f"[Extract] error: {fname}: {e}")

        prog["value"] = total
        dlg.update()
        dlg.destroy()

        if cancelled[0]:
            msg = f"已解压 {success} 个文件，已取消"
        else:
            msg = f"解压完成：{success} 个成功"
            if errors:
                msg += f"，{errors} 个失败"

        messagebox.showinfo("完成", msg)

        # 解压成功后打开目录
        if success and not cancelled[0]:
            try:
                if sys.platform == "win32":
                    os.startfile(outdir)
            except Exception:
                pass

    def _do_extract(self, filepath: str, outdir: str):
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
            self._extract_with_7z(filepath, outdir)

        else:
            raise ValueError(f"不支持的格式: {os.path.basename(filepath)}")

    def _extract_with_7z(self, filepath: str, outdir: str):
        """用 7z 命令行解压 rar/7z 文件"""
        # 尝试常见 7z 路径
        candidates = [
            r"C:\Program Files\7-Zip\7z.exe",
            r"C:\Program Files (x86)\7-Zip\7z.exe",
            "7z",
        ]
        exe = None
        for c in candidates:
            if os.path.isfile(c):
                exe = c
                break

        if not exe:
            raise FileNotFoundError(
                "未找到 7-Zip，请安装 7-Zip 后重试\n"
                "下载地址: https://www.7-zip.org/"
            )

        result = subprocess.run(
            [exe, "x", filepath, f"-o{outdir}", "-y"],
            capture_output=True, text=True, timeout=300,
            startupinfo=self._hide_window(),
        )

        if result.returncode != 0:
            raise RuntimeError(f"7z 解压失败:\n{result.stderr[:200]}")

    # ============================================================
    # 设置 Tab
    # ============================================================

    def _build_settings_tab(self):
        scroll = tk.Frame(self.tab_settings, bg=C["bg"])
        scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # ---- 主题选择 ----
        sec_theme = tk.LabelFrame(scroll, text="🎨 主题", bg=C["bg"], fg=C["fg"],
                                   font=("Segoe UI", 10, "bold"), bd=0,
                                   labelanchor="w")
        sec_theme.pack(fill=tk.X, pady=(0, 12))

        self._theme_var = tk.StringVar(value=self._theme_key)
        self._theme_preview_labels = {}

        for key, theme in THEMES.items():
            row = tk.Frame(sec_theme, bg=C["bg"])
            row.pack(fill=tk.X, padx=4, pady=2)

            rb = tk.Radiobutton(row, text=theme["name"], variable=self._theme_var,
                                 value=key, command=self._on_theme_change,
                                 bg=C["bg"], fg=C["fg"],
                                 selectcolor=C["item_bg"],
                                 activebackground=C["bg"],
                                 activeforeground=C["fg"],
                                 font=("Segoe UI", 9),
                                 indicatoron=True)
            rb.pack(side=tk.LEFT)

            # 预览色块
            preview = tk.Frame(row, bg=C["bg"])
            preview.pack(side=tk.RIGHT, padx=4)

            for color_key, size in [("accent", 16), ("bg", 16), ("fg", 16)]:
                lbl = tk.Label(preview, text="  ", bg=theme[color_key], width=2, height=1,
                               relief=tk.SOLID, bd=1)
                lbl.pack(side=tk.LEFT, padx=1)
                self._theme_preview_labels[(key, color_key)] = lbl

        # ---- 关于 ----
        sec_about = tk.LabelFrame(scroll, text="ℹ️ 关于", bg=C["bg"], fg=C["fg"],
                                   font=("Segoe UI", 10, "bold"), bd=0,
                                   labelanchor="w")
        sec_about.pack(fill=tk.X, pady=(0, 12))

        tk.Label(sec_about, text="Quick Folder v1.0", bg=C["bg"], fg=C["gray"],
                 font=("Segoe UI", 9), anchor=tk.W).pack(fill=tk.X, padx=8, pady=2)
        tk.Label(sec_about, text="快捷文件夹 + 文件解压 工具", bg=C["bg"], fg=C["gray"],
                 font=("Segoe UI", 9), anchor=tk.W).pack(fill=tk.X, padx=8, pady=2)

    def _on_theme_change(self):
        """切换主题"""
        key = self._theme_var.get()
        if key == self._theme_key:
            return
        self._theme_key = key
        C.update(THEMES[key])
        self.save_config()
        # 重建 UI
        self._rebuild_ui()

    def _rebuild_ui(self):
        """主题切换后重建整个 UI"""
        # 清除所有子控件
        for w in self.main.winfo_children():
            w.destroy()

        # 重建
        self._tab_buttons = {}
        self._rows.clear()
        self._build_titlebar()

        self.tab_container = tk.Frame(self.main, bg=C["bg"])
        self.tab_container.pack(fill=tk.BOTH, expand=True)

        # 快捷文件夹 tab
        self.tab_folder = tk.Frame(self.tab_container, bg=C["bg"])
        folder_toolbar = tk.Frame(self.tab_folder, bg=C["bg"])
        folder_toolbar.pack(fill=tk.X, padx=6, pady=(6, 0))
        tk.Button(folder_toolbar, text="+ 添加",
                  command=self.add_folder,
                  bg=C["accent"], fg=C["fg"], bd=0,
                  padx=10, pady=2, cursor="hand2",
                  font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=2)
        self.body = tk.Frame(self.tab_folder, bg=C["bg"])
        self.body.pack(fill=tk.BOTH, expand=True, padx=2, pady=(4, 2))
        self._sec_common, self._inner_common = self._make_section(
            self.body, "⭐ 常用", C["gold"])
        self._sec_uncommon, self._inner_uncommon = self._make_section(
            self.body, "📦 非常用", C["gray"])
        self._empty = tk.Label(
            self.body,
            text="✨ 点击「+ 添加」按钮添加快捷文件夹",
            bg=C["bg"], fg=C["gray"],
            font=("Segoe UI", 10), pady=12,
        )

        # 文件夹合并 tab
        self.tab_merge = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_merge_tab()

        # 解压 tab
        self.tab_extract = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_extract_tab()

        # 设置 tab
        self.tab_settings = tk.Frame(self.tab_container, bg=C["bg"])
        self._build_settings_tab()

        # 注册 tabs
        self._tabs = {"folder": self.tab_folder, "merge": self.tab_merge, "extract": self.tab_extract, "settings": self.tab_settings}
        self._active_tab = None
        self._show_tab("folder")

        # 重新设置拖拽
        if sys.platform == "win32":
            self.root.after(100, self._setup_drag_drop)

    # ============================================================
    # 窗口拖动
    # ============================================================

    def _win_drag_start(self, event):
        self._win_x = event.x_root - self.root.winfo_x()
        self._win_y = event.y_root - self.root.winfo_y()

    def _win_drag_move(self, event):
        x = event.x_root - self._win_x
        y = event.y_root - self._win_y
        if sys.platform == "win32" and hasattr(self, "_hwnd"):
            try:
                SWP_NOSIZE = 0x0001
                SWP_NOZORDER = 0x0004
                SWP_NOACTIVATE = 0x0010
                SWP_NOREDRAW = 0x0008
                ctypes.windll.user32.SetWindowPos(
                    self._hwnd, 0, x, y, 0, 0,
                    SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_NOREDRAW
                )
                return
            except Exception:
                pass
        self.root.geometry(f"+{x}+{y}")

    # ============================================================
    # 窗口定位
    # ============================================================

    def _position_window(self):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        w = min(620, sw - 20)
        x = (sw - w) // 2
        self.root.geometry(f"{w}x200+{x}+0")

    # ---------- 无边框窗口（但保留任务栏图标） ----------

    def _apply_borderless(self):
        """通过 Win32 API 去掉窗口边框，但保留任务栏图标"""
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            self._hwnd = hwnd

            GWL_STYLE = -16
            GWL_EXSTYLE = -20

            # 移除标题栏、边框、可变大小框
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_STYLE)
            style &= ~0x00C00000  # WS_CAPTION
            style &= ~0x00800000  # WS_BORDER
            style &= ~0x00040000  # WS_THICKFRAME
            style &= ~0x00080000  # WS_SYSMENU
            style &= ~0x00020000  # WS_MINIMIZEBOX
            style &= ~0x00010000  # WS_MAXIMIZEBOX
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_STYLE, style)

            # 确保出现在任务栏
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= 0x00040000   # WS_EX_APPWINDOW
            ex_style &= ~0x00000080  # WS_EX_TOOLWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            # 刷新窗口
            SWP_FRAMECHANGED = 0x0020
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_NOACTIVATE = 0x0010
            ctypes.windll.user32.SetWindowPos(
                hwnd, 0, 0, 0, 0, 0,
                SWP_FRAMECHANGED | SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE,
            )

            # 重新设置置顶（样式变更后可能丢失）
            if self.topmost:
                self.root.attributes("-topmost", True)

            # 显示窗口（前面用 alpha=0 隐藏了，避免闪烁）
            self.root.attributes("-alpha", 1)
        except Exception as e:
            print(f"[QuickFolder] apply_borderless error: {e}")
            # 兜底：用传统的 overrideredirect
            self.root.overrideredirect(True)
            self.root.attributes("-alpha", 1)


# ============================================================
# 启动入口
# ============================================================
def main():
    root = tk.Tk()
    root.option_add("*Font", "{Microsoft YaHei UI} 9")
    root.bind("<Escape>", lambda e: root.quit())
    app = QuickFolderPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
