# 运维知识检索服务

为运维 Agent 提供知识检索 HTTP 接口。服务从 `doc/` 构建并查询 Chroma 的 `ops_knowledge` 索引，返回完整项目文档或技术切片，不生成聊天回答。

## 启动

在项目 Python 环境中执行：

```powershell
pip install -r requirements.txt
python ingest.py --dry-run
python ingest.py
uvicorn main:app --host 0.0.0.0 --port 8000
```

已有最新索引时直接启动服务，无需重复入库。模型首次加载需要下载或提前准备 Hugging Face 缓存。

`lifespan` 启动时加载 embedding、reranker 和 `ops_knowledge` collection，查询复用 `app.state.collection`。索引缺失时启动失败并提示先入库，不自动创建空集合，不依赖旧 `go_docs` 索引或文档机器人 API。

## 接口

- `GET /health`：健康状态及模型、collection 是否已加载。
- `POST /api/v1/knowledge/search`：知识检索。
- `GET /docs`：接口调试和响应模型说明。

请求示例：

```json
{
  "query": "Redis 读取超时后如何排查",
  "doc_type": "technology",
  "top_k": 3
}
```

`doc_type` 可省略，或指定 `architecture/runbook/technology`。前两类按文档取最高章节分数，技术切片独立计分，统一排序取 `top_k`。结果通过 `content_mode: full/chunk` 区分全文与切片。

## 主要文件

| 文件 | 职责 |
|---|---|
| main.py | 服务生命周期、观测埋点、健康检查、路由注册 |
| knowledge_api.py | HTTP 查询入口，复用启动时加载的依赖 |
| knowledge_models.py | 请求模型及全文、切片两种响应模型 |
| knowledge.py | 召回、精排、聚合排序和父文档读取 |
| ingest.py | 文档解析、按类型准备切片、统一写入索引 |
| markdown_splitter.py | Markdown 切分与 token 预算控制 |
| view_chunks.py | 本地切片查看页面 |

入库规则见 [maintenance/ingestion.md](maintenance/ingestion.md)，查询契约见 [maintenance/knowledge-search-api.md](maintenance/knowledge-search-api.md)。

更新索引使用 `ingest.py` 的全量同步流程；构建期间避免查询。如果删除并重新创建 collection，应重启服务以重新加载 collection。
