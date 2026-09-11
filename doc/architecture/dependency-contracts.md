---
id: arch-dependencies
doc_type: architecture
project: ops-agent
service: ops-agent-backend
component: middleware
deployment: docker-compose
---

# 中间件调用预算与消息契约

## 超时是局部预算
| 操作 | 代码设置 |
|---|---|
| Redis 缓存 GET/SET/DEL | 每次 context 600ms |
| Redis 拨号/读/写 | 200ms / 300ms / 300ms |
| 更新加锁/解锁 | 每次 context 500ms；锁 TTL 4s |
| MySQL Create/Delete | 1s |
| MySQL GetById | 1500ms |
| MySQL List/Update/ListAllIDs | 2s |
这些不是接口总耗时上限，父 context、执行路径、等待与客户端行为均会影响结果。重试行为尚未确认，不据此推算固定的总等待时长。
MySQL Update 后会回读 GetById；外层操作耗时不能简单理解为一条 UPDATE SQL 的耗时。

## 消息拓扑
Exchange 为 user.event，类型 topic，durable=true。
Routing key 为 user.register，消费者队列名 email-service，durable=true，绑定相同 routing key。
消息包含 event_id、event_type、timestamp、user_id、user_name；虽然模型有 trace_id，当前创建路径未赋值，也未将 Trace Context 注入 AMQP header。

## 发布与消费边界
Publisher 使用互斥锁串行发布，创建 500ms context 传给 PublishWithContext；不能据此保证整个发布操作严格在 500ms 结束（包括等待锁和客户端实际行为）。
当前未开启 publisher confirms，mandatory=false，Publishing 未设置持久化 DeliveryMode。调用无错误不能证明已持久化、已路由或已消费，持久队列不等于消息可靠投递承诺。
发布失败不回滚用户创建，未见 outbox 或自动补发逻辑。Publisher 未实现断线后的连接/Channel 重建。
消费者手动 Ack；JSON 解析失败 Nack(requeue=false)，回调失败 Nack(requeue=true)，无次数上限；当前回调只打印并成功返回。Channel 关闭后消费循环退出，未自动恢复订阅。
