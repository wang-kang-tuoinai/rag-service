---
id: runbook-redis-read-fallback
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: redis
deployment: docker-compose
---

# Redis 读取失败与数据库回源

## 适用范围与症状
GET /api/v1/users/:id 返回成功但出现 WARN、degraded 或变慢。列表 GET /api/v1/users 不走 Redis 读取，此手册不直接适用。

## 项目行为与证据线索
`failed to read cache for user {user_id}`（WARN），attrs.err、component=redis；cache.GetById 可出现 cache.hit=false 和异常。非 redis.Nil 的读取错误会回源 MySQL，成功后直接返回，不回填。

## Agent 可执行的只读验证
1. 已知入口可用 search_traces(operation=实际入口, status="degraded")；若问题是慢，另按 min_duration_ms 查询，不强制限定 degraded。
2. get_trace_detail 查看 Redis 错误与 mysql.GetById 是否同一请求，记录根状态和耗时。
3. search_logs(trace_id=实际ID) 检查读取失败模板与 attrs.err；日志不足时不要限制为 ERROR，读取失败是 WARN。
4. 若返回 500，检查 MySQL 回源是否也失败，而不是仅看 Redis 摘要。

## 需要人工补充的检查
核对 REDIS_ADDR、容器状态、连通性、实际错误类型和客户端配置。需要 Redis 侧检查时由人工完成；Agent 当前不能查询 Redis 运行状态。

## 处理建议、影响与恢复验证
按证据修复 Redis 地址或服务连通性。回源会增加数据库请求，需要同时观察 MySQL 路径。修复后连续查询一个已存在且规范 ID 的用户，核对错误停止且缓存命中恢复。

## 不能据此得出的结论
cache.hit=false 也可能是正常未命中；仅凭该属性不能认定 Redis 故障。Redis 错误不一定导致 HTTP 失败，也不能只凭超时确定网络是根因。
