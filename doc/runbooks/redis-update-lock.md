---
id: runbook-redis-update-lock
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: redis
deployment: docker-compose
---

# 更新锁冲突、加锁失败与解锁失败

## 适用范围与症状
PUT /api/v1/users/:id 返回 409/500，或成功后出现锁释放 WARN。

## 项目行为与证据线索
锁键 lock:user:<id>，TTL 4 秒，加锁/解锁各 500ms context。SetNX=false 返回 ErrLockConflict，HTTP 409、`distributed lock conflict`。Redis 命令错误导致未预期 500，handler.lock=false。解锁使用令牌校验 Lua；失败记录 `distributed lock release failed for {lock_key}`，不改成功响应。

## Agent 可执行的只读验证
1. query_log_templates 查看冲突或释放失败模板；409 在当前 Trace 分类中可能为 ok，不要只查 failed。
2. search_traces 定位 PUT 请求；get_trace_detail 检查 handler.update.user、handler.lock、handler.unlock 及 Redis 异常。
3. search_logs(trace_id=实际ID) 区分锁已占用、连接失败、令牌不匹配或过期的错误说明。
4. 确认加锁失败的请求没有继续进入 mysql.Update。

## 需要人工补充的检查
人工查看并发请求、锁 TTL、请求是否超过锁持有时间。解锁返回 0 可能是锁过期或持有者变化，不能只归因于 Redis 宕机。

## 处理建议、影响与恢复验证
正常竞争可降低同用户并发并让调用方适度重试。基础设施错误先修复依赖。不要直接删除未确认归属的锁；TTL 和长事务策略需代码评估。恢复后确认更新成功、无重复释放失败。

## 不能据此得出的结论
409 不是数据库崩溃；解锁失败不代表更新失败。4 秒锁没有自动续租保证。
