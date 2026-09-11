---
id: arch-system
doc_type: maintenance
project: ops-agent
service: ops-agent-backend
component: system
deployment: docker-compose
reviewed_at: "2026-09-11"
verification: source_review_only
---

# 系统架构与部署边界

## 适用范围
当前示例业务是用户 CRUD，不包含订单、支付或库存服务。本文描述代码和 Compose 配置，不证明这些服务当前正在运行。

## 服务职责与数据流
- ops-agent-backend（Compose 服务 app，HTTP 8080）：用户业务，MySQL 持久化，Redis 缓存及更新锁，发布注册事件。
- consumer：独立进程，消费用户注册事件；当前回调仅打印信息，不实际发送邮件。
- obs-api（容器 8081，宿主机 8082）：查询 observability 库日志、查询 Jaeger 并分析 Trace，提供六个只读观测工具接口。
- ops-diagnosis-agent：LangGraph 调用观测工具；当前根 Compose 未编排此服务。
- rag-service：文档索引、召回和精排及原有问答；rag-gateway 是其 HTTP 入口和静态页面宿主，宿主机 8081。诊断 Agent 的知识检索接入属于后续工作。

业务链：HTTP → Handler → CacheUserRepository → MySQL；Redis 参与缓存和更新锁。注册成功后尝试发布 RabbitMQ 事件。
观测链：业务 Recorder → obs-mysql → obs-api；OpenTelemetry → Jaeger → obs-api → 诊断 Agent。消费者不在这条结构化日志/Trace 链中。

## 存储和配置
| 组件 | 配置或数据 |
|---|---|
| mysql | 镜像 mysql:8，业务库 ops_agent，宿主机 3306 |
| obs-mysql | 镜像 mysql:8，观测库 observability，宿主机 3307 |
| redis | 镜像 redis:7，缓存 user:<id>、锁 lock:user:<id> |
| rabbitmq | 镜像 rabbitmq:3-management，AMQP 5672、管理界面 15672 |
| jaeger | 镜像 1.76.0，查询 UI 16686、OTLP HTTP 4318 |
镜像的大版本标签不代表当前容器精确补丁版本；需要人工确认实际镜像。文档不记录连接密码或模型密钥。

## 网络与启动边界
容器内用服务名访问依赖；宿主机进程应使用映射端口。obs-api 默认 JAEGER_BASE_URL 为 http://jaeger:16686，宿主机运行时需核对该配置。OBS_API_BASE 是诊断工具访问 obs-api 的地址。
app 启动会连接业务 MySQL、加载用户 ID 到布隆过滤器并连接 RabbitMQ。业务 MySQL 或 RabbitMQ 初始化最终失败会退出。obs-mysql 初始化失败后的代码仍有后续数据库调用，不能承诺完整的故障降级。
Compose 中 app 未显式等待 obs-mysql 健康；obs-api 的 /health 仅检查观测数据库，不能代表 Jaeger、业务依赖或模型可用。

## 代码依据
以下路径相对 ops-agent 仓库根目录；内容依据 2026-09-11 工作区代码静态核对，未作为已验证事故记录。运行配置、代码变更或新证据与本文不一致时，应重新核对。
- `docker-compose.yml`
- `ops-agent-backend/main.go`
- `obs-api/main.go`
- `obs-api/internal/router/router.go`
- `ops-agent-backend/cmd/consumer/main.go`
- `ops-diagnosis-agent/langgraph_tools.py`
- `rag-service/ingest.py`
