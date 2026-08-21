"""
离线迁移脚本：将旧格式 conversations/<id>.json（元数据+消息混存）
转换为新格式 conversations/meta/<id>.json + conversations/messages/<id>.jsonl

使用方式：
    cd rag-service
    python migrate_conversations.py

幂等：已迁移的对话（meta/ 中已存在）会跳过。
"""
import json
import sys
from pathlib import Path

CONV_DIR = Path("conversations")
META_DIR = CONV_DIR / "meta"
MSG_DIR = CONV_DIR / "messages"


def migrate():
    if not CONV_DIR.exists():
        print("conversations/ 目录不存在，无需迁移")
        return

    # 只处理 conversations/ 根目录下的 .json 文件（旧格式）
    legacy_files = [
        p for p in CONV_DIR.glob("*.json")
        if p.is_file()  # 排除目录
    ]

    if not legacy_files:
        print("没有找到需要迁移的旧格式文件")
        return

    META_DIR.mkdir(parents=True, exist_ok=True)
    MSG_DIR.mkdir(parents=True, exist_ok=True)

    migrated = 0
    skipped = 0
    failed = 0

    for legacy_path in legacy_files:
        conv_id = legacy_path.stem
        meta_path = META_DIR / f"{conv_id}.json"
        msg_path = MSG_DIR / f"{conv_id}.jsonl"

        # 幂等：已迁移则跳过
        if meta_path.exists():
            print(f"  [跳过] {conv_id} — meta 已存在")
            skipped += 1
            continue

        try:
            conv = json.loads(legacy_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            print(f"  [失败] {conv_id} — 读取失败: {e}")
            failed += 1
            continue

        # 提取元数据
        messages = conv.get("messages", [])
        meta = {
            "id": conv["id"],
            "title": conv.get("title"),
            "created_at": conv.get("created_at", 0),
            "updated_at": conv.get("updated_at", 0),
            "message_count": len(messages),
        }

        # 为旧消息生成时间戳：根据 created_at 和 updated_at 均匀插值
        created = conv.get("created_at", 0)
        updated = conv.get("updated_at", 0)
        n = len(messages)
        if n > 1 and updated > created:
            step = (updated - created) / (n - 1)
        else:
            step = 0

        # 写入 JSONL
        with open(msg_path, "w", encoding="utf-8") as f:
            for i, msg in enumerate(messages):
                enriched = {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": int(created + i * step),
                    "references": msg.get("references", []),
                }
                f.write(json.dumps(enriched, ensure_ascii=False) + "\n")

        # 写入 meta
        meta_path.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print(f"  [完成] {conv_id} — {n} 条消息")
        migrated += 1

    print(f"\n迁移完成：成功 {migrated}，跳过 {skipped}，失败 {failed}")

    if migrated > 0:
        print(
            "\n旧文件保留在 conversations/ 根目录下，确认无误后可手动删除：\n"
            "  del conversations\\*.json       (Windows)\n"
            "  rm conversations/*.json         (Linux/Mac)"
        )


if __name__ == "__main__":
    migrate()
