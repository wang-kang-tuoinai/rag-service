---
id: runbook-expected-4xx-bloom
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: application
deployment: docker-compose
---

# 重复用户、用户不存在与布隆拦截

## 适用范围与症状
创建/更新 409，详情/删除 404，或 Trace 内数据库异常但顶层 status=ok。

## 项目行为与证据线索
GORM 开启 TranslateError，重复键转换 ErrDuplicateUser → 409、INFO `duplicate user creation attempt`。用户不存在 → 404、INFO `user not found`。布隆拒绝另记 `request blocked by bloom filter for {id}`，实际 attrs 使用 user_id，不要按占位符 id 假设字段存在。

## Agent 可执行的只读验证
1. search_logs 查看具体 access attrs.status 与业务模板，不仅看 ERROR。
2. 4xx 不再直接判为 ok：只排除已确认的 MySQL 重复键业务冲突，同一请求的 Redis 超时等其他异常仍参与分类。已知 Trace 直接 get_trace_detail，检查 user.duplicate、user.isExist，以及数据库节点的 expected_error；原始重复键错误仍保留。
3. 布隆拦截时可能没有 Redis/MySQL 查询；检查输入是否规范十进制 ID。
4. 查询同窗口是否还有真正 500，不把客户端冲突和服务端故障合并统计。

## 需要人工补充的检查
人工确认用户唯一约束、实际数据库记录及启动时 ID 加载是否成功。外部插入或非规范 ID 字符串可与布隆集合不同。

## 处理建议、影响与恢复验证
重复用户按业务语义处理，不重建数据库。若确认过滤器与数据库不同步，再评估重载方案；重启有服务中断且需依赖就绪，不作为自动动作。用规范 ID 和已知数据复核。

## 不能据此得出的结论
顶层 ok 不等于 HTTP 2xx。布隆拦截不证明数据库无此用户；数据库插件的异常标记不必然意味着服务端故障。
