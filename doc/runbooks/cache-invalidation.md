---
id: runbook-cache-invalidation
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: redis
deployment: docker-compose
---

# 更新或删除成功但缓存失效失败

## 适用范围与症状
PUT/DELETE 返回成功伴随 WARN，或者后续查询仍看到旧数据。

## 项目行为与证据线索
数据库操作先完成，再 DEL user:<id>。DEL 失败只记录 `failed to delete cache for user {user_id}` 和 cache.del=false，不回滚数据库；缓存可能持续存在至过期。

## Agent 可执行的只读验证
1. search_traces 按 PUT 或 DELETE 入口找 degraded 或指定 trace_id。
2. get_trace_detail 检查 mysql.Update/mysql.Delete 和 cache.Update/cache.Delete 的错误及 cache.del 属性。
3. search_logs 关联删除缓存失败模板和 user_id。
4. 查看后续 GET 的缓存命中与返回表现；单条写入 Trace 无法证明后续读到的内容。

## 需要人工补充的检查
人工核对业务库状态与对应缓存键。更新接口先加 Redis 锁：Redis 从头就不可用时可能在加锁阶段失败，尚未更新数据库，必须区分。

## 处理建议、影响与恢复验证
先确认数据库已成功变更，再评估失效单个旧缓存；恢复 Redis 后重试读取。不要盲目重复创建或执行整库清缓存，避免改变原故障和产生额外负载。

## 不能据此得出的结论
HTTP 成功不代表缓存一致性已经恢复；cache.del=false 不能证明数据库失败。
