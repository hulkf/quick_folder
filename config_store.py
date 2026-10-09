"""本地配置：兼容 BOM、原子写入，并保留上一份有效配置。"""
import json
import os
import tempfile
from pathlib import Path


def read_config(path):
    config = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("配置根节点必须是对象")
    for key in ("folders", "launch_items"):
        if key in config and not isinstance(config[key], list):
            raise ValueError(f"配置 {key} 必须是列表")
    for folder in config.get("folders", []):
        if (not isinstance(folder, (list, tuple)) or len(folder) != 2
                or not isinstance(folder[0], str) or not folder[0]
                or not isinstance(folder[1], bool)):
            raise ValueError("文件夹配置格式无效")
    return config


def atomic_write(path, data):
    path = Path(path)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def write_config(path, config):
    path = Path(path)
    data = json.dumps(config, ensure_ascii=False, indent=2).encode("utf-8")
    if path.exists():
        # 校验失败直接停止，不能用空配置覆盖损坏文件或污染备份。
        read_config(path)
        atomic_write(path.with_name(path.name + ".bak"), path.read_bytes())
    atomic_write(path, data)
