# 知识查询接口

`POST /api/v1/knowledge/search`，请求和响应均为 JSON。本接口不调用生成模型，不保存对话，不注册 Agent 工具。

## 请求

```json
{
  "query": "Redis 读取失败后，用户查询如何处理",
  "doc_type": "runbook",
  "top_k": 3
}
```

| 参数 | 规则 |
|---|---|
| query | 必填，去除首尾空白后非空，输入最大 2000 字符 |
| doc_type | 可选 architecture/runbook/technology；省略或 null 检索全部三类；无结果不放宽过滤 |
| top_k | 聚合后统一排序的结果条数，默认 3，范围 1–5，必须为整数；全文和技术切片各计一条 |

未声明字段（包括 component、type）会返回 422，避免误以为过滤生效。

## 检索流程

复用服务启动时的 embedding 和 reranker。将 query 加上 BGE 查询前缀后向量化，从 ops_knowledge 召回最多 20 个章节；doc_type 作为 Chroma where 条件。精排输入为 (原始 query, 章节文本)。

- architecture/runbook：按 doc_id 分组，校验同一文档的快照一致性，每组最高章节分数作为文档分数。matched_sections 来自命中章节 metadata.section，去重并按章节分数排列。
- technology：每个 chunk 独立作为候选，使用自己的精排分数，不按 doc_id 聚合，不限制每篇文章入选数量。相同 chunk_id 只保留最高分的一条，不做相邻片段合并或正文相似去重。
- 将文档候选和技术切片候选统一按分数降序排列，取 top_k。同分时依次按 doc_id、chunk_id 排序，使结果稳定。

只有入选的 architecture/runbook 才从 my_chroma_data/ops_knowledge_parents/<snapshot_id>.json 读取父文档，通过 doc_id 获取。校验快照 SHA-256、文档 ID 和类型，不读取当前 doc/ 文件替代快照。一次查询内部复用已读取快照。

technology 直接返回 Chroma documents 中保存的文本（文档标题 + 章节路径 + 正文），chunk_id 使用 Chroma 返回的 ids，不依赖 snapshot_id 或父文档目录。同一技术文章的相邻切片可以同时入选，保留入库时的少量正文重叠。

## 成功响应

请求和响应模型集中在 knowledge_models.py，KnowledgeSearchResponse.items 通过 content_mode 区分 KnowledgeFullItem 和 KnowledgeChunkItem。FastAPI /docs 展示两种结构，避免把两类专属字段都设为可选。

全文结果保持原有结构：

```json
{
  "items": [{
    "doc_id": "runbook-redis-read-fallback",
    "snapshot_id": "入库生成的64位十六进制哈希",
    "title": "Redis 读取失败与数据库回源",
    "doc_type": "runbook",
    "source": "runbooks/redis-read-fallback.md",
    "score": 0.92,
    "matched_sections": ["项目行为与证据线索"],
    "content": "完整 Markdown 正文（不含 front matter）",
    "content_mode": "full"
  }],
  "notices": ["结果为相关候选资料，不代表故障已确认；精排分数不是置信度，当前未设置相关性拒答阈值。"]
}
```

技术切片结果示例（可与全文结果同时出现在 items 中）：

```json
{
  "doc_id": "technology-来源URL的SHA256",
  "chunk_id": "technology-来源URL的SHA256::section::4",
  "title": "Redis 延迟诊断指南",
  "doc_type": "technology",
  "component": "redis",
  "source": "technology/redis/10-redis-latency.md",
  "source_url": "https://redis.com.cn/management/10-redis-latency.html",
  "section": "测量延迟 / 使用 redis-cli 测量延迟",
  "chunk_index": 4,
  "score": 0.88,
  "content": "文档标题：Redis 延迟诊断指南\n章节标题：测量延迟 / 使用 redis-cli 测量延迟\n\n切片正文",
  "content_mode": "chunk"
}
```

技术切片没有 snapshot_id、matched_sections；全文结果没有 chunk_id、chunk_index 等切片专属字段。技术切片的 source_url、component、section 和 chunk_index 来自其 metadata。

示例分数仅为说明，不是固定范围或概率。所有入选结果的 content 总量最多 16000 个 Python 字符，不是 Token 预算；超预算整条省略并写 notices，不截断后标为全文或完整切片。先选 top_k 再应用预算，省略后可能少于 top_k，不自动用低排名结果补位。

## 状态码与边界

- 200：完成查询；空集合、过滤无候选或预算省略可返回 items=[]，区别见 notices。
- 422：参数非法。
- 503：查询依赖未就绪、运行中索引已不可用、快照缺失/损坏、索引不一致或查询失败。响应为 {"detail":"说明"}。启动时缺少 ops_knowledge 会直接导致启动失败并提示先入库。

当前不设相关性阈值，不承诺每次返回的候选都能回答；需要后续用实际查询校准。沿用现有 reranker 的输入长度设置，过长 query/章节组合可能受其截断限制，后续评测需关注。应在入库完成后查询，构建不是原子切换。

## 运行

先完成 ingest.py 的实际入库（dry-run 不生成索引），再启动 rag-service。接口在 FastAPI /docs 中可测试。main.py 的 lifespan 加载模型和 ops_knowledge，并通过 app.state.collection 提供给查询路由；每次请求不再调用 get_collection。旧文档机器人路由已移除，服务不依赖 go_docs，也不会自动创建空集合。

删除并重新创建 collection 后应重启服务，重新获取 collection。正常入库使用现有 collection 的 upsert/delete 流程；构建期间避免查询。

查询与入库的 23 项回归测试通过，覆盖混合排序、同篇技术切片不设数量上限、响应模型、预算和快照异常，并用临时 Chroma 集合检查 metadata 过滤及切片 ID。

另外使用本地缓存的真实 embedding/reranker 和已重建索引，通过 FastAPI TestClient 验证 technology、runbook、不指定类型三种 HTTP 查询，均返回 200 和非空结果。这属于接口与数据兼容性验证，不代表系统性的召回质量评测；未重新入库。
