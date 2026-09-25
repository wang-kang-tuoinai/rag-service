---
id: runbook-rabbitmq-publish-consume
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: rabbitmq
deployment: docker-compose
---

# 注册事件发布失败或消费者停止

## 适用范围与症状
POST 创建用户成功但出现消息 WARN；或者 RabbitMQ 恢复后消费仍不继续。

## 项目行为与证据线索
`user register event publish failed for user {user_id}` 为 WARN，handler.publish=false，handler.create.user 记录异常，但创建仍返回 200。消息 exchange=user.event、routing key=user.register、queue=email-service。消费者只打印，未真正发送邮件。

## Agent 可执行的只读验证
1. query_log_templates(level="WARN") 查发布失败；search_traces 定位 POST 的 degraded，get_trace_detail 看 handler.publish 和 error。
2. search_logs(trace_id=实际ID) 核对 user_id 与发布错误。
3. 未发现发布错误只能说未观察到该错误，不能确认队列已接收或消费成功。
4. 消费侧、队列深度不能由当前六个工具直接验证，报告应明确证据缺口。

## 需要人工补充的检查
人工查看 RabbitMQ 管理界面的连接/Channel、队列绑定与积压，查看 app 和 consumer stdout 中的连接中断、重连失败、连接及拓扑恢复成功日志。发布者和消费者均支持运行时自动重连，重试间隔从 1 秒递增至最多 30 秒；消费者重新声明队列和绑定并恢复订阅。权限、声明参数冲突等配置/协议错误会停止重试，需要修正配置。没有跨 AMQP 的 Trace Context。

## 处理建议、影响与恢复验证
确认 Broker 可用后，先检查 app/consumer 是否自动恢复，给当前退避等待及连接初始化留出时间。用新注册事件核对发布告警是否停止、队列绑定是否存在以及消费者是否继续处理。若持续无法恢复，查看连接地址、网络、权限和声明参数；出现停止恢复日志时，修正配置后再重启对应服务。既往发布失败事件无自动补发，不能保证恢复连接或重启会补齐；补发前核对事件和业务幂等。未确认的消费可能重新投递。当前无 confirms、无显式消息持久化，不能承诺无丢失。

## 不能据此得出的结论
发布函数返回 nil 不证明可靠投递或消费完成。不要因消息失败重复创建用户。不能用数据库成功推断邮件已发送；当前没有实际邮件逻辑。
