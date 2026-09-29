import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PyQt5.QtCore import QPoint, Qt, QMimeData, QUrl
from PyQt5.QtGui import QDragLeaveEvent, QDragMoveEvent, QDropEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QPushButton

import main_pyqt5


class FolderExpansionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.parent = self.root / "parent"
        self.child = self.parent / "child"
        self.grandchild = self.child / "grandchild"
        self.grandchild.mkdir(parents=True)
        (self.parent / "visible.txt").write_text("test", encoding="utf-8")
        self.config_patch = patch.object(main_pyqt5, "CONFIG_FILE", self.root / "config.json")
        self.config_patch.start()
        self.panel = main_pyqt5.QuickFolderPanel()
        self.panel.folders = [{"path": str(self.parent), "display_name": "parent", "is_common": True}]
        self.panel.refresh_folder_list()
        self.panel.show()
        self.app.processEvents()

    def tearDown(self):
        self.panel.launch_timer.stop()
        self.panel.close()
        self.config_patch.stop()
        self.temp.cleanup()

    def test_expand_only_directories_one_level_and_promote(self):
        first_group = self.panel.common_list.itemWidget(self.panel.common_list.item(0))
        expand = next(button for button in first_group.main_row.findChildren(QPushButton)
                      if button.toolTip() == "展开下一级文件夹")
        expand.click()
        group = self.panel.common_list.itemWidget(self.panel.common_list.item(0))
        self.assertEqual([row.path for row in group.children], [str(self.child)])
        self.assertEqual(group.folder_at(QPoint(100, 10)), str(self.parent))
        self.assertEqual(group.folder_at(QPoint(100, 55)), str(self.child))
        self.assertFalse(group.children[0].findChildren(main_pyqt5.FolderGroupWidget))

        QTest.mouseClick(group.children[0].sec_icon, Qt.LeftButton)
        self.assertEqual(len(self.panel.folders), 2)
        parent_group = self.panel.common_list.itemWidget(self.panel.common_list.item(0))
        self.assertEqual([row.path for row in parent_group.children], [str(self.child)])
        self.assertEqual(parent_group.children[0].sec_icon.text(), "⬇")
        self.panel.toggle_folder_expanded(str(self.child))
        promoted = self.panel.common_list.itemWidget(self.panel.common_list.item(1))
        self.assertEqual([row.path for row in promoted.children], [str(self.grandchild)])

    def test_drop_file_on_child_moves_it_without_overwriting(self):
        self.panel.toggle_folder_expanded(str(self.parent))
        source = self.root / "source.txt"
        source.write_text("source", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        drop_point = QPoint(100, self.panel.common_list.visualItemRect(self.panel.common_list.item(0)).top() + 55)
        self.assertEqual(self.panel.common_list.folder_at(drop_point), str(self.child))
        target_row = self.panel.common_list.row_at(drop_point)
        original_callback = self.panel.common_list._file_drop_callback

        def move_with_visible_target(paths, target):
            self.assertTrue(target_row._drop_highlight)
            original_callback(paths, target)

        self.panel.common_list.set_file_drop_callback(move_with_visible_target)
        event = QDropEvent(drop_point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
        with patch.object(QMessageBox, "information"):
            self.panel.common_list.dropEvent(event)
        self.assertFalse(target_row._drop_highlight)
        self.assertFalse(source.exists())
        self.assertEqual((self.child / "source.txt").read_text(encoding="utf-8"), "source")
        source.write_text("second", encoding="utf-8")
        event = QDropEvent(drop_point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
        with patch.object(QMessageBox, "information"):
            self.panel.common_list.dropEvent(event)
        self.assertTrue(source.exists())
        self.assertEqual((self.child / "source.txt").read_text(encoding="utf-8"), "source")

    def test_file_drag_highlights_only_the_current_folder_row(self):
        self.panel.toggle_folder_expanded(str(self.parent))
        folder_list = self.panel.common_list
        group = folder_list.itemWidget(folder_list.item(0))
        self.assertEqual(group.main_row.styleSheet(), "")
        self.assertEqual(group.children[0].styleSheet(), "")
        self.assertFalse(group.main_row.testAttribute(Qt.WA_StyledBackground))
        self.assertIn("item:selected", folder_list.styleSheet())
        self.assertIn("background: transparent", folder_list.styleSheet())
        source = self.root / "hover.txt"
        source.write_text("hover", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        top = folder_list.visualItemRect(folder_list.item(0)).top()

        for y, highlighted in [(top + 10, group.main_row), (top + 55, group.children[0])]:
            event = QDragMoveEvent(QPoint(100, y), Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier)
            folder_list.dragMoveEvent(event)
            self.assertTrue(highlighted._drop_highlight)
            self.assertTrue(highlighted.testAttribute(Qt.WA_StyledBackground))
            self.assertIn("border: 2px solid", highlighted.styleSheet())
            other = group.children[0] if highlighted is group.main_row else group.main_row
            self.assertFalse(other._drop_highlight)
            self.assertEqual(other.styleSheet(), "")

        folder_list.dragLeaveEvent(QDragLeaveEvent())
        self.assertFalse(group.main_row._drop_highlight)
        self.assertFalse(group.children[0]._drop_highlight)
        self.assertEqual(group.main_row.styleSheet(), "")
        self.assertEqual(group.children[0].styleSheet(), "")
        self.assertFalse(group.main_row.testAttribute(Qt.WA_StyledBackground))
        self.assertFalse(group.children[0].testAttribute(Qt.WA_StyledBackground))

    def test_drop_file_on_top_level_row(self):
        source = self.root / "top.txt"
        source.write_text("top", encoding="utf-8")
        mime = QMimeData()
        mime.setUrls([QUrl.fromLocalFile(str(source))])
        point = QPoint(100, self.panel.common_list.visualItemRect(self.panel.common_list.item(0)).top() + 10)
        self.assertEqual(self.panel.common_list.folder_at(point), str(self.parent))
        with patch.object(QMessageBox, "information"):
            self.panel.common_list.dropEvent(QDropEvent(point, Qt.MoveAction, mime, Qt.LeftButton, Qt.NoModifier))
        self.assertEqual((self.parent / "top.txt").read_text(encoding="utf-8"), "top")

    def test_managed_folder_refresh_and_saved_setting(self):
        self.assertEqual(self.panel.managed_folder_path, "")
        managed = self.root / "managed"
        managed.mkdir()
        (managed / "today-a").mkdir()
        (managed / "today-b").mkdir()
        (managed / "today-a" / "nested").mkdir()
        (managed / "file.txt").write_text("not a folder", encoding="utf-8")

        with patch.object(QFileDialog, "getExistingDirectory", return_value=str(managed)):
            self.panel.select_managed_folder()
        self.assertEqual(self.panel.managed_folder_entry.text(), str(managed))
        refresh_button = next(button for button in self.panel.folder_tab.findChildren(QPushButton)
                              if button.text() == "🔄 刷新管理文件夹")
        with patch.object(QMessageBox, "information"):
            refresh_button.click()
            self.panel.refresh_managed_folder()
        self.assertEqual({f["display_name"] for f in self.panel.folders[:2]}, {"today-a", "today-b"})
        self.assertEqual(len(self.panel.folders), 3)
        self.assertEqual(self.panel.folders[2]["path"], str(self.parent))

        reopened = main_pyqt5.QuickFolderPanel()
        try:
            self.assertEqual(reopened.managed_folder_path, str(managed))
            self.assertEqual(reopened.managed_folder_entry.text(), str(managed))
        finally:
            reopened.launch_timer.stop()
            reopened.close()

    def test_managed_folder_ignores_other_dates(self):
        managed = self.root / "managed"
        managed.mkdir()
        (managed / "created-today").mkdir()
        self.panel.managed_folder_path = str(managed)

        class Tomorrow(datetime):
            @classmethod
            def now(cls, tz=None):
                return super().now(tz) + timedelta(days=1)

        with patch.object(main_pyqt5, "datetime", Tomorrow), patch.object(QMessageBox, "information"):
            self.panel.refresh_managed_folder()
        self.assertEqual(len(self.panel.folders), 1)

if __name__ == "__main__":
    unittest.main()
