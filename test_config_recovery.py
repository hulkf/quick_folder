import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from PyQt5.QtWidgets import QApplication, QMessageBox
import main_pyqt5
from config_store import read_config, write_config


class ConfigRecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "config.json"
        self.config_patch = patch.object(main_pyqt5, "CONFIG_FILE", self.path)
        self.config_patch.start()
        self.addCleanup(self.config_patch.stop)
        self.warning = patch.object(QMessageBox, "warning").start()
        self.addCleanup(patch.stopall)

    def roundtrip(self):
        panel = main_pyqt5.QuickFolderPanel()
        try:
            self.app.processEvents()
        finally:
            panel.close()
            self.app.processEvents()

    def test_bom_and_missing_folder_preserve_settings(self):
        missing = str(Path(self.temp.name) / "offline-folder")
        config = {"folders": [[missing, True]], "theme": "dark_blue",
                  "folder_add_prefix": "example-",
                  "feishu_sync": {"document_url": "https://example.feishu.cn/base/base1",
                                  "base_token": "base1", "table_id": "tbl1"}}
        self.path.write_text(json.dumps(config), encoding="utf-8-sig")
        self.roundtrip()
        result = read_config(self.path)
        for key in ("folders", "theme", "folder_add_prefix"):
            self.assertEqual(result[key], config[key])
        self.assertEqual(result["feishu_sync"]["base_token"], "base1")
        self.assertEqual(read_config(self.path.with_suffix(".json.bak")), config)

    def test_invalid_config_not_overwritten_on_close(self):
        for contents in (b'{"folders":', b'[]', b'{"folders": [null]}'):
            with self.subTest(contents=contents):
                self.path.write_bytes(contents)
                self.roundtrip()
                self.assertEqual(self.path.read_bytes(), contents)
        self.assertEqual(self.warning.call_count, 3)

    def test_failed_replace_preserves_original_and_backup(self):
        original = {"folders": [], "theme": "dark_blue"}
        self.path.write_text(json.dumps(original), encoding="utf-8")
        real_replace = os.replace

        def fail_target(src, dst):
            if Path(dst) == self.path:
                raise PermissionError("example failure")
            return real_replace(src, dst)

        with patch("config_store.os.replace", side_effect=fail_target):
            with self.assertRaises(PermissionError):
                write_config(self.path, {"folders": [], "theme": "dark_teal"})
        self.assertEqual(read_config(self.path), original)
        self.assertEqual(read_config(self.path.with_suffix(".json.bak")), original)
        self.assertEqual(list(self.path.parent.glob("*.tmp")), [])

    def test_corrupt_file_does_not_replace_good_backup(self):
        backup = self.path.with_suffix(".json.bak")
        backup.write_text('{"theme":"dark_blue"}', encoding="utf-8")
        self.path.write_bytes(b'{')
        with self.assertRaises(ValueError):
            write_config(self.path, {})
        self.assertEqual(read_config(backup), {"theme": "dark_blue"})
        self.assertEqual(self.path.read_bytes(), b'{')


if __name__ == "__main__":
    unittest.main()
