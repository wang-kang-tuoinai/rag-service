# 知识库维护清单

本文件供维护者使用，不参与 RAG 检索。doc/ 只保留业务架构与排查知识。以下来源与核对状态从正文移入，未重新进行故障演练。

## 维护规则

- 当前文档依据 2026-09-11 工作区静态核对，verification 为 source_review_only；不是已验证事故记录。
- 代码变更后按下列来源检查业务语义、日志模板、超时和工具字段；实际故障演练结果及部署版本在此记录。
- 人工检查步骤仍保留在知识正文：Agent 可以建议用户补充这些证据，但不能声称已经执行。
- 工具通用规则（只读范围、真实 trace_id、截断提示）应由工具描述统一承载，不在每篇重复维护。
- ingest.py 当前读取 docs/，尚未接入 doc/；后续解析适用范围元数据并合理切分，排除 maintenance/。本次不重建索引。
- Redis MaxRetries=0 的实际客户端行为尚需核对依赖版本，不把源码注释当作禁用重试保证。

## 文档来源与核对状态

### architecture/dependency-contracts.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/main.go`
- `ops-agent-backend/internal/repository/mysql/user_mysql.go`
- `ops-agent-backend/internal/utils/redisDL.go`
- `ops-agent-backend/internal/cache/user_cache_repository.go`
- `ops-agent-backend/internal/mq/publisher.go`
- `ops-agent-backend/internal/mq/consumer.go`
- `ops-agent-backend/internal/mq/event.go`
- `ops-agent-backend/cmd/consumer/main.go`

### architecture/user-request-flows.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/router/router.go`
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/handler/response.go`
- `ops-agent-backend/internal/cache/user_cache_repository.go`
- `ops-agent-backend/internal/bloom/bloom.go`
- `ops-agent-backend/main.go`

### runbooks/cache-invalidation.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/cache/user_cache_repository.go`
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/observability/log.go`

### runbooks/cache-miss-invalid-data.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/cache/user_cache_repository.go`
- `ops-agent-backend/internal/cache/cached_user.go`
- `ops-agent-backend/internal/handler/response.go`
- `ops-agent-backend/internal/observability/log.go`

### runbooks/expected-4xx-bloom.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/handler/response.go`
- `ops-agent-backend/internal/repository/mysql/user_mysql.go`
- `ops-agent-backend/main.go`
- `ops-agent-backend/internal/observability/log.go`

### runbooks/mysql-failure-slow.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/repository/mysql/user_mysql.go`
- `ops-agent-backend/internal/handler/response.go`
- `ops-agent-backend/main.go`

### runbooks/rabbitmq-publish-consume.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/mq/publisher.go`
- `ops-agent-backend/internal/mq/consumer.go`
- `ops-agent-backend/internal/mq/event.go`
- `ops-agent-backend/cmd/consumer/main.go`

### runbooks/redis-read-fallback.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/cache/user_cache_repository.go`
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/observability/log.go`

### runbooks/redis-update-lock.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/handler/user_handler.go`
- `ops-agent-backend/internal/utils/redisDL.go`
- `ops-agent-backend/internal/handler/response.go`
- `ops-agent-backend/internal/observability/log.go`

### runbooks/telemetry-gaps-and-unexplained-latency.md

- 核对日期：2026-09-11；状态：source_review_only，待故障演练。
- `ops-agent-backend/internal/observability/recorder.go`
- `ops-agent-backend/internal/observability/middleware.go`
- `ops-agent-backend/main.go`
- `obs-api/main.go`
- `obs-api/internal/tracestore/detail.go`
- `obs-api/internal/tracestore/analyze.go`

## 移出与拆分记录

- doc/README.md → maintenance/knowledge-index.md（人用目录和入库流程）。
- 观测故障手册 → [采集与工具排查](telemetry-troubleshooting.md)，保留原文供维护者使用。
- 其中业务未解释耗时部分独立为 doc/runbooks/unexplained-latency.md；源码依据沿用原手册中的后端 Recorder、Middleware、main.go 与 Trace 分析代码。核对状态同上。
