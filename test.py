from datetime import datetime

from retriever import retrieve_with_rank
from generator import generate,generate_query
from chat_scroll import new_conversation, load, list_conversations, save
import chromadb as chroma

# 获取构建好的collection
client = chroma.PersistentClient(path="./my_chroma_data")
collection = client.get_collection("go_docs")

if collection is None:
    print("对应Collection不存在")


def _fmt_time(ts):
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


def select_conversation():
    """启动时选择：继续旧会话或新建"""
    convs = list_conversations()
    if not convs:
        return new_conversation()
    print("历史会话（按修改时间从新到旧）：")
    for i, c in enumerate(convs, 1):
        title = c.get("title") or "（无标题）"
        n = len(c.get("messages", []))
        print(f"  [{i}] {title}  ({_fmt_time(c['updated_at'])}, {n} 条消息)")
    sel = input("输入编号继续会话，直接回车新建：").strip()
    if sel.isdigit() and 1 <= int(sel) <= len(convs):
        return load(convs[int(sel) - 1]["id"]) or new_conversation()
    return new_conversation()


def main():
    print("Go技术文档问答机器人(输入quit退出)")
    conv = select_conversation()
    while True:
        q = input("\n问题：").strip()
        if q.lower() == "quit":
            break
        query = generate_query(q,conv["messages"])
        print(f"system:生成的query为{query}")
        chunks = retrieve_with_rank(collection=collection, query=query)
        answer = generate(question=q, chunks=chunks, history=conv["messages"])
        print(f"\n回答:\n{answer}")
        print(f"\n参考资料:")
        for i, c in enumerate(chunks, 1):
            print(f"  [{i}] {c['metadata']['source']} - {c['metadata']['topic']}")
        conv["messages"].append({"role": "user", "content": q})
        conv["messages"].append({"role": "assistant", "content": answer})
        save(conv)


if __name__ == "__main__":
    main()
