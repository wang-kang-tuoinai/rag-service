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
发布失败不回滚用户创建，未见 outbox 或自动补发逻辑。检测到连接不可用后，发布返回错误，不等待后台重连；连接恢复仅使后续发布可以继续，不会自动补发此前失败或结果不确定的消息。
消费者手动 Ack；JSON 解析失败 Nack(requeue=false)，回调失败 Nack(requeue=true)，无次数上限；当前回调只打印并成功返回。Ack/Nack 失败会退出当前消费循环并进入恢复流程。未确认的消费可能重新投递，业务处理仍需考虑幂等。

## RabbitMQ 断线恢复契约
发布者和消费者各自管理连接，运行期间监听 Connection、Channel 关闭；消费者还监听订阅取消和消息流关闭。可恢复故障触发后台重连，间隔依次为 1、2、4、8、16、30 秒，此后保持 30 秒，恢复成功后重置退避间隔。恢复时间还包含故障检测、连接建立和拓扑声明耗时，30 秒不是恢复总耗时上限。
每次恢复都会重新建立 Connection、Channel 并声明 Exchange；消费者还会重新声明 Queue、Binding 并订阅。每个 Consumer 管理一个订阅，上一代消费循环退出后才开始下一代。
权限、声明参数冲突等被判定为不可恢复的服务端配置/协议错误会停止重试，需人工修正配置后重启对应服务。应用退出时停止重连并关闭连接，不会因主动关闭再次重连。
连接中断、重连失败、连接及拓扑恢复成功日志输出到 app/consumer stdout；当前观测工具不能直接读取这些日志或确认消费恢复，需人工补充检查。看到恢复日志也不能证明此前发布失败的消息已补齐或所有消息已消费。
