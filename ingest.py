"""运维知识入库：章节向量 + YAML metadata + 父文档快照。"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path

import yaml

BASE = Path(__file__).resolve().parent
MODEL = "BAAI/bge-base-zh-v1.5"
COLLECTION = "ops_knowledge"
REQUIRED = ("id", "doc_type", "project", "service", "component", "deployment")
RESERVED = {"doc_id", "chunk_id", "source", "title", "section", "chunk_index", "snapshot_id"}


def parse_document(path: Path, root: Path) -> dict:
    """读取并解析 Markdown 文档，校验 YAML front matter 元数据及正文合法性。"""
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not match:
        raise ValueError(f"{path}: 缺少 YAML front matter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: metadata 必须是映射")
    for key in REQUIRED:
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"{path}: {key} 必须是非空字符串")
    if metadata["doc_type"] not in {"architecture", "runbook"}:
        raise ValueError(f"{path}: 不支持的 doc_type")
    for key, value in metadata.items():
        if not isinstance(key, str) or key in RESERVED:
            raise ValueError(f"{path}: metadata 键非法或与保留字段冲突: {key}")
        if not isinstance(value, (str, int, float, bool)) or (
            isinstance(value, float) and not math.isfinite(value)
        ):
            raise ValueError(f"{path}: {key} 请使用字符串/数字/布尔值，日期请加引号")
    body = text[match.end():].strip()
    if not body:
        raise ValueError(f"{path}: 正文为空")
    return {"metadata": metadata, "body": body, "source": path.relative_to(root).as_posix()}


def split_sections(body: str) -> tuple[str, list[tuple[str, str]]]:
    """按 H2 拆分，保留 H3、列表、表格；代码围栏中的标题不是分隔符。"""
    title = ""
    section = "概述"
    lines = []
    sections = []
    fence_char, fence_size = "", 0

    def flush():
        content = "\n".join(lines).strip()
        if content:
            sections.append((section, content))

    for line in body.splitlines():
        # 处理代码块，防止代码块里的#被错误识别
        fence = re.match(r"^ {0,3}(`{3,}|~{3,})(.*)$", line)
        if fence_char:
            lines.append(line)
            if fence and fence.group(1)[0] == fence_char and len(fence.group(1)) >= fence_size and not fence.group(2).strip():
                fence_char = ""
            continue
        if fence:
            fence_char, fence_size = fence.group(1)[0], len(fence.group(1))
            lines.append(line)
            continue
        heading = re.match(r"^ {0,3}(#{1,2})\s+(.+?)\s*#*\s*$", line)
        if heading and heading.group(1) == "#" and not title:
            title = heading.group(2)
            continue
        if heading and heading.group(1) == "##":
            flush()
            section = heading.group(2)
            lines = []
        else:
            lines.append(line)
    flush()
    if not title or not sections:
        raise ValueError("文档必须有一级标题和非空章节正文")
    return title, sections

# TODO doc_id和id字段重复
def prepare(root: Path) -> tuple[dict, list[dict]]:
    """遍历目录下所有 Markdown 文档，执行解析、去重校验、章节切分并组装向量库切片数据。"""
    parents, chunks = {}, []
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        doc = parse_document(path, root)
        doc_id = doc["metadata"]["id"]
        if doc_id in parents:
            raise ValueError(f"重复文档 id: {doc_id}")
        title, sections = split_sections(doc["body"])
        doc["title"] = title
        parents[doc_id] = doc
        for index, (section, content) in enumerate(sections):
            chunk_id = f"{doc_id}::section::{index}"
            chunks.append({
                "id": chunk_id,
                "text": f"文档标题：{title}\n章节标题：{section}\n\n{content}",
                "metadata": {
                    **doc["metadata"], "doc_id": doc_id, "chunk_id": chunk_id,
                    "source": doc["source"], "title": title, "section": section,
                    "chunk_index": index,
                },
            })
    if not chunks:
        raise ValueError(f"{root}: 没有可入库章节")
    return parents, chunks


def build_index(parents: dict, chunks: list[dict], db_path: Path):
    # 校验完成后才加载模型；禁止静默截断章节。
    import chromadb
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL)
    texts = [c["text"] for c in chunks]
    sizes = [len(model.tokenizer.encode(text, add_special_tokens=True, truncation=False)) for text in texts]
    oversized = [chunks[i]["id"] for i, n in enumerate(sizes) if n > model.max_seq_length]
    if oversized:
        raise ValueError(f"章节超过模型 {model.max_seq_length} token 上限，需细分后重试: {oversized}")
    embeddings = model.encode(texts, normalize_embeddings=True).tolist()

    # 内容寻址快照：每条向量指向本次正文，而非后续修改过的 Markdown。
    payload = json.dumps(parents, ensure_ascii=False, sort_keys=True, indent=2)
    snapshot_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    snapshot_dir = db_path / "ops_knowledge_parents"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = snapshot_dir / f"{snapshot_id}.json"
    if not snapshot.exists():
        temporary = snapshot.with_suffix(".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(snapshot)

    client = chromadb.PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine", "embedding_model": MODEL}
    )
    ids = [c["id"] for c in chunks]
    # 小规模全量同步：写入成功后才删除已消失的章节，不触碰 go_docs。
    batch_size = min(client.get_max_batch_size(), 128)
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{**c["metadata"], "snapshot_id": snapshot_id} for c in batch],
            embeddings=embeddings[start:start + batch_size],
        )
    stale = sorted(set(collection.get()["ids"]) - set(ids))
    for start in range(0, len(stale), batch_size):
        collection.delete(ids=stale[start:start + batch_size])
    return collection.count(), snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=BASE / "doc")
    parser.add_argument("--db-path", type=Path, default=BASE / "my_chroma_data")
    parser.add_argument("--dry-run", action="store_true", help="只校验解析和切分，不加载模型或写索引")
    args = parser.parse_args()
    parents, chunks = prepare(args.root)
    print(f"文档 {len(parents)} 篇，章节 {len(chunks)} 个")
    if args.dry_run:
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2))
        return
    count, snapshot = build_index(parents, chunks, args.db_path)
    print(f"{COLLECTION} 入库完成：{count} 个章节；父文档：{snapshot}")


if __name__ == "__main__":
    main()
