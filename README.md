# RAG Bot

一个基于 **RAG（检索增强生成）** 的技术文档问答机器人。流程分三步：先把 `docs/` 里的 Markdown 文档切块向量化存入向量库，检索时粗召回 + 精排取出最相关的片段，最后交给 LLM 基于这些片段生成带来源标注的回答。

## 处理流程

```text
docs/*.md  ──(ingest.py)──▶  ChromaDB 向量库
                                  │
                                  ▼
用户提问  ──(retriever.py)──▶  粗召回 20 条 ──▶ rerank 精排 top3
                                  │
                                  ▼
                          (generator.py) ──▶ LLM 生成回答（带 [n] 来源标注）
```

## 目录结构

```text
rag-bot/
├── ingest.py       # 离线构建索引：读取文档 → 切块 → 向量化 → 写入向量库
├── retriever.py    # 检索：embedding 粗召回 + reranker 精排
├── generator.py    # 生成：调用 DeepSeek API 基于检索片段回答问题
├── test.py         # 交互式入口，把检索和生成串起来
├── docs/           # 知识库源文档（Markdown），按主题分子目录
└── my_chroma_data/ # ChromaDB 持久化数据（运行 ingest.py 后生成）
```

## 各文件说明

### `ingest.py` —— 离线构建索引

把 `docs/` 目录下的 Markdown 文档切成小段，向量化后写入 ChromaDB。

- **`load_documents(root)`**：递归读取 `docs/` 下所有 `.md` 文件。每个文件用相对路径作为 `source`，用所在目录名作为 `topic`。
- **切分逻辑**（`_split_recursive` + `_merge`，合起来是 `recursive_split`）：先按分隔符递归切分，再合并到接近目标长度，块大小 `size=300`、重叠 `overlap=50`。
- **向量化**：用 `BAAI/bge-base-zh-v1.5` 模型对文档块编码（768 维，归一化）。
- **写入**：`chroma.PersistentClient` 持久化到 `./my_chroma_data`，collection 名为 `go_docs`，余弦距离。每个 chunk 的 metadata 记录 `source` / `topic` / `chunk_index`。
- 脚本开头会**先删除旧 collection 再重建**，所以重跑即可全量重建索引。

### `retriever.py` —— 检索 + 精排

加载 embedding 模型和 reranker 模型，实现「粗召回 + 精排」两阶段检索。

- 模块导入时加载两个模型：
  - `SentenceTransformer("BAAI/bge-base-zh-v1.5")` —— 向量化查询（加 bge 的查询指令前缀）。
  - `CrossEncoder("BAAI/bge-reranker-base")` —— 交叉编码器做精排。
- **`retrieve_with_rank(collection, query, ...)`**：
  1. 阶段一：把 query 编码后在向量库做相似度检索，粗召回 `recall_k=20` 条；
  2. 阶段二：用 reranker 对候选重新打分排序，取 `final_k=3` 条；
  3. 返回 `list[dict]`，每个元素是 `{"document": 原文, "metadata": {...}}`，原文和来源信息绑在一起。

### `generator.py` —— 生成回答

调用 DeepSeek 的 OpenAI 兼容接口，基于检索到的片段生成回答。

- 从环境变量 `DEEPSEEK_API_KEY` 读取密钥，`base_url` 指向 `https://api.deepseek.com`，模型 `deepseek-v4-flash`。
- **`build_context(chunks)`**：把检索到的片段拼成带编号的上下文，格式如 `[1] (来自: source - topic) 内容...`。
- **`generate(question, chunks)`**：套用 `PROMPT_TEMPLATE` 约束 LLM——只基于资料回答、资料没有就明说、标注来源 `[n]`。

### `test.py` —— 交互式入口

把上面的三步串成一个命令行问答循环：获取 collection → 检索 → 生成 → 打印回答和参考资料，输入 `quit` 退出。

## 快速开始

1. **安装依赖**（项目使用 `.venv` 虚拟环境）：

   ```powershell
   pip install chromadb sentence-transformers openai
   ```

2. **准备知识库**：往 `docs/` 里放 Markdown 文档，子目录名会被当作 `topic`。

3. **构建索引**：

   ```powershell
   python ingest.py
   ```

   成功后打印 `索引完成:xxx个chunk`。

4. **设置 API Key**（DeepSeek）：

   ```powershell
   $env:DEEPSEEK_API_KEY = "你的key"
   ```

5. **运行问答**：

   ```powershell
   python test.py
   ```

## 依赖

| 库 | 用途 |
| --- | --- |
| `chromadb` | 向量数据库（持久化存储与相似度检索） |
| `sentence-transformers` | BGE 嵌入模型 + reranker |
| `openai` | 调用 DeepSeek 的 OpenAI 兼容接口 |

## 常见问题

- **`Collection expecting embedding with dimension of X, got Y`**：构建索引和检索用了不同的 embedding 模型，导致向量维度不一致。重新跑 `python ingest.py` 重建即可。
- **运行 test.py 没输出**：模型在 `import retriever` 时就加载了，首次启动会慢几秒到十几秒，属正常现象。
