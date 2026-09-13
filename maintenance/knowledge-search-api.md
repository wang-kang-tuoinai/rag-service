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
| doc_type | 可选 architecture/runbook；省略或 null 检索两类；无结果不放宽过滤 |
| top_k | 父文档数量，默认 3，范围 1–5，必须为整数 |

未声明字段（包括 component、type）会返回 422，避免误以为过滤生效。

## 检索流程

复用服务启动时的 embedding 和 reranker。将 query 加上 BGE 查询前缀后向量化，从 ops_knowledge 召回最多 20 个章节；doc_type 作为 Chroma where 条件。精排输入为 (原始 query, 章节文本)。按 doc_id 分组，组内保留 snapshot_id 用于读取正文，并校验同一文档的快照一致性，每组最高章节分数作为文档分数，取 top_k 篇。matched_sections 来自命中章节 metadata.section，去重并按章节分数排列。

父文档从 my_chroma_data/ops_knowledge_parents/<snapshot_id>.json 读取，通过 doc_id 获取。校验快照 SHA-256、文档 ID 和类型，不读取当前 doc/ 文件替代快照。一次查询内部复用已读取快照。

## 成功响应

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
  "notices": ["结果为相关候选文档，不代表故障已确认；精排分数不是置信度，当前未设置相关性拒答阈值。"]
}
```

示例分数仅为说明，不是固定范围或概率。最多返回所选文档的 16000 个 Python 字符正文总量，不是 Token 预算；超预算整篇省略并写 notices，不截断后标为全文。所选文档超过预算时可能少于 top_k，不自动用低排名文档补位。

## 状态码与边界

- 200：完成查询；空集合、过滤无候选或预算省略可返回 items=[]，区别见 notices。
- 422：参数非法。
- 503：模型依赖未就绪、ops_knowledge 不存在、快照缺失/损坏、索引不一致或查询失败。响应为 {"detail":"说明"}。

当前不设相关性阈值，不承诺每次返回的候选都能回答；需要后续用实际查询校准。沿用现有 reranker 的输入长度设置，过长 query/章节组合可能受其截断限制，后续评测需关注。应在入库完成后查询，构建不是原子切换。

## 运行

先完成 ingest.py 的实际入库（dry-run 不生成索引），再运行原有 rag-service 服务。接口在 FastAPI /docs 中可测试。main.py 仍沿用现有 go_docs 的启动加载要求；部署时旧问答索引也需存在。新接口不会创建空集合掩盖缺失索引。

验证使用模拟 embedding/reranker 和临时快照，并额外用真实临时 Chroma 集合检查 metadata 过滤；不代表真实模型的召回质量评测。
