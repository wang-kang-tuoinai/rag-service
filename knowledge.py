"""章节召回与精排，再按文档最高章节分数返回父文档快照。"""
import hashlib
import json
import math
import re
from pathlib import Path

COLLECTION = "ops_knowledge"
INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class KnowledgeUnavailable(RuntimeError):
    """索引与快照缺失或不一致，不能作为成功空结果返回。"""


def load_parent(directory: Path, snapshot_id: str, doc_id: str, cache: dict) -> dict:
    if not re.fullmatch(r"[0-9a-f]{64}", snapshot_id):
        raise KnowledgeUnavailable("索引 snapshot_id 非法，请重新构建运维知识索引")
    if snapshot_id not in cache:
        try:
            payload = (directory / f"{snapshot_id}.json").read_bytes()
            if hashlib.sha256(payload).hexdigest() != snapshot_id:
                raise ValueError("快照哈希不匹配")
            cache[snapshot_id] = json.loads(payload)
        except (OSError, ValueError) as exc:
            raise KnowledgeUnavailable("父文档快照缺失或损坏，请重新构建运维知识索引") from exc
    parents = cache[snapshot_id]
    parent = parents.get(doc_id) if isinstance(parents, dict) else None
    if not isinstance(parent, dict) or not isinstance(parent.get("metadata"), dict):
        raise KnowledgeUnavailable("父文档不存在或结构非法")
    if any(not isinstance(parent.get(k), str) or not parent[k] for k in ("body", "title", "source")):
        raise KnowledgeUnavailable("父文档正文、标题或来源缺失")
    if parent["metadata"].get("id") != doc_id:
        raise KnowledgeUnavailable("父文档 ID 不一致")
    return parent


def search_knowledge(collection, model, reranker, snapshot_dir: Path, query: str,
                     doc_type: str | None = None, top_k: int = 3,
                     recall_k: int = 20, max_content_chars: int = 16000) -> dict:
    """依赖由调用方注入；预算不足时省略整篇，绝不伪称截断内容为全文。"""
    notices = ["结果为相关候选文档，不代表故障已确认；精排分数不是置信度，当前未设置相关性拒答阈值。"]
    count = collection.count()
    if not count:
        return {"items": [], "notices": notices + ["运维知识集合为空，请先入库。"]}
    query_embedding = model.encode(INSTRUCTION + query, normalize_embeddings=True).tolist()
    kwargs = {"query_embeddings": [query_embedding], "n_results": min(recall_k, count),
              "include": ["documents", "metadatas"]}
    if doc_type is not None:
        kwargs["where"] = {"doc_type": doc_type}
    result = collection.query(**kwargs)
    texts = (result.get("documents") or [[]])[0]
    metadata = (result.get("metadatas") or [[]])[0]
    if not texts:
        return {"items": [], "notices": notices + ["当前查询范围没有候选章节，未自动放宽过滤条件。"]}
    if len(texts) != len(metadata) or any(not isinstance(t, str) or not isinstance(m, dict) for t, m in zip(texts, metadata)):
        raise KnowledgeUnavailable("章节正文或元数据不完整")
    scores = reranker.predict([(query, text) for text in texts])
    if len(scores) != len(texts):
        raise KnowledgeUnavailable("精排结果数量不匹配")
    grouped = {}
    for meta, raw_score in zip(metadata, scores):
        if any(not isinstance(meta.get(k), str) or not meta[k] for k in ("doc_id", "snapshot_id", "section", "doc_type")):
            raise KnowledgeUnavailable("章节缺少父文档关联字段")
        if meta["doc_type"] not in {"architecture", "runbook", "technology"} or (doc_type and meta["doc_type"] != doc_type):
            raise KnowledgeUnavailable("章节文档类型与过滤条件不一致")
        score = float(raw_score)
        if not math.isfinite(score):
            raise KnowledgeUnavailable("精排分数非法")
        doc_id, snapshot_id = meta["doc_id"], meta["snapshot_id"]
        group = grouped.setdefault(doc_id, {"snapshot_id": snapshot_id, "score": score,
                                            "sections": {}, "doc_type": meta["doc_type"]})
        if group["snapshot_id"] != snapshot_id:
            raise KnowledgeUnavailable("同一文档存在多个快照版本，请完成入库后重试")
        group["score"] = max(group["score"], score)
        group["sections"][meta["section"]] = max(group["sections"].get(meta["section"], -math.inf), score)
    ranked = sorted(grouped.items(), key=lambda pair: (-pair[1]["score"], pair[0]))[:top_k]
    items, snapshots, used = [], {}, 0
    for doc_id, group in ranked:
        snapshot_id = group["snapshot_id"]
        parent = load_parent(snapshot_dir, snapshot_id, doc_id, snapshots)
        if parent["metadata"].get("doc_type") != group["doc_type"]:
            raise KnowledgeUnavailable("章节与父文档类型不一致")
        if used + len(parent["body"]) > max_content_chars:
            notices.append(f"文档 {doc_id} 超过剩余正文预算，已省略整篇；可缩小查询范围或减少 top_k。")
            continue
        used += len(parent["body"])
        items.append({"doc_id": doc_id, "snapshot_id": snapshot_id,
                      "title": parent["title"], "doc_type": group["doc_type"],
                      "source": parent["source"], "score": group["score"],
                      "matched_sections": sorted(group["sections"], key=lambda section: (-group["sections"][section], section)),
                      "content": parent["body"], "content_mode": "full"})
    return {"items": items, "notices": notices}
