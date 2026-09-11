---
id: runbook-cache-miss-invalid-data
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: redis
deployment: docker-compose
---

# 缓存未命中与缓存 JSON 损坏

## 适用范围与症状
用户详情频繁查库，或缓存命中后返回 500。

## 项目行为与证据线索
正常 redis.Nil 记录 DEBUG `cache miss for user {user_id}`，回源后尝试回填，TTL 10 分钟。读取成功设置 cache.hit=true 后才反序列化；解析失败返回 ErrCache，不回源，可能出现 `internal server error in cache`。回填失败模板为 `failed to store cache for user {user_id}`。

## Agent 可执行的只读验证
1. get_trace_detail 区分 cache.hit=false 的回源和 cache.hit=true 的 JSON 解析异常。
2. search_logs(trace_id=实际ID) 查 attrs.err，必要时用 query_log_templates(level="DEBUG") 查看 miss，WARN 查看 store failed。
3. 比较同一用户的多个独立请求；工具无缓存命中率计数器，不把单次样例当成整体命中率。

## 需要人工补充的检查
人工读取对应 user:<id> 内容和 TTL，确认数据是否符合 CachedUser JSON；不要把用户信息复制进公共知识文档。核对是否有其他写入者或反复过期。

## 处理建议、影响与恢复验证
若确认单个缓存损坏，人工评估后只失效受影响键，由后续读取回源重建；会暂时增加数据库负载，不清空整个 Redis。修复写入源后再验证连续查询。

## 不能据此得出的结论
未命中属于正常缓存行为，不等于连接失败。cache.hit=true 不保证反序列化成功。没有 Redis 键证据不能认定有人写坏缓存。
