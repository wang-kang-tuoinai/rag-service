---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/01-redis-administration.html
---

# Redis 生产环境管理指南

本文提供在生产环境中配置和管理 Redis 的建议。

## Linux 系统设置建议

  * **使用 Linux 部署 Redis** 。Redis 也在 OS X 上测试，偶尔在 FreeBSD 和 OpenBSD 上测试。但 Linux 是大多数压力测试和生产部署运行的平台。

  * **设置内核 overcommit_memory 为 1** 。在 `/etc/sysctl.conf` 中添加 `vm.overcommit_memory = 1`，然后重启或运行 `sysctl vm.overcommit_memory=1` 激活设置。

  * **禁用透明大页（Transparent Huge Pages）** 。运行以下命令：
        
        echo never > /sys/kernel/mm/transparent_hugepage/enabled
        

## 内存管理建议

  * **确保启用了 swap** ，且 swap 文件大小等于系统内存总量。如果 Linux 没有设置 swap，Redis 实例意外消耗过多内存时可能会崩溃，或被 Linux 内核 OOM killer 杀死。

  * **设置明确的`maxmemory` 限制**。确保 Redis 在接近系统内存限制时报错而不是崩溃。计算时要考虑 Redis 的数据开销和碎片开销。例如，如果你有 10 GB 空闲内存，建议设置为 8 或 9 GB。

  * **注意写密集型应用的内存峰值** 。在保存 RDB 文件或重写 AOF 日志时，Redis 可能使用高达正常内存 2 倍的内存。额外内存使用量与保存过程中被写入修改的内存页数量成正比。

  * 使用 LATENCY DOCTOR 和 MEMORY DOCTOR 命令辅助故障排查。

## 镜像部署建议

  * 在 daemontools 下运行时，使用 `daemonize no`。

## 复制（Replication）建议

  * **设置合理的复制积压缓冲区（replication backlog）** 。缓冲区大小应与 Redis 使用的内存量成比例，使副本（replica）更容易与主节点（master）同步。

  * **如果禁用持久化但使用复制，启用无盘复制（diskless replication）** 。因为 Redis 即使禁用持久化也会执行 RDB 保存来服务副本同步。

  * **确保主节点启用持久化，或崩溃后不会自动重启** 。因为副本会尝试维护主节点的精确副本，如果主节点以空数据集重启，副本也会被清空。

## 安全建议

  * 默认情况下 Redis 不需要任何认证并监听所有网络接口。如果将 Redis 暴露在互联网上是非常严重的安全问题。请参考 Redis 安全页面了解如何保护 Redis。

## 不停机升级或重启 Redis 实例

Redis 设计为服务器上的长期运行进程。你可以使用 CONFIG SET 命令修改许多配置选项而无需重启。也可以在不停机的情况下在 AOF 和 RDB 快照持久化之间切换。

如果需要重启（例如升级 Redis 版本），按以下步骤避免停机：

  1. 将新的 Redis 实例设置为当前实例的副本。
  2. 如果使用单台服务器，确保副本在不同端口启动。
  3. 等待复制初始同步完成，检查副本日志文件。
  4. 使用 INFO 确保主节点和副本键数量相同。使用 `redis-cli` 检查副本工作正常。
  5. 使用 `CONFIG SET slave-read-only no` 允许写入副本。
  6. 将所有客户端配置为使用新实例。可以使用 CLIENT PAUSE 确保切换期间没有客户端写入旧主节点。
  7. 确认旧主节点不再接收查询后，使用 `REPLICAOF NO ONE` 将副本提升为主节点，然后关闭旧主节点。

如果使用 Redis Sentinel 或 Redis Cluster，最简单的方式是逐个升级副本，然后手动故障转移将升级后的副本提升为主节点，最后升级最后一个副本。

> **注意** ：Redis Cluster 4.0 在集群总线协议级别与 Redis Cluster 3.2 不兼容，因此这种情况下需要大规模重启。但 Redis 5 集群总线与 Redis 4 向后兼容。