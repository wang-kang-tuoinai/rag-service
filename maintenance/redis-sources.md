# Redis 技术语料来源与核对记录

核对日期：2026-09-13。正文为独立编写的精简诊断知识，不是原文全文转载、性能保证或已经验证的项目事故。适用范围为 Redis 7.x 单机的相关基础机制；官方 latest 页面可能包含更新版本内容，已避开其新增功能。实际补丁版本与参数需按部署确认。

## 用户提供资料

- [技术自由圈：Redis 突然变慢](https://www.cnblogs.com/crazymakercircle/p/19053755)：已读取，用于选择延迟、慢命令、大键和持久化主题；技术结论以官方资料核对。
- [Redis 最佳实践](https://redis.com.cn/best-practices.html)：多次读取失败，未将其未获取正文作为依据，后续可补充本地副本。
- [weixin_42201180：过期策略与内存淘汰](https://blog.csdn.net/weixin_42201180/article/details/129150967)：已读取，用于过期与淘汰主题。原页面声明 CC BY-SA 4.0；本批不复制其正文、代码或图示，按官方语义独立整理。

## 主题与官方核对

| 知识文档 | 核对来源 |
|---|---|
| latency-diagnosis.md | [延迟诊断](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/) |
| slowlog.md | [SLOWLOG GET](https://redis.io/docs/latest/commands/slowlog-get/) |
| large-keys.md | [MEMORY USAGE](https://redis.io/docs/latest/commands/memory-usage/)、[SCAN](https://redis.io/docs/latest/commands/scan/)、[UNLINK](https://redis.io/docs/latest/commands/unlink/) |
| expiration-eviction.md | [EXPIRE](https://redis.io/docs/latest/commands/expire/)、[TTL](https://redis.io/docs/latest/commands/ttl/)、[淘汰策略](https://redis.io/docs/latest/develop/reference/eviction/) |
| persistence-latency.md | [持久化](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/) |

正文位置为 doc/technology/redis/。source_url 指向主要核对来源，其余来源在此维护。service=common 表示通用技术机制，不冒充 ops-agent-backend 已实现的业务行为。

## 未采纳或修正的表述

- 未清理的过期键仍可 GET 到：不采用；普通访问会检查过期。
- maxmemory-samples 决定主动过期抽样数量：不采用；不能与淘汰采样混淆。
- intrinsic-latency 测 Redis 实例请求响应：修正为宿主机调度延迟测量，不连接 Redis。
- latency 单独测排队时间：不采用，它不能单独分离请求的各个耗时环节。
- 大键立即切换 volatile-ttl、关闭刷盘或全局 swapoff 的通用止血流程：不作为默认建议，处理需匹配证据及数据用途。
- 固定 QPS、延迟倍数、键大小阈值及无来源事故数字：未录入。

本次只准备文档并使入库/查询允许 technology 类型，不重建向量库、不执行 Redis 命令。后续需要实际入库及检索评测。
