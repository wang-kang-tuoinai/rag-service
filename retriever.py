# 该文件是检索+rerank的作用
import chromadb as chroma
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

# 初始化模型
model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
reranker = reranker = CrossEncoder("BAAI/bge-reranker-base")


def retrieve_with_rank(
    collection: chroma.Collection,
    query,
    model: SentenceTransformer = model,
    reranker: CrossEncoder = reranker,
    recall_k=20,
    final_k=3,
) -> list[dict]:
    "带rerank的召回，返回 chunk 原文及其 metadata"
    # 阶段一，粗召回
    INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
    q_emb = model.encode(INSTRUCTION + query, normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=[q_emb], n_results=recall_k)
    documents = res["documents"]
    if not documents:
        return []
    candidates = documents[0]
    metadatas = res.get("metadatas") or []
    metadatas = metadatas[0] if metadatas else [{}] * len(candidates)

    # 阶段二，精排
    pairs = [(query, doc) for doc in candidates]
    scores = reranker.predict(pairs)
    ranked = sorted(zip(scores, candidates, metadatas), key=lambda x: -x[0])
    return [{"document": doc, "metadata": meta} for _, doc, meta in ranked[:final_k]]
