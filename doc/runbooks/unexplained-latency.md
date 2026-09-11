---
id: runbook-unexplained-latency
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: application
deployment: docker-compose
---

# 依赖节点不慢但接口耗时高

## 适用范围与症状
ops-agent-backend 的 HTTP 请求较慢，但详情中已展示的 Redis/MySQL 节点不能解释全部耗时。

## 项目行为与证据线索
POST /api/v1/users 的密码哈希在 handler.create.user 内执行，当前没有单独的 bcrypt Span。
业务结构化日志使用请求 context 同步写入观测数据库，写入等待可能增加请求耗时；这属于业务请求路径中的候选因素，不代表已经证明观测数据库慢。
self_ms 表示未被直接子节点区间覆盖的时间，可能包含计算、未埋点等待和其他代码，不是 CPU 时间。

## Agent 可执行的只读验证
1. query_trace_stats 定位慢入口，search_traces 用 operation 和 min_duration_ms 获取实际慢请求，不仅查 failed/degraded。
2. get_trace_detail 比较根节点、Handler 和依赖节点的耗时及 start_offset_ms，寻找未覆盖时间集中在哪一层。
3. 若 truncated，增加 max_spans（最多 200），避免把未展示的子节点误认为没有发生；self_ms 仍按裁剪前的树计算。
4. search_logs(trace_id=实际ID) 补充请求状态、缓存分支和异常，比较同入口多次请求，区分偶发等待与重复模式。
5. 给出已观察到的耗时分布和待验证假设，不直接给出 CPU 或数据库根因。

## 需要人工补充的检查
如果 POST 的 Handler 未覆盖时间较高，人工使用性能分析确认是否来自密码哈希；如怀疑同步写日志，测量对应写入延迟。当前观测工具无法执行 CPU profile 或直接查询数据库等待指标。

## 处理建议、影响与恢复验证
先补充测量再选择优化。密码哈希是安全相关步骤，不应仅为降低延迟随意降低成本。日志异步化会改变缓冲、丢失和退出刷新语义，需要单独设计。改动后以同入口、相近负载比较多次请求耗时，并验证业务结果。

## 不能据此得出的结论
self_ms 高不证明 CPU 使用高；依赖节点看起来正常不证明没有未埋点依赖等待。单次慢请求不能代表整体性能。
