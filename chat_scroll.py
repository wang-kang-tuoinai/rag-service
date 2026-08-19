# 对话历史管理：保存 / 加载 / 列表 + 自动标题
import json
import time
import uuid
from pathlib import Path

from generator import generate_title
from opentelemetry import trace

tracer = trace.get_tracer("rag-service")

CONV_DIR = Path("conversations")


def new_conversation() -> dict:
    """新建一个空会话对象"""
    now = int(time.time())
    return {
        "id": uuid.uuid4().hex[:16],
        "title": None,
        "messages": [],
        "created_at": now,
        "updated_at": now,
    }


def save(conv: dict) -> dict:
    """保存会话到 conversations/<id>.json，刷新修改时间，首次保存时生成标题"""
    with tracer.start_as_current_span("save_conversation") as span:
        span.set_attribute("rag.conversation_id", conv.get("id", ""))
        conv["updated_at"] = int(time.time())
        if not conv.get("title") and conv.get("messages"):
            # 从对话历史里面取出用户发送的第一条消息
            first_user = next((m["content"] for m in conv["messages"] if m["role"] == "user"), "")
            if first_user:
                try:
                    conv["title"] = generate_title(first_user)
                except Exception:
                    conv["title"] = first_user[:20]
        CONV_DIR.mkdir(exist_ok=True)
        _path(conv["id"]).write_text(
            json.dumps(conv, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return conv


def load(conv_id: str) -> dict | None:
    """读取单个会话，不存在或损坏返回 None"""
    with tracer.start_as_current_span("load_conversation") as span:
        span.set_attribute("rag.conversation_id", conv_id)
        p = _path(conv_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


def list_conversations() -> list[dict]:
    """列出所有会话，按修改时间从新到旧排序"""
    if not CONV_DIR.exists():
        return []
    convs = []
    for p in CONV_DIR.glob("*.json"):
        try:
            convs.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    convs.sort(key=lambda c: c.get("updated_at", 0), reverse=True)
    return convs


def delete(conv_id: str) -> None:
    """删除会话文件"""
    p = _path(conv_id)
    if p.exists():
        p.unlink()


def _path(conv_id: str) -> Path:
    return CONV_DIR / f"{conv_id}.json"
