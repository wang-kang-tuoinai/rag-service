---
id: arch-observability
doc_type: maintenance
project: ops-agent
service: ops-agent-backend
component: observability
deployment: docker-compose
reviewed_at: "2026-09-28"
verification: source_review_only
---

# 观测工具与证据口径

## 日志
query_log_stats → query_log_templates → search_logs，已有 trace_id 时直接查询关联日志。
日志来自显式 Recorder 调用，不是 stdout 全量采集。ERROR 占比是日志条数占比，不是请求失败率；一个 500 可能有业务 ERROR 和 access ERROR，不能简单除以二还原。
当前 access middleware 的实际分支是 5xx 为 ERROR，其他为 INFO（包括 4xx），以代码为准，不采用旧注释的 4xx WARN。
templates 的 sample 是代表性样例，不证明其他请求均有相同根因。attrs.err 才可能包含具体异常。
Recorder 使用请求 context 同步写 obs-mysql；写失败仅打印 record event failed。请求超时或观测库故障可能造成日志缺失，写日志本身也可能增加请求耗时。

## Trace
stats 查询预算：未指定 operation 时发现 server 操作并逐个查询，默认每个 1500 条；指定 operation 时默认 5000 条。stats 不再接受 limit。meta.per_operation_limit 表示实际预算，operation_queries 记录各操作 success/failed/skipped、raw_trace_count 和 limit_reached；失败/跳过不代表零请求，部分失败时整体统计不完整。概览触顶后指定接口重查，仍触顶再缩小时间窗口；不直接累加多次查询的统计。search 的 limit/fetch_limit 保持不变。
query_trace_stats：候选按指定服务的 server 入口过滤，再按 service/operation 聚合，范围为入口及其后代，不包含上游或旁支。多根、缺失上游时仍统计已识别入口并提示不完整。total_calls 按 (trace_id, entry_span_id) 计数，meta.fetched_traces 表示候选 Trace 数；同一 Trace 可有多次入口调用。默认单个服务由 TRACE_ENTRY_SERVICE 配置，初始为 ops-agent-backend，可传 service 覆盖。downstream_error_services 按每次入口调用去重汇总下游有效错误服务，不代表根因或下游自身错误率；跨服务不可相加。百分位仅针对本次样本。
search_traces：指定服务自己的 server 入口、耗时、状态筛选，不要求全局根；min_duration_ms 下推 Jaeger 后再按目标入口验证。每行以 trace_id+entry_span_id 区分。fetched_count 是 Trace 数，matched_count/returned_count 是入口调用数；不受上游或兄弟分支错误影响。
get_trace_detail：按 trace_id 展示全局树及缺少父节点的 fragments，默认 50 节点，上限 200，共享预算；truncated/incomplete/warnings 提醒裁剪和结构缺失。各节点 status_desc 与 error 分别保留。

## 状态和耗时
classifyStatus 不再对 4xx 直接判 ok。选中入口有效错误或 HTTP 5xx 为 failed，仅后代有有效错误为 degraded，否则为 ok。只排除同一服务 mysql.Create/Update 的 user.duplicate=true 调用内已明确识别的 MySQL 重复键错误，其他错误仍参与统计；detail 用 expected_error 标注但不删除原始错误。ok 不代表业务成功或没有客户端错误；degraded 不证明执行了某种业务降级，也不保证请求慢。
根 duration_ms 是根 Span 耗时；start_offset_ms 相对根开始；self_ms 是扣除直接子区间并集后的未覆盖时间，不是 CPU 时间。并行耗时不能相加。
error_summary 是目标入口子树按时间排序、先后代后自身深度优先选择的第一个有效错误，service/span_id/operation/message 来自同一节点，不是全部错误、全局最早错误或已确认根因。详情中只包括已采集、已解析、未裁剪的节点。没有唯一根时顶层状态 unknown，start_ms 与偏移参考最早片段开始时间。

## 能做和不能做
六个工具只读日志与 Trace，不能直接执行 SQL、Redis 命令、队列管理、容器操作或修复。消费者日志未接入观测库，不能用业务 trace_id 还原消费全链路。
空结果时先检查时间窗、service、入口名称、候选截断和数据源错误；工具失败不是业务无异常。HTTP 404 的 Trace 详情表示没有可返回链路，不证明请求从未发生。

## 代码依据
以下路径相对 ops-agent 仓库根目录；Trace 口径已按多服务第一版工作区代码更新，未作为历史事故记录。运行配置、代码变更或新证据与本文不一致时，应重新核对。
- `ops-agent-backend/internal/observability/recorder.go`
- `ops-agent-backend/internal/observability/middleware.go`
- `obs-api/internal/tracestore/analyze.go`
- `obs-api/internal/tracestore/search.go`
- `obs-api/internal/tracestore/detail.go`
- `obs-api/internal/tracestore/jaeger.go`
- `ops-diagnosis-agent/langgraph_tools.py`
