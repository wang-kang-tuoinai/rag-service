# 读取docs目录下面的文件，相对路径作为source，目录名作为topic
from pathlib import Path
def load_documents(root: str) -> list[dict]:
    docs = []
    for path in Path(root).rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        docs.append(
            {"text": text, "source": str(path.relative_to(root)), "topic": path.parent.name}
        )
    return docs

import chromadb as chroma
from sentence_transformers import SentenceTransformer

# 使用BAAI/bge-base-zh-v1.5这个embed模型对doc进行向量化(与 retriever 保持一致)
model = SentenceTransformer("BAAI/bge-base-zh-v1.5")

client = chroma.PersistentClient(path="./my_chroma_data")
# 不存在就创建collection，存在先删除再创建
try:
    client.delete_collection("go_docs")
except Exception:
    pass
collection = client.create_collection("go_docs", metadata={"hnsw:space": "cosine"})

# 递归切分
def _split_recursive(text, separators, size):
    """阶段一:递归切,直到每个片段都不超过 size"""
    if len(text) <= size:
        return [text]

    # 找第一个在文本里出现的分隔符
    sep, rest = "", []
    for i, s in enumerate(separators):
        if s == "":              # 兜底:没有任何分隔符可用
            break
        if s in text:
            sep, rest = s, separators[i + 1:]
            break
    # 如果没有找到分割符,直接按长度硬切
    if sep == "":                # 硬切
        return [text[i:i + size] for i in range(0, len(text), size)]

    parts = text.split(sep)
    pieces = []
    for j, p in enumerate(parts):
        if not p:
            continue
        # 把分隔符加回去,不然句号全丢了
        piece = p + sep if j < len(parts) - 1 else p
        # 如果切分后的长度还是大于size,递归再切分
        if len(piece) > size:
            pieces.extend(_split_recursive(piece, rest, size))  # 降级再切
        else:
            pieces.append(piece)
    return pieces


def _merge(pieces, size, overlap):
    """阶段二:把小片段合并到接近 size"""
    chunks, cur, cur_len = [], [], 0
    for p in pieces:
        # 如果再加一个会超过size，并且当前cur缓冲区不为空，那就先将当前缓冲区内容作为一个chunk
        if cur_len + len(p) > size and cur:
            chunks.append("".join(cur))
            # 从头部丢弃,保留末尾约 overlap 长度作为重叠
            while cur and cur_len > overlap:
                cur_len -= len(cur[0])
                cur.pop(0)
        cur.append(p)
        cur_len += len(p)
    if cur:
        chunks.append("".join(cur))
    return chunks

# 先切分，再合并。
def recursive_split(text, size=300, overlap=50, separators=None)->list[str]:
    if separators is None:
        separators = ["\n\n", "\n", "。", "！", "？", "；", "，", ""]
    return _merge(_split_recursive(text, separators, size), size, overlap)

docs = load_documents("./docs")

# 把文档切分塞入collection
chunk_ids = []
chunk_texts = []
chunk_metadatas = []
for i,d in enumerate(docs):
    chunks = recursive_split(d["text"])
    for j,chunk in enumerate(chunks):
        chunk_ids.append(f"doc_{i}_chunk_{j}")
        chunk_texts.append(chunk)
        chunk_metadatas.append({"source":d["source"],"topic":d["topic"],"chunk_index":j})

chunk_embeddings = model.encode(chunk_texts, normalize_embeddings=True).tolist()

collection.add(
    ids=chunk_ids,
    documents=chunk_texts,
    metadatas=chunk_metadatas,
    embeddings=chunk_embeddings,
)

print(f"索引完成:{collection.count()}个chunk")