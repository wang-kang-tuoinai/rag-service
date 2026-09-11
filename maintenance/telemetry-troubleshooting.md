---
id: runbook-telemetry-gaps-and-unexplained-latency
doc_type: maintenance
project: ops-agent
service: ops-agent-backend
component: observability
deployment: docker-compose
reviewed_at: "2026-09-11"
verification: source_review_only
---

# 观测无数据、工具失败与未解释耗时

## 适用范围与症状
日志/Trace 查询为空，obs-api 返回错误，或接口慢但已展示依赖节点不慢。
本文是依据当前代码编写的排查流程，未经过真实故障演练验收，不是历史事故结论。

## 项目行为与证据线索
结构化日志为同步写入，失败仅打印 record event failed；观测库故障可能导致记录缺失或增加耗时。Trace 查询有候选限制，Detail 有节点裁剪。obs-api /health 只检查 obs-mysql。宿主机运行 obs-api 时默认 Jaeger 服务名地址可能不可解析。

## Agent 可执行的只读验证
1. 先区分工具 HTTP 错误与成功空数组，记录错误，不把失败当成正常。
2. 统一秒级 start/end，核对 service=ops-agent-backend、真实 operation，读取 notices 的候选范围；缩小时间窗再查。
3. 已知 trace_id 直接 get_trace_detail；若 truncated 提高 max_spans（最多 200）。
4. 比较根耗时、子区间与 self_ms；POST 内 bcrypt 没有独立 Span，日志同步写入也可能形成未解释时间，只列为候选。
5. 查询相邻时间与其他入口以区分全局数据中断和局部缺失。
各工具参数沿用当前工具 schema；使用同一明确时间窗，读取 notices/warnings。下钻 trace_id 必须来自实际观测结果。

## 需要人工补充的检查
人工检查 obs-api/Jaeger/obs-mysql 状态、JAEGER_BASE_URL、OTLP 配置、标准输出与容器网络。需要 CPU profile 或数据库写日志耗时证据时，由人工补充；当前 Agent 无这些工具。

## 处理建议、影响与恢复验证
先修复采集或查询路径，再重新产生测试请求，等待批量上报后核对。缺失的历史证据不一定能补回；不要为了让诊断有答案而捏造根因。若要优化日志写入或补埋点，应作为后续代码改动。
以上处理仅是建议，不授权 Agent 执行修改操作。恢复后用相同入口的新请求核对结果，旧错误不会因修复从历史记录消失。

## 不能据此得出的结论
self_ms 不是 CPU 时间。空结果不证明无故障；/health 成功不证明 Jaeger 健康；没有依赖慢 Span 不证明依赖完全正常。

## 代码依据
路径相对 ops-agent 根目录，静态核对日期为 2026-09-11；若部署版本不同，应先重新核对。
- `ops-agent-backend/internal/observability/recorder.go`
- `ops-agent-backend/internal/observability/middleware.go`
- `ops-agent-backend/main.go`
- `obs-api/main.go`
- `obs-api/internal/tracestore/detail.go`
- `obs-api/internal/tracestore/analyze.go`
