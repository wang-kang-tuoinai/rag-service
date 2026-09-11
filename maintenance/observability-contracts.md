---
id: arch-observability
doc_type: maintenance
project: ops-agent
service: ops-agent-backend
component: observability
deployment: docker-compose
reviewed_at: "2026-09-11"
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
query_trace_stats：候选请求按根入口聚合，百分位仅针对本次候选。query_trace_stats 工具当前固定 service=ops-agent-backend。
search_traces：入口、根耗时、状态筛选；min_duration_ms 下推 Jaeger minDuration，再校验根耗时；fetch_limit 限制候选，limit 限制摘要，排序不是全窗口 Top N。
get_trace_detail：按 trace_id 展示树，默认 50 节点，上限 200；truncated/warnings 提醒裁剪和结构缺失。各节点 status_desc 与 error 分别保留。

## 状态和耗时
当前 classifyStatus 首先将根 HTTP 4xx 归为 ok；其余根出错为 failed、仅后代出错为 degraded、均未标错为 ok。ok 不代表没有客户端错误；degraded 不证明执行了某种业务降级，也不保证请求慢。
根 duration_ms 是根 Span 耗时；start_offset_ms 相对根开始；self_ms 是扣除直接子区间并集后的未覆盖时间，不是 CPU 时间。并行耗时不能相加。
error_summary 是深度优先选择的一条代表性错误，不是全部错误或已确认根因。详情中也只包括已采集、已解析、未裁剪的节点。

## 能做和不能做
六个工具只读日志与 Trace，不能直接执行 SQL、Redis 命令、队列管理、容器操作或修复。消费者日志未接入观测库，不能用业务 trace_id 还原消费全链路。
空结果时先检查时间窗、service、入口名称、候选截断和数据源错误；工具失败不是业务无异常。HTTP 404 的 Trace 详情表示没有可返回链路，不证明请求从未发生。

## 代码依据
以下路径相对 ops-agent 仓库根目录；内容依据 2026-09-11 工作区代码静态核对，未作为已验证事故记录。运行配置、代码变更或新证据与本文不一致时，应重新核对。
- `ops-agent-backend/internal/observability/recorder.go`
- `ops-agent-backend/internal/observability/middleware.go`
- `obs-api/internal/tracestore/analyze.go`
- `obs-api/internal/tracestore/search.go`
- `obs-api/internal/tracestore/detail.go`
- `obs-api/internal/tracestore/jaeger.go`
- `ops-diagnosis-agent/langgraph_tools.py`
