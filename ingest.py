"""运维知识入库：项目文档保存父文档，技术文档直接保存有长度预算的切片。"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import yaml

from markdown_splitter import format_chunk, split_long_section, split_sections

BASE = Path(__file__).resolve().parent
MODEL = "BAAI/bge-base-zh-v1.5"
COLLECTION = "ops_knowledge"
REQUIRED = ("id", "doc_type", "project", "service", "component", "deployment")
TECHNOLOGY_REQUIRED = ("doc_type", "component", "source_url")
RESERVED = {"doc_id", "chunk_id", "source", "title", "section", "chunk_index", "snapshot_id"}


def normalize_source_url(value: str) -> str:
    parts = urlsplit(value.strip())
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("source_url 必须是完整的 HTTP(S) 来源地址，且不能含认证信息")
    # 锚点不改变文章身份；保留路径大小写和查询参数，避免合并不同文章。
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path or "/", parts.query, ""))


def parse_document(path: Path, root: Path) -> dict:
    """读取并解析 Markdown 文档，校验 YAML front matter 元数据及正文合法性。"""
    text = path.read_text(encoding="utf-8-sig")
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", text, re.S)
    if not match:
        raise ValueError(f"{path}: 缺少 YAML front matter")
    metadata = yaml.safe_load(match.group(1))
    if not isinstance(metadata, dict):
        raise ValueError(f"{path}: metadata 必须是映射")
    required = TECHNOLOGY_REQUIRED if metadata.get("doc_type") == "technology" else REQUIRED
    for key in required:
        if not isinstance(metadata.get(key), str) or not metadata[key].strip():
            raise ValueError(f"{path}: {key} 必须是非空字符串")
    if metadata["doc_type"] not in {"architecture", "runbook", "technology"}:
        raise ValueError(f"{path}: 不支持的 doc_type")
    if metadata["doc_type"] == "technology":
        try:
            metadata["source_url"] = normalize_source_url(metadata["source_url"])
        except ValueError as exc:
            raise ValueError(f"{path}: {exc}") from exc
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


def make_chunks(doc, doc_id, title, sections):
    return [{
        "id": f"{doc_id}::section::{index}",
        "text": format_chunk(title, section, content),
        "metadata": {
            **{key: value for key, value in doc["metadata"].items() if key != "id"},
            "doc_id": doc_id, "source": doc["source"], "title": title,
            "section": section, "chunk_index": index,
        },
    } for index, (section, content) in enumerate(sections)]


def prepare_project_document(doc):
    title, sections = split_sections(doc["body"])
    parent = {**doc, "title": title}
    return parent, make_chunks(doc, doc["metadata"]["id"], title, sections)


def prepare_technology_document(doc, tokenizer, max_tokens, overlap_ratio=0.12):
    if tokenizer is None or max_tokens is None:
        raise ValueError("技术文档切分需要 tokenizer 和 max_tokens")
    title, sections = split_sections(doc["body"])
    doc_id = "technology-" + hashlib.sha256(doc["metadata"]["source_url"].encode("utf-8")).hexdigest()
    pieces = []
    for section, content in sections:
        pieces.extend(split_long_section(title, section, content, tokenizer, max_tokens, overlap_ratio))
    if not pieces:
        raise ValueError(f"{doc['source']}: 没有非空切片")
    return None, make_chunks(doc, doc_id, title, pieces)


def validate_lengths(chunks, tokenizer, max_tokens):
    oversized = [chunk["id"] for chunk in chunks
                 if len(tokenizer.encode(chunk["text"], add_special_tokens=True, truncation=False, verbose=False)) > max_tokens]
    if oversized:
        raise ValueError(f"切片超过模型 {max_tokens} token 上限，需细分后重试: {oversized}")

def prepare(root: Path, tokenizer=None, max_tokens=None, overlap_ratio=0.12) -> tuple[dict, list[dict]]:
    """全量汇总后再写库；技术文档不进入 parents，所有文档独立去重。"""
    parents, chunks, seen_doc_ids = {}, [], set()
    for path in sorted(root.rglob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        doc = parse_document(path, root)
        if doc["metadata"]["doc_type"] == "technology":
            parent, items = prepare_technology_document(doc, tokenizer, max_tokens, overlap_ratio)
        else:
            parent, items = prepare_project_document(doc)
        doc_id = items[0]["metadata"]["doc_id"]
        if doc_id in seen_doc_ids:
            raise ValueError(f"重复文档 id: {doc_id} ({path})")
        seen_doc_ids.add(doc_id)
        if parent is not None:
            parents[doc_id] = parent
        chunks.extend(items)
    if not chunks:
        raise ValueError(f"{root}: 没有可入库章节")
    if tokenizer is not None and max_tokens is not None:
        validate_lengths(chunks, tokenizer, max_tokens)
    return parents, chunks


def load_tokenizer():
    """只读取 tokenizer 与配置；dry-run 不加载模型权重。"""
    from huggingface_hub import hf_hub_download
    from transformers import AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(MODEL)
    config_path = hf_hub_download(MODEL, "sentence_bert_config.json")
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    max_tokens = min(int(config["max_seq_length"]), int(tokenizer.model_max_length))
    if max_tokens <= 0:
        raise ValueError("模型 token 上限必须为正数")
    return tokenizer, max_tokens


def sync_collection(collection, parents, chunks, embeddings, db_path, batch_size):
    """同一次全量同步涵盖所有类型；技术文档不关联快照。"""
    snapshot, snapshot_id = None, None
    if parents:
        payload = json.dumps(parents, ensure_ascii=False, sort_keys=True, indent=2)
        snapshot_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        snapshot_dir = db_path / "ops_knowledge_parents"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        snapshot = snapshot_dir / f"{snapshot_id}.json"
        if not snapshot.exists():
            temporary = snapshot.with_suffix(".tmp")
            temporary.write_text(payload, encoding="utf-8")
            temporary.replace(snapshot)
    ids = [c["id"] for c in chunks]
    # 小规模全量同步：写入成功后才删除已消失的章节，不触碰 go_docs。
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        collection.upsert(
            ids=[c["id"] for c in batch],
            documents=[c["text"] for c in batch],
            metadatas=[{**c["metadata"], **({"snapshot_id": snapshot_id}
                       if c["metadata"]["doc_type"] != "technology" else {})} for c in batch],
            embeddings=embeddings[start:start + batch_size],
        )
    stale = sorted(set(collection.get()["ids"]) - set(ids))
    for start in range(0, len(stale), batch_size):
        collection.delete(ids=stale[start:start + batch_size])
    return collection.count(), snapshot


def build_index(parents: dict, chunks: list[dict], db_path: Path):
    import chromadb
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(MODEL)
    validate_lengths(chunks, model.tokenizer, model.max_seq_length)
    embeddings = model.encode([chunk["text"] for chunk in chunks], normalize_embeddings=True).tolist()
    client = chromadb.PersistentClient(path=str(db_path))
    collection = client.get_or_create_collection(
        COLLECTION, metadata={"hnsw:space": "cosine", "embedding_model": MODEL}
    )
    return sync_collection(collection, parents, chunks, embeddings, db_path,
                           min(client.get_max_batch_size(), 128))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=BASE / "doc")
    parser.add_argument("--db-path", type=Path, default=BASE / "my_chroma_data")
    parser.add_argument("--dry-run", action="store_true", help="加载 tokenizer 校验切分，不加载模型权重或写索引")
    args = parser.parse_args()
    tokenizer, max_tokens = load_tokenizer()
    parents, chunks = prepare(args.root, tokenizer, max_tokens)
    doc_count = len({chunk["metadata"]["doc_id"] for chunk in chunks})
    print(f"文档 {doc_count} 篇，父文档 {len(parents)} 篇，切片 {len(chunks)} 个；token 上限 {max_tokens}")
    if args.dry_run:
        print(json.dumps(chunks[0], ensure_ascii=False, indent=2))
        return
    count, snapshot = build_index(parents, chunks, args.db_path)
    print(f"{COLLECTION} 入库完成：{count} 个切片；父文档：{snapshot or '无'}")


if __name__ == "__main__":
    main()
