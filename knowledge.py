"""统一精排：项目文档取最高章节分数，技术切片独立排序。"""
import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from pydantic import ValidationError

from knowledge_models import KnowledgeChunkItem, KnowledgeFullItem

COLLECTION = "ops_knowledge"
INSTRUCTION = "为这个句子生成表示以用于检索相关文章："


class KnowledgeUnavailable(RuntimeError):
    """索引与快照缺失或不一致，不能作为成功空结果返回。"""


def load_parent(directory: Path | None, snapshot_id: str, doc_id: str, cache: dict) -> dict:
    if directory is None:
        raise KnowledgeUnavailable("父文档快照目录尚未配置")
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


@dataclass
class DocumentCandidate:
    doc_id: str
    doc_type: str
    snapshot_id: str
    score: float
    sections: dict[str, float] = field(default_factory=dict)


def rank_candidates(ids, texts, metadata, scores, doc_type):
    """只聚合项目文档；技术切片不按 doc_id 合并，也不限制每篇的切片数量。"""
    grouped, chunks, document_types = {}, {}, {}
    for chunk_id, text, meta, raw_score in zip(ids, texts, metadata, scores):
        if any(not isinstance(meta.get(k), str) or not meta[k] for k in ("doc_id", "section", "doc_type")):
            raise KnowledgeUnavailable("章节缺少文档 ID、章节名或类型")
        kind, doc_id = meta["doc_type"], meta["doc_id"]
        if kind not in {"architecture", "runbook", "technology"} or (doc_type and kind != doc_type):
            raise KnowledgeUnavailable("章节文档类型与过滤条件不一致")
        if document_types.setdefault(doc_id, kind) != kind:
            raise KnowledgeUnavailable("同一文档存在不同文档类型")
        try:
            score = float(raw_score)
        except (ValueError, TypeError) as exc:
            raise KnowledgeUnavailable("精排分数非法") from exc
        if not math.isfinite(score):
            raise KnowledgeUnavailable("精排分数非法")
        if kind == "technology":
            try:
                item = KnowledgeChunkItem(
                    doc_id=doc_id, chunk_id=chunk_id, score=score, content=text,
                    **{key: meta.get(key) for key in
                       ("title", "source", "component", "source_url", "section", "chunk_index")},
                )
            except ValidationError as exc:
                raise KnowledgeUnavailable("技术切片元数据缺失或非法，请重新构建索引") from exc
            if chunk_id not in chunks or score > chunks[chunk_id].score:
                chunks[chunk_id] = item
            continue
        snapshot_id = meta.get("snapshot_id")
        if not isinstance(snapshot_id, str) or not re.fullmatch(r"[0-9a-f]{64}", snapshot_id):
            raise KnowledgeUnavailable("项目章节缺少有效的 snapshot_id，请重新构建索引")
        group = grouped.setdefault(doc_id, DocumentCandidate(doc_id, kind, snapshot_id, score))
        if group.snapshot_id != snapshot_id:
            raise KnowledgeUnavailable("同一文档存在多个快照版本，请完成入库后重试")
        group.score = max(group.score, score)
        group.sections[meta["section"]] = max(group.sections.get(meta["section"], -math.inf), score)
    # 同分时用稳定 ID 排序，不依赖向量库的返回顺序。
    return sorted([*grouped.values(), *chunks.values()],
                  key=lambda item: (-item.score, item.doc_id, getattr(item, "chunk_id", "")))


def search_knowledge(collection, model, reranker, snapshot_dir: Path | None, query: str,
                     doc_type: str | None = None, top_k: int = 3,
                     recall_k: int = 20, max_content_chars: int = 16000) -> dict:
    """先聚合排序取 top_k，再取全文或切片；预算不足时整条省略。"""
    notices = ["结果为相关候选资料，不代表故障已确认；精排分数不是置信度，当前未设置相关性拒答阈值。"]
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
    ids = (result.get("ids") or [[]])[0]
    if not (len(ids) == len(texts) == len(metadata)):
        raise KnowledgeUnavailable("章节 ID、正文或元数据数量不一致")
    if not texts:
        return {"items": [], "notices": notices + ["当前查询范围没有候选章节，未自动放宽过滤条件。"]}
    if any(not isinstance(cid, str) or not cid or not isinstance(t, str) or not t.strip()
           or not isinstance(m, dict) for cid, t, m in zip(ids, texts, metadata)):
        raise KnowledgeUnavailable("章节 ID、正文或元数据不完整")
    scores = reranker.predict([(query, text) for text in texts])
    if len(scores) != len(texts):
        raise KnowledgeUnavailable("精排结果数量不匹配")
    ranked = rank_candidates(ids, texts, metadata, scores, doc_type)[:top_k]
    items, snapshots, used = [], {}, 0
    for candidate in ranked:
        if isinstance(candidate, DocumentCandidate):
            parent = load_parent(snapshot_dir, candidate.snapshot_id, candidate.doc_id, snapshots)
            if parent["metadata"].get("doc_type") != candidate.doc_type:
                raise KnowledgeUnavailable("章节与父文档类型不一致")
            item = KnowledgeFullItem(
                doc_id=candidate.doc_id, snapshot_id=candidate.snapshot_id,
                title=parent["title"], doc_type=candidate.doc_type,
                source=parent["source"], score=candidate.score, content=parent["body"],
                matched_sections=sorted(candidate.sections, key=lambda s: (-candidate.sections[s], s)),
            )
        else:
            item = candidate
        if used + len(item.content) > max_content_chars:
            identity = item.chunk_id if isinstance(item, KnowledgeChunkItem) else item.doc_id
            notices.append(f"结果 {identity} 超过剩余正文预算，已整条省略；可缩小查询范围或减少 top_k。")
            continue
        used += len(item.content)
        items.append(item.model_dump())
    return {"items": items, "notices": notices}
