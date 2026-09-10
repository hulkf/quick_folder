#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Feishu Base clipboard synchronization helpers.

The module talks to Feishu through the locally configured ``lark-cli``.  This
keeps access tokens and application secrets out of Quick Folder's config file.
"""

from __future__ import annotations

import json
import os
import queue
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, urlparse

from PyQt5.QtCore import QThread, pyqtSignal


READ_ONLY_FIELD_TYPES = {
    "attachment",
    "auto_number",
    "created_at",
    "created_by",
    "formula",
    "lookup",
    "updated_at",
    "updated_by",
}
DEFAULT_LARK_PROFILE = "quick-folder"


class LarkCliError(RuntimeError):
    """A user-facing lark-cli failure."""


class LarkCliCancelled(LarkCliError):
    """Raised when a running lark-cli process is cancelled."""


def _decode_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip().lstrip("\ufeff")
    if not text:
        raise LarkCliError("飞书命令没有返回结果")
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LarkCliError(f"无法解析飞书命令返回结果: {text[:240]}") from exc
    if not isinstance(value, dict):
        raise LarkCliError("飞书命令返回了非预期的数据格式")
    return value


def _error_message(payload: Dict[str, Any]) -> str:
    error = payload.get("error") if isinstance(payload, dict) else None
    if not isinstance(error, dict):
        return str(payload)[:500]

    code = error.get("code")
    message = error.get("message") or "飞书请求失败"
    hint = error.get("hint")
    missing = error.get("missing_scopes")

    if code == 91403:
        message = "当前飞书身份无权访问该多维表格，请把文档授权给当前用户或飞书应用"
    elif code == 91402:
        message = "未找到该多维表格，请检查文档链接"

    parts = [message]
    if code is not None:
        parts.append(f"错误码: {code}")
    if missing:
        parts.append("缺少权限: " + ", ".join(str(item) for item in missing))
    if hint:
        parts.append(str(hint))
    return "；".join(parts)


def _first_item_list(payload: Any, keys: Iterable[str]) -> List[Dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    nested = payload.get("data")
    if nested is not payload:
        return _first_item_list(nested, keys)
    return []


def _normalize_items(
    payload: Any,
    collection_keys: Iterable[str],
    id_keys: Iterable[str],
    name_keys: Iterable[str],
) -> List[Dict[str, Any]]:
    result = []
    for raw in _first_item_list(payload, collection_keys):
        item_id = next((raw.get(key) for key in id_keys if raw.get(key)), None)
        name = next((raw.get(key) for key in name_keys if raw.get(key)), None)
        if item_id and name:
            item = dict(raw)
            item["id"] = str(item_id)
            item["name"] = str(name)
            result.append(item)
    return result


def field_type(field: Dict[str, Any]) -> str:
    raw_type = field.get("type")
    if isinstance(raw_type, dict):
        raw_type = raw_type.get("type") or raw_type.get("name")
    # Older bitable responses use 1 for a text field.
    if raw_type == 1:
        return "text"
    return str(raw_type or "").lower()


def is_clipboard_text_field(field: Dict[str, Any]) -> bool:
    """Only plain text storage fields can safely accept arbitrary clipboard text."""
    kind = field_type(field)
    return kind == "text" and kind not in READ_ONLY_FIELD_TYPES


class LarkCliClient:
    def __init__(
        self,
        executable: Optional[str] = None,
        identity: Optional[str] = None,
        cancel_event: Optional[threading.Event] = None,
        profile: Optional[str] = DEFAULT_LARK_PROFILE,
    ):
        self.executable = executable or self.find_executable()
        self.identity = identity
        self.cancel_event = cancel_event
        self.profile = profile

    @staticmethod
    def find_executable() -> str:
        candidates = ["lark-cli.cmd", "lark-cli.exe", "lark-cli"] if os.name == "nt" else ["lark-cli"]
        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise LarkCliError("未找到 lark-cli，请先安装并完成飞书应用配置")

    def _run(self, args: List[str], timeout: float = 35.0) -> Dict[str, Any]:
        env = os.environ.copy()
        env["LARKSUITE_CLI_NO_UPDATE_NOTIFIER"] = "1"
        env["LARKSUITE_CLI_NO_SKILLS_NOTIFIER"] = "1"
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
        try:
            process = subprocess.Popen(
                self._process_argv(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                creationflags=creationflags,
            )
        except OSError as exc:
            raise LarkCliError(f"无法启动 lark-cli: {exc}") from exc

        deadline = time.monotonic() + timeout
        cancelled = False
        while True:
            try:
                stdout, stderr = process.communicate(timeout=0.05)
                break
            except subprocess.TimeoutExpired:
                if self.cancel_event is not None and self.cancel_event.is_set():
                    # 取消请求：尽快杀掉子进程，不要再等剩下的超时时间
                    stdout, stderr = self._terminate_process(process)
                    cancelled = True
                    break
                if time.monotonic() >= deadline:
                    stdout, stderr = self._terminate_process(process)
                    break

        if cancelled:
            raise LarkCliCancelled("同步已停止")

        output = stdout if process.returncode == 0 else (stderr or stdout)
        payload = _decode_json(output)
        if process.returncode != 0 or payload.get("ok") is False:
            raise LarkCliError(_error_message(payload))
        return payload

    def _process_argv(self, args: List[str]) -> List[str]:
        """Bypass npm's Windows cmd shim so shell metacharacters stay inside argv."""
        cli_args = ["--profile", self.profile, *args] if self.profile else list(args)
        executable = Path(self.executable)
        if os.name == "nt" and executable.suffix.lower() == ".cmd":
            cli_script = executable.parent / "node_modules" / "@larksuite" / "cli" / "scripts" / "run.js"
            bundled_node = executable.parent / "node.exe"
            node = str(bundled_node) if bundled_node.exists() else (shutil.which("node.exe") or shutil.which("node"))
            if not cli_script.exists() or not node:
                raise LarkCliError("无法安全启动 lark-cli：未找到 npm 安装目录中的 Node 入口")
            return [node, str(cli_script), *cli_args]
        return [self.executable, *cli_args]

    @staticmethod
    def _terminate_process(process: subprocess.Popen):
        """杀掉子进程并返回 (stdout, stderr)，尽力避免阻塞调用方"""
        if process.poll() is not None:
            return process.communicate()
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            try:
                subprocess.run(
                    ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=creationflags,
                    timeout=3,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                process.kill()
        else:
            process.terminate()
        try:
            return process.communicate(timeout=1)
        except subprocess.TimeoutExpired:
            process.kill()
            try:
                return process.communicate(timeout=1)
            except subprocess.TimeoutExpired:
                return "", ""

    def detect_identity(self) -> str:
        payload = self._run(["auth", "status", "--json", "--verify"], timeout=20.0)
        identities = payload.get("identities", {})
        user = identities.get("user", {}) if isinstance(identities, dict) else {}
        if user.get("available") or user.get("status") == "ready":
            self.identity = "user"
        else:
            self.identity = None
            hint = user.get("hint") if isinstance(user, dict) else None
            message = "飞书 CLI 用户身份尚未登录；同步功能不会使用 Bot 身份"
            if hint:
                message += f"；{hint}"
            raise LarkCliError(message)
        return self.identity

    def _identity_args(self) -> List[str]:
        if self.identity != "user":
            self.detect_identity()
        return ["--as", "user", "--format", "json"]

    def resolve_url(self, document_url: str) -> Dict[str, str]:
        if not document_url.lower().startswith(("http://", "https://")):
            raise LarkCliError("请输入完整的飞书多维表格链接")
        payload = self._run(
            ["base", "+url-resolve", "--url", document_url, *self._identity_args()]
        )
        data = payload.get("data", {})
        base_token = data.get("base_token") or data.get("app_token")
        if not base_token:
            raise LarkCliError("该链接没有解析到多维表格，请粘贴 Base 或 Wiki 中的数据表链接")
        query_table_id = (parse_qs(urlparse(document_url).query).get("table") or [""])[0]
        return {
            "base_token": str(base_token),
            "table_id": str(data.get("table_id") or query_table_id),
        }

    def list_tables(self, base_token: str) -> List[Dict[str, Any]]:
        payload = self._run(
            ["base", "+table-list", "--base-token", base_token, "--limit", "100", *self._identity_args()]
        )
        return _normalize_items(payload.get("data", {}), ("items", "tables"), ("table_id", "id"), ("name", "table_name"))

    def list_fields(self, base_token: str, table_id: str) -> List[Dict[str, Any]]:
        payload = self._run(
            [
                "base", "+field-list", "--base-token", base_token,
                "--table-id", table_id, "--limit", "200", *self._identity_args(),
            ]
        )
        return _normalize_items(payload.get("data", {}), ("items", "fields"), ("field_id", "id"), ("name", "field_name"))

    def load_target(
        self,
        document_url: str,
        preferred_table_id: str = "",
        preferred_table_name: str = "",
    ) -> Dict[str, Any]:
        self.detect_identity()
        coordinates = self.resolve_url(document_url)
        tables = self.list_tables(coordinates["base_token"])
        if not tables:
            raise LarkCliError("该多维表格中没有可用的数据表")

        desired_ids = [coordinates.get("table_id"), preferred_table_id]
        selected = next((item for item in tables if item["id"] in desired_ids and item["id"]), None)
        if selected is None and preferred_table_name:
            selected = next((item for item in tables if item["name"] == preferred_table_name), None)
        selected = selected or tables[0]

        fields = self.list_fields(coordinates["base_token"], selected["id"])
        return {
            "identity": self.identity,
            "base_token": coordinates["base_token"],
            "tables": tables,
            "selected_table_id": selected["id"],
            "fields": fields,
        }

    def create_text_record(self, target: Dict[str, str], text: str) -> str:
        body = json.dumps(
            {"fields": [target["field_id"]], "rows": [[text]]},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload = self._run(
            [
                "base", "+record-batch-create",
                "--base-token", target["base_token"],
                "--table-id", target["table_id"],
                "--json", body,
                *self._identity_args(),
            ]
        )
        data = payload.get("data", {})
        record_ids = data.get("record_id_list") or data.get("record_ids") or []
        return str(record_ids[0]) if record_ids else ""


class FeishuTargetLoader(QThread):
    loaded = pyqtSignal(dict)
    failed = pyqtSignal(str)

    def __init__(self, document_url: str, table_id: str = "", table_name: str = ""):
        super().__init__()
        self.document_url = document_url
        self.table_id = table_id
        self.table_name = table_name
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        try:
            client = LarkCliClient(cancel_event=self._cancel_event)
            result = client.load_target(self.document_url, self.table_id, self.table_name)
            if not self._cancel_event.is_set():
                self.loaded.emit(result)
        except LarkCliCancelled:
            pass
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.failed.emit(str(exc))


class FeishuFieldLoader(QThread):
    loaded = pyqtSignal(str, list)
    failed = pyqtSignal(str)

    def __init__(self, base_token: str, table_id: str, identity: str):
        super().__init__()
        self.base_token = base_token
        self.table_id = table_id
        self.identity = identity
        self._cancel_event = threading.Event()

    def cancel(self):
        self._cancel_event.set()

    def run(self):
        try:
            client = LarkCliClient(identity=self.identity, cancel_event=self._cancel_event)
            fields = client.list_fields(self.base_token, self.table_id)
            if not self._cancel_event.is_set():
                self.loaded.emit(self.table_id, fields)
        except LarkCliCancelled:
            pass
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.failed.emit(str(exc))


class FeishuClipboardSyncWorker(QThread):
    synced = pyqtSignal(str, str)
    failed = pyqtSignal(str, str)

    def __init__(self, target: Dict[str, str]):
        super().__init__()
        self.target = dict(target)
        self._queue: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()

    def enqueue(self, text: str):
        if not self._stop_event.is_set():
            self._queue.put(text)

    def stop(self):
        self._stop_event.set()
        while True:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                break

    def run(self):
        try:
            client = LarkCliClient(identity=self.target.get("identity"), cancel_event=self._stop_event)
        except Exception as exc:
            self.failed.emit("", str(exc))
            return
        while not self._stop_event.is_set():
            try:
                text = self._queue.get(timeout=0.2)
            except queue.Empty:
                continue
            if self._stop_event.is_set():
                break
            try:
                record_id = client.create_text_record(self.target, text)
                self.synced.emit(text, record_id)
            except LarkCliCancelled:
                break
            except Exception as exc:
                self.failed.emit(text, str(exc))
