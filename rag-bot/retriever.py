# 该文件是检索+rerank的作用（纯函数，模型由调用方传入）
import chromadb as chroma
from chromadb import Where
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

from opentelemetry import trace

tracer = trace.get_tracer("rag-service")


def _truncate(text: str, limit: int = 200) -> str:
    """截断文本，避免往 span 里塞过大内容"""
    return text[:limit] + ("..." if len(text) > limit else "")


def _meta_str(meta, key: str) -> str:
    """安全取出 metadata 里的字符串字段（可能为 None 或非字符串类型）"""
    value = (meta or {}).get(key)
    return value if isinstance(value, str) else ""


def retrieve_with_rank(
    collection: chroma.Collection,
    query,
    model: SentenceTransformer,
    reranker: CrossEncoder,
    corpus: str = "all",
    recall_k=20,
    final_k=3,
) -> list[dict]:
    "带rerank的召回，返回 chunk 原文及其 metadata"
    # 阶段一，粗召回
    INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
    with tracer.start_as_current_span("retrieve") as span:
        span.set_attribute("rag.query", query)
        span.set_attribute("rag.recall_k", recall_k)
        q_emb = model.encode(INSTRUCTION + query, normalize_embeddings=True).tolist()
        where: Where | None = {"corpus": corpus} if corpus != "all" else None
        res = collection.query(query_embeddings=[q_emb], n_results=recall_k, where=where)
        candidates = res["documents"][0] if res["documents"] else []
        metadatas = res["metadatas"][0] if res["metadatas"] else [{}] * len(candidates)
        span.set_attribute("rag.num_candidates", len(candidates))
        for i, (doc, meta) in enumerate(zip(candidates, metadatas)):
            span.set_attribute(f"rag.recall.{i:02d}.source", _meta_str(meta, "source"))
            span.set_attribute(f"rag.recall.{i:02d}.topic", _meta_str(meta, "topic"))
            span.set_attribute(f"rag.recall.{i:02d}.text", _truncate(doc))

    if not candidates:
        return []
    # 阶段二，精排
    with tracer.start_as_current_span("rerank") as span:
        span.set_attribute("rag.final_k", final_k)
        pairs = [(query, doc) for doc in candidates]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, candidates, metadatas), key=lambda x: -x[0])
        final = [{"document": doc, "metadata": meta} for _, doc, meta in ranked[:final_k]]
        span.set_attribute("rag.num_reranked", len(final))
        for i, item in enumerate(final):
            span.set_attribute(f"rag.rerank.{i:02d}.source", _meta_str(item["metadata"], "source"))
            span.set_attribute(f"rag.rerank.{i:02d}.topic", _meta_str(item["metadata"], "topic"))
            span.set_attribute(f"rag.rerank.{i:02d}.text", _truncate(item["document"]))
        return final
