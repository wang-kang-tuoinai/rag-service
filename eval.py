import statistics

import chromadb as chroma
from chromadb import Where
from sentence_transformers import SentenceTransformer
from sentence_transformers import CrossEncoder

from generator import generate_query_and_corpus

eval_set = [
    {"query": "怎么样解决缓存穿透问题", "expect_span": ["缓存空数据"]},
    {
        "query": "缓存穿透问题出现的原因有哪些",
        "expect_span": ["恶意的攻击", "代码的逻辑有问题"],
        "corpus": "my-notes",
    },
    {
        "query": "缓存雪崩的解决办法是什么",
        "expect_span": ["搭建redis集群", "随机的抖动"],
        "corpus": "my-notes",
    },
    {
        "query": "布隆过滤器为什么会产生误判",
        "expect_span": ["不同key的经过哈希计算出来得到的下标总会有重叠"],
        "corpus": "my-notes",
    },
    {
        "query": "为什么需要分布式锁",
        "expect_span": ["多个实例同时运行，那他就不能保证互斥了"],
        "corpus": "my-notes",
    },
    {
        "query": "分布式锁解锁有什么要注意的",
        "expect_span": [
            "要判断一下删除的是不是自己的锁",
            "如果只是单纯的先去Redis查询再决定是否删除",
            "Lua脚本",
        ],
        "corpus": "my-notes",
    },
    {
        "query": "redis的RDB持久化方式有哪些特点",
        "expect_span": [
            "fork出一个子进程",
            "不阻塞主进程",
            "RDB是二进制文件内存占用比AOF小",
            "恢复速度快",
        ],
        "corpus": "my-notes",
    },
    {
        "query": "装饰器模式的好处",
        "expect_span": [
            "handler层以及repository层代码根本不用改",
            "Cache层无需关注数据层的实现细节",
        ],
        "corpus": "my-notes",
    },
    {
        "query": "数据更新的时候是删缓存还是更新缓存",
        "expect_span": [
            "更新缓存会有并发问题",
            "导致缓存与实际数据库存储的数据不一致",
            "缓存删除时幂等的",
        ],
        "corpus": "my-notes",
    },
    {
        "query": "异步解耦有哪些好处",
        "expect_span": ["削峰填谷", "不会导致服务器压力暴增"],
        "corpus": "my-notes",
    },
    {
        "query": "为什么明明数据库里没这条数据，布隆过滤器还说有",
        "expect_span": ["下标总会有重叠"],
        "corpus": "my-notes",
    },
    {
        "query": "A进程的锁被B进程解掉了怎么办",
        "expect_span": ["判断一下删除的是不是自己的锁"],
        "corpus": "my-notes",
    },
    {
        "query": "秒杀活动开始瞬间大量请求涌进来，数据库扛不住怎么办",
        "expect_span": ["互斥锁", "逻辑过期"],
        "corpus": "my-notes",
    },
    {
        "query": "服务器半夜突然全线崩溃，重启后又正常了",
        "expect_span": ["随机的抖动"],
        "corpus": "my-notes",
    },
    {
        "query": "怎么让加缓存这件事不侵入原来的代码",
        "expect_span": ["cache层持有repository层的引用"],
        "corpus": "my-notes",
    },
    {
        "query": "消息处理失败了但重试也没用该怎么处理",
        "expect_span": ["消息本身就有缺陷"],
        "corpus": "my-notes",
    },
    {
        "query": "哪些数据不适合放进缓存",
        "expect_span": ["List分页", "GetAll", "GetAllIDs"],
        "corpus": "my-notes",
    },
    {
        "query": "为什么不能直接用Del命令释放锁",
        "expect_span": ["判断一下删除的是不是自己的锁"],
        "corpus": "my-notes",
    },
    {
        "query": "redis两种持久化方式在恢复速度上有什么差别",
        "expect_span": ["恢复速度快", "指令恢复速度较慢"],
        "corpus": "my-notes",
    },
    {
        "query": "布隆过滤器的参数该怎么设计",
        "expect_span": ["参数没有固定的值", "根据实际业务来考虑"],
        "corpus": "my-notes",
    },
]

# 导入模型
model = SentenceTransformer("BAAI/bge-base-zh-v1.5")
reranker = CrossEncoder("BAAI/bge-reranker-base")


# 判断召回结果是否命中
def is_hit(d: str, item: dict) -> bool:
    d = d.lower()
    if any(sub.lower() in d for sub in item["expect_span"]):
        return True
    return False


def evaluate(collection, eval_set, model, reranker, recall_k=20, final_k=3):
    hits, rr_sum = 0, 0.0
    corpus_hits, corpus_total = 0, 0
    missed = []
    not_top1 = []
    corpus_missed = []
    INSTRUCTION = "为这个句子生成表示以用于检索相关文章："
    for item in eval_set:
        # 用 generate_query_and_corpus 改写 query，并判断语料范围
        q, pred_corpus = generate_query_and_corpus(item["query"])

        # corpus 命中率统计（只统计有标注 corpus 的样本）
        expect_corpus = item.get("corpus")
        if expect_corpus:
            corpus_total += 1
            if pred_corpus == expect_corpus:
                corpus_hits += 1
            else:
                corpus_missed.append((item["query"], expect_corpus, pred_corpus))

        where: Where | None = {"corpus": pred_corpus} if pred_corpus != "all" else None
        q_emb = model.encode(INSTRUCTION + q, normalize_embeddings=True).tolist()
        candidates = collection.query(
            query_embeddings=[q_emb], n_results=recall_k, where=where
        )
        docs = candidates["documents"][0]
        pairs = [[q, doc] for doc in docs]
        scores = reranker.predict(pairs)
        ranked = sorted(zip(scores, docs), key=lambda x: -x[0])
        if not ranked:
            missed.append((item["query"], []))
            continue
        _, docs = zip(*ranked)
        docs = docs[:final_k]
        rank = 0
        for i, d in enumerate(docs, start=1):
            if is_hit(d, item):
                rank = i
                break  # 只算第一个命中的位置

        if rank > 0:
            hits += 1
            rr_sum += 1 / rank
            if rank > 1:
                not_top1.append((item["query"], rank, docs))
        else:
            missed.append((item["query"], docs))

    n = len(eval_set)
    corpus_hit_rate = corpus_hits / corpus_total if corpus_total else 0.0
    return hits / n, rr_sum / n, corpus_hit_rate, missed, not_top1, corpus_missed


client = chroma.PersistentClient(path="./my_chroma_data")
try:
    collection = client.get_collection("go_docs")
except Exception:
    print("对应Collection不存在")
    raise

final_k = 3
N_RUNS = 5

hit_vals, rr_vals, corpus_vals = [], [], []
missed_all, not_top1_all, corpus_missed_all = [], [], []

for _ in range(N_RUNS):
    hit, rr, corpus_hit_rate, missed, not_top1, corpus_missed = evaluate(
        collection=collection,
        eval_set=eval_set,
        model=model,
        reranker=reranker,
        final_k=final_k,
    )
    hit_vals.append(hit)
    rr_vals.append(rr)
    corpus_vals.append(corpus_hit_rate)
    missed_all.extend(missed)
    not_top1_all.extend(not_top1)
    corpus_missed_all.extend(corpus_missed)


def summarize(name, values):
    return f"{name}: 均值={statistics.mean(values):.4f}, 标准差={statistics.stdev(values):.4f}"


def dedup_by_query(entries):
    """按 query 去重，避免多轮重复统计"""
    seen, result = set(), []
    for e in entries:
        key = e[0] if isinstance(e, tuple) else e
        if key not in seen:
            seen.add(key)
            result.append(e)
    return result


print(f"共运行 {N_RUNS} 次（LLM 生成有随机性，取均值/标准差）")
print(summarize(f"hit@{final_k}", hit_vals))
print(summarize("rr", rr_vals))
print(summarize("corpus_hit", corpus_vals))
print(f"missed_query（去重后）:{dedup_by_query(missed_all)}")
print(f"not_top1_query（去重后）:{dedup_by_query(not_top1_all)}")
print(f"corpus_missed（去重后）:{dedup_by_query(corpus_missed_all)}")
