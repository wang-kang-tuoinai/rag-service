from retriever import retrieve_with_rank
from generator import generate
import chromadb as chroma

# 获取构建好的collection
client = chroma.PersistentClient(path="./my_chroma_data")
collection = client.get_collection("go_docs")

if collection is None:
    print("对应Collection不存在")

def main():
    print("Go技术文档问答机器人(输入quit退出)")
    while True:
        q = input("\n问题：").strip()
        if q.lower()=="quit":
            break
        chunks = retrieve_with_rank(collection=collection,query=q)
        answer = generate(chunks=chunks,question=q)
        print(f"\n回答:\n{answer}")
        print(f"\n参考资料:")
        for i, c in enumerate(chunks, 1):
            print(f"  [{i}] {c['metadata']['source']} - {c['metadata']['topic']}")


if __name__ == "__main__":
    main()