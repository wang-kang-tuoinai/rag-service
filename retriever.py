# 该文件是检索+rerank的作用（纯函数，模型由调用方传入）
import chromadb as chroma
from chromadb import Where
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder


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
    q_emb = model.encode(INSTRUCTION + query, normalize_embeddings=True).tolist()
    where: Where | None = {"corpus": corpus} if corpus != "all" else None
    res = collection.query(query_embeddings=[q_emb], n_results=recall_k,where=where)
    candidates = res["documents"][0] if res["documents"] else []
    metadatas = res["metadatas"][0] if res["metadatas"] else [{}] * len(candidates)

    if not candidates:
        return []
    # 阶段二，精排
    pairs = [(query, doc) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, candidates, metadatas), key=lambda x: -x[0])
    return [{"document": doc, "metadata": meta} for _, doc, meta in ranked[:final_k]]
