# 项目知识文档（首批）

知识正文位于 `doc/`，与已有 `docs/` 并存。包含 2 篇业务架构文档、8 篇排查手册和 5 篇 Redis 技术知识。业务文档依据 2026-09-11 代码核对；技术资料来源另见维护记录。

## 项目架构

- [用户接口调用路径与失败语义](../doc/architecture/user-request-flows.md)
- [中间件调用预算与消息契约](../doc/architecture/dependency-contracts.md)

## 排查手册

- [Redis 读取失败与数据库回源](../doc/runbooks/redis-read-fallback.md)
- [缓存未命中与缓存 JSON 损坏](../doc/runbooks/cache-miss-invalid-data.md)
- [缓存失效失败](../doc/runbooks/cache-invalidation.md)
- [更新锁冲突、加锁与解锁失败](../doc/runbooks/redis-update-lock.md)
- [MySQL 调用失败或耗时升高](../doc/runbooks/mysql-failure-slow.md)
- [重复用户、用户不存在与布隆拦截](../doc/runbooks/expected-4xx-bloom.md)
- [注册事件发布失败或消费者停止](../doc/runbooks/rabbitmq-publish-consume.md)
- [依赖节点不慢但接口耗时高](../doc/runbooks/unexplained-latency.md)

## 元数据与使用边界

Redis 技术知识：

- [客户端延迟与服务端延迟](../doc/technology/redis/latency-diagnosis.md)
- [慢日志含义与边界](../doc/technology/redis/slowlog.md)
- [大键识别与处理](../doc/technology/redis/large-keys.md)
- [过期与内存淘汰](../doc/technology/redis/expiration-eviction.md)
- [持久化延迟](../doc/technology/redis/persistence-latency.md)

技术文档使用 doc_type=technology，service=common，保留 version 和 source_url；详细来源及校正记录见 [Redis 来源清单](redis-sources.md)。

正文 front matter 保留 id、doc_type、project、service、component、deployment。源码依据、核对日期和验证状态集中记录在 [知识库维护清单](knowledge-maintenance.md)。

代码依据路径相对 ops-agent 仓库根目录。项目行为以实际部署代码、配置和观测为准；文档只提供待验证的解释，不能替代实时证据。人工检查和处理建议不意味着 Agent 已有相应执行工具或授权。

## 后续入库工作（本次未执行）

ingest.py 已改为读取 doc/ 并解析元数据、按 H2 切分。构建方式见 [入库说明](ingestion.md)；当前仅完成 dry-run，尚未实际向量化写入。

接入时需要显式增加 doc/ 来源，解析 front matter 并把元数据附到每个片段。不要仅修改目录就假定元数据已经进入 Chroma。建议架构按章节切分，手册保留症状、假设与验证步骤的联系；较长手册按排查分支拆分并重复必要适用范围。README 是维护索引，建议不作为诊断知识检索内容。

运行故障实验后，补充预期/实际证据、结果及部署版本，再更新维护清单中的验证状态。保留未知项，不填未经测量的概率或诊断准确率。知识内容引用用户字段时不录入真实密码、密钥或业务数据。
