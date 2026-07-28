import json
import os
import unittest

from feishu_sync import (
    LarkCliClient,
    _error_message,
    _normalize_items,
    field_type,
    is_clipboard_text_field,
)


class FeishuSyncHelpersTest(unittest.TestCase):
    @unittest.skipUnless(os.name == "nt", "Windows npm shim regression")
    def test_npm_cmd_shim_is_replaced_with_node_entrypoint(self):
        url = "https://example.feishu.cn/wiki/token?table=tbl1&view=vew1"
        client = LarkCliClient(identity="bot")
        argv = client._process_argv(["base", "+url-resolve", "--url", url])
        self.assertFalse(argv[0].lower().endswith(".cmd"))
        self.assertTrue(any(item.replace("\\", "/").endswith("/@larksuite/cli/scripts/run.js") for item in argv))
        self.assertEqual(argv[-1], url)

    def test_client_pins_quick_folder_profile(self):
        client = LarkCliClient(executable="lark-cli", identity="user")
        argv = client._process_argv(["auth", "status", "--json"])
        self.assertEqual(argv[1:3], ["--profile", "quick-folder"])

    def test_normalizes_table_and_field_items(self):
        payload = {"items": [{"table_id": "tbl1", "name": "数据表"}]}
        self.assertEqual(
            _normalize_items(payload, ("items",), ("table_id",), ("name",)),
            [{"table_id": "tbl1", "name": "数据表", "id": "tbl1"}],
        )

    def test_only_text_storage_fields_accept_arbitrary_clipboard_text(self):
        self.assertTrue(is_clipboard_text_field({"type": "text"}))
        self.assertTrue(is_clipboard_text_field({"type": 1}))
        self.assertFalse(is_clipboard_text_field({"type": "number"}))
        self.assertFalse(is_clipboard_text_field({"type": "formula"}))
        self.assertEqual(field_type({"type": {"type": "text"}}), "text")

    def test_permission_error_has_actionable_message(self):
        message = _error_message({"error": {"code": 91403, "message": "forbidden"}})
        self.assertIn("无权访问", message)
        self.assertIn("91403", message)

    def test_wiki_url_keeps_table_query_when_cli_omits_it(self):
        client = LarkCliClient.__new__(LarkCliClient)
        client.identity = "user"
        client._run = lambda args, timeout=35.0: {
            "ok": True,
            "data": {"base_token": "base1", "resource_type": "bitable"},
        }
        result = client.resolve_url(
            "https://example.feishu.cn/wiki/token?table=tblWikiTarget&view=vew1"
        )
        self.assertEqual(result, {"base_token": "base1", "table_id": "tblWikiTarget"})

    def test_identity_detection_never_falls_back_to_bot(self):
        client = LarkCliClient.__new__(LarkCliClient)
        client.identity = None
        client._run = lambda args, timeout=35.0: {
            "identities": {
                "user": {"status": "missing", "available": False},
                "bot": {"status": "ready", "available": True},
            }
        }
        with self.assertRaisesRegex(Exception, "用户身份"):
            client.detect_identity()

    def test_record_payload_keeps_unicode_and_uses_field_id(self):
        client = LarkCliClient.__new__(LarkCliClient)
        client.identity = "user"
        captured = {}

        def fake_run(args, timeout=35.0):
            captured["args"] = args
            return {"ok": True, "data": {"record_id_list": ["rec1"]}}

        client._run = fake_run
        record_id = client.create_text_record(
            {"base_token": "base1", "table_id": "tbl1", "field_id": "fld1", "identity": "user"},
            "剪贴板内容",
        )
        self.assertEqual(record_id, "rec1")
        body = captured["args"][captured["args"].index("--json") + 1]
        self.assertEqual(json.loads(body), {"fields": ["fld1"], "rows": [["剪贴板内容"]]})


if __name__ == "__main__":
    unittest.main()
