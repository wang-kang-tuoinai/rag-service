---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/06-redis-cluster.html
---

# Redis 集群指南

Redis 使用称为 **Redis Cluster** 的部署拓扑进行水平扩展。本文介绍如何在生产环境中设置、测试和操作 Redis Cluster。

## Redis Cluster 101

Redis Cluster 提供了一种运行 Redis 安装的方式，数据自动分片到多个 Redis 节点。它还提供一定程度的分区可用性——当某些节点故障或无法通信时继续操作的能力。

### TCP 端口

每个 Redis Cluster 节点需要两个开放的 TCP 连接：

  * 客户端通信端口（如 6379）
  * **集群总线端口** ：默认数据端口 + 10000（如 16379），可通过 `cluster-port` 配置覆盖

集群总线是节点间通信通道，使用二进制协议。客户端不应尝试与集群总线端口通信。

### Redis Cluster 与 Docker

Redis Cluster 目前不支持 NAT 环境。要使 Docker 兼容 Redis Cluster，需要使用 Docker 的 **host networking mode** （`--net=host`）。

### 数据分片

Redis Cluster 不使用一致性哈希，而是使用不同的分片形式：每个键概念上属于我们称为 **哈希槽（hash slot）** 的一部分。

Redis Cluster 中有 **16384 个哈希槽** 。计算给定键的哈希槽：对键取 CRC16 后模 16384。

每个节点负责一部分哈希槽。例如 3 节点集群：

  * 节点 A：哈希槽 0-5500
  * 节点 B：哈希槽 5501-11000
  * 节点 C：哈希槽 11001-16383

添加和删除节点只需移动哈希槽，**无需停机** 。

Redis Cluster 支持多键操作，只要单个命令执行（或整个事务或 Lua 脚本执行）中涉及的所有键属于同一哈希槽。用户可使用 **哈希标签（hash tags）** 强制多键属于同一哈希槽：如果键中有 `{}` 括号内的子字符串，仅括号内的内容被哈希。例如 `user:{123}:profile` 和 `user:{123}:account` 保证在同一哈希槽。

### 主从模型

Redis Cluster 使用主从模型，每个哈希槽有 1（主节点本身）到 N 个副本（N-1 个额外副本节点）。

例如 3 主节点集群 A、B、C，各添加一个副本 A1、B1、C1：

  * 如果节点 B 故障，B1 复制 B，B 故障后集群将提升 B1 为新主节点
  * 但如果 B 和 B1 同时故障，Redis Cluster 将无法继续运行

### 一致性保证

Redis Cluster **不保证强一致性** 。在某些条件下可能丢失已被系统确认给客户端的写入。

原因：

  1. **异步复制** ：主节点 B 回复 OK 给客户端后才传播写入给副本 B1、B2、B3。如果 B 确认写入后崩溃，未能发送给副本，未收到写入的副本可能被提升为主节点，永久丢失写入
  2. **网络分区** ：客户端与少数实例（包括至少一个主节点）隔离时，客户端仍可写入旧主节点。如果分区持续时间足够长，多数端提升副本为主节点，客户端写入旧主节点的数据将丢失

可通过 WAIT 命令实现同步写入，减少丢失写入的可能性。但即使使用同步复制，Redis Cluster 也不实现强一致性。

**节点超时（node timeout）** 是重要配置：经过此时间后，主节点被认为故障，可被其副本替换。同样，主节点在节点超时时间内无法感知大多数其他主节点时，进入错误状态并停止接受写入。

## 配置参数

  * `cluster-enabled <yes/no>`：启用 Redis Cluster 支持
  * `cluster-config-file <filename>`：集群节点自动持久化集群配置的文件
  * `cluster-node-timeout <milliseconds>`：节点不可用的最长时间，超过则被认为故障
  * `cluster-slave-validity-factor <factor>`：如果为 0，副本始终认为自己有效；正值计算最大断开时间为节点超时乘以该因子
  * `cluster-migration-barrier <count>`：主节点保持连接的最小副本数，另一个副本才能迁移到无副本覆盖的主节点
  * `cluster-require-full-coverage <yes/no>`：默认 yes，如果部分键空间未被任何节点覆盖，集群停止接受写入
  * `cluster-allow-reads-when-down <yes/no>`：默认 no，集群标记为故障时节点停止服务所有流量

## 创建和使用 Redis Cluster

### 创建要求

最小集群配置（redis.conf）：
    
    
    port 7000
    cluster-enabled yes
    cluster-config-file nodes.conf
    cluster-node-timeout 5000
    appendonly yes
    

**最小集群** 必须包含至少三个主节点。强烈建议部署六节点集群（3 主 + 3 副本）。

### 创建集群
    
    
    redis-cli --cluster create 127.0.0.1:7000 127.0.0.1:7001 127.0.0.1:7002 127.0.0.1:7003 127.0.0.1:7004 127.0.0.1:7005 --cluster-replicas 1
    

`--cluster-replicas 1` 表示为每个创建的主节点创建一个副本。

或使用 `create-cluster` 脚本：
    
    
    create-cluster start
    create-cluster create  # 回复 yes
    create-cluster stop
    

### 与集群交互

使用 `redis-cli` 的集群模式：
    
    
    redis-cli -c -p 7000
    

Redis Cluster 节点能够重定向客户端到正确的节点。

### 重新分片（Reshard）
    
    
    redis-cli --cluster reshard 127.0.0.1:7000
    

非交互式：
    
    
    redis-cli --cluster reshard <host>:<port> --cluster-from <node-id> --cluster-to <node-id> --cluster-slots <number> --cluster-yes
    

### 测试故障转移

崩溃主节点：
    
    
    redis-cli -p 7002 debug segfault
    

### 手动故障转移

在要故障转移的主节点的副本上执行：
    
    
    CLUSTER FAILOVER
    

手动故障转移更安全，避免数据丢失：仅当系统确认新主节点已处理旧主节点的所有复制流后，才将客户端从旧主节点切换到新主节点。

### 添加新节点

添加空主节点：
    
    
    redis-cli --cluster add-node 127.0.0.1:7006 127.0.0.1:7000
    

添加副本：
    
    
    redis-cli --cluster add-node 127.0.0.1:7006 127.0.0.1:7000 --cluster-slave
    

指定主节点：
    
    
    redis-cli --cluster add-node 127.0.0.1:7006 127.0.0.1:7000 --cluster-slave --cluster-master-id <node-id>
    

或使用 CLUSTER REPLICATE：
    
    
    CLUSTER REPLICATE <master-node-id>
    

### 移除节点

移除副本：
    
    
    redis-cli --cluster del-node 127.0.0.1:7000 <node-id>
    

移除主节点前必须先清空（重新分片数据）。或使用手动故障转移将其变为副本后移除。

移除故障节点：
    
    
    redis-cli --cluster call 127.0.0.1:7000 cluster forget <node-id>
    

### 副本迁移

副本迁移允许副本自动从一个主节点移动到另一个无副本的主节点，提高集群可靠性。

  * 集群将尝试从副本最多的主节点迁移副本
  * 只需向集群中的单个主节点添加几个额外副本即可受益
  * 由 `cluster-migration-barrier` 配置参数控制

### 升级节点

升级副本：直接停止并重启更新版本。

升级主节点：

  1. 使用 CLUSTER FAILOVER 触发手动故障转移
  2. 等待主节点变为副本
  3. 像升级副本一样升级该节点
  4. 如需，再次触发手动故障转移将其恢复为主节点

### 迁移到 Redis Cluster

迁移步骤：

  1. 停止客户端
  2. 对所有 N 个主节点使用 BGREWRITEAOF 生成 AOF 文件
  3. 保存 AOF 文件
  4. 创建 N 个主节点、0 个副本的 Redis Cluster，确保所有节点使用 AOF 持久化
  5. 停止所有集群节点，用预先存在的 AOF 文件替换
  6. 重启集群节点
  7. 使用 `redis-cli --cluster fix` 修复集群，根据哈希槽迁移键
  8. 使用 `redis-cli --cluster check` 确认集群正常
  9. 重启使用 Redis Cluster 感知客户端库的客户端

或使用导入命令：
    
    
    redis-cli --cluster import <target-cluster-node> --cluster-from <source-node> --cluster-copy