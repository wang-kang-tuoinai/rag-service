# 对话历史管理：保存 / 加载 / 列表 + 自动标题
# 存储拆分：meta/<id>.json 存元数据，messages/<id>.jsonl 存消息流
import json
import time
import uuid
from pathlib import Path

from generator import generate_title
from opentelemetry import trace

tracer = trace.get_tracer("rag-service")

CONV_DIR = Path("conversations")
META_DIR = CONV_DIR / "meta"
MSG_DIR = CONV_DIR / "messages"


def _ensure_dirs():
    META_DIR.mkdir(parents=True, exist_ok=True)
    MSG_DIR.mkdir(parents=True, exist_ok=True)


def _meta_path(conv_id: str) -> Path:
    return META_DIR / f"{conv_id}.json"


def _msg_path(conv_id: str) -> Path:
    return MSG_DIR / f"{conv_id}.jsonl"


# ---------- 创建 ----------

def new_conversation() -> dict:
    """新建一个空会话，返回元数据 dict"""
    now = int(time.time())
    return {
        "id": uuid.uuid4().hex[:16],
        "title": None,
        "created_at": now,
        "updated_at": now,
        "message_count": 0,
    }


# ---------- 元数据读写 ----------

def save_meta(meta: dict) -> dict:
    """保存会话元数据到 meta/<id>.json，刷新修改时间"""
    with tracer.start_as_current_span("save_meta") as span:
        span.set_attribute("rag.conversation_id", meta.get("id", ""))
        meta["updated_at"] = int(time.time())
        _ensure_dirs()
        _meta_path(meta["id"]).write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return meta


def load_meta(conv_id: str) -> dict | None:
    """读取单个会话的元数据，不存在或损坏返回 None"""
    with tracer.start_as_current_span("load_meta") as span:
        span.set_attribute("rag.conversation_id", conv_id)
        p = _meta_path(conv_id)
        if not p.exists():
            return None
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None


# ---------- 消息读写 ----------

def append_message(conv_id: str, role: str, content: str,
                   references: list[dict] | None = None) -> dict:
    """追加一条消息到 messages/<id>.jsonl，返回写入的消息 dict"""
    with tracer.start_as_current_span("append_message") as span:
        span.set_attribute("rag.conversation_id", conv_id)
        span.set_attribute("rag.message_role", role)
        _ensure_dirs()
        msg = {
            "role": role,
            "content": content,
            "timestamp": int(time.time()),
            "references": references or [],
        }
        with open(_msg_path(conv_id), "a", encoding="utf-8") as f:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        return msg


def load_all_messages(conv_id: str) -> list[dict]:
    """读取某个会话的全部消息（用于构造 LLM history），按时间正序"""
    p = _msg_path(conv_id)
    if not p.exists():
        return []
    messages = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                messages.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return messages


def list_messages(conv_id: str, limit: int = 20,
                  cursor: int | None = None) -> dict:
    """
    游标分页读取消息，按 timestamp 倒序（最新在前）。
    cursor 为上一页最后一条（最旧的那条）的 timestamp，
    下一页取 timestamp < cursor 的消息。
    """
    with tracer.start_as_current_span("list_messages") as span:
        span.set_attribute("rag.conversation_id", conv_id)
        all_msgs = load_all_messages(conv_id)
        # 按 timestamp 倒序
        all_msgs.sort(key=lambda m: m.get("timestamp", 0), reverse=True)

        if cursor is not None:
            all_msgs = [m for m in all_msgs if m.get("timestamp", 0) < cursor]

        page = all_msgs[: limit + 1]
        has_more = len(page) > limit
        items = page[:limit]
        next_cursor = items[-1]["timestamp"] if has_more and items else None

        return {
            "conversation_id": conv_id,
            "items": items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        }


# ---------- 会话列表 ----------

def list_conversations() -> list[dict]:
    """列出所有会话（仅元数据），按修改时间从新到旧排序"""
    if not META_DIR.exists():
        return []
    convs = []
    for p in META_DIR.glob("*.json"):
        try:
            convs.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    convs.sort(key=lambda c: c.get("updated_at", 0), reverse=True)
    return convs


# ---------- 保存流程（兼容 _ask 调用） ----------

def save_conversation_with_messages(
    meta: dict,
    user_content: str,
    assistant_content: str,
    references: list[dict] | None = None,
) -> dict:
    """
    完整的保存流程：追加 user + assistant 消息，更新元数据。
    首次保存时自动生成标题。
    """
    conv_id = meta["id"]

    # 追加消息
    append_message(conv_id, "user", user_content)
    append_message(conv_id, "assistant", assistant_content, references)

    # 更新消息计数
    meta["message_count"] = meta.get("message_count", 0) + 2

    # 首次生成标题
    if not meta.get("title") and user_content:
        try:
            meta["title"] = generate_title(user_content)
        except Exception:
            meta["title"] = user_content[:20]

    save_meta(meta)
    return meta


# ---------- 删除 ----------

def delete(conv_id: str) -> None:
    """删除会话的元数据和消息文件"""
    p = _meta_path(conv_id)
    if p.exists():
        p.unlink()
    p = _msg_path(conv_id)
    if p.exists():
        p.unlink()
