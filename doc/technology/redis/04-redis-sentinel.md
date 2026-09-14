---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/04-redis-sentinel.html
---

# Redis Sentinel 高可用指南

Redis Sentinel 为不使用 Redis Cluster 的 Redis 提供高可用性。它还提供监控、通知功能，并充当客户端的配置提供者。

## Sentinel 功能概览

  * **监控（Monitoring）** ：Sentinel 持续检查主节点和副本实例是否正常工作
  * **通知（Notification）** ：Sentinel 可通过 API 通知系统管理员或其他程序某个 Redis 实例出现问题
  * **自动故障转移（Automatic failover）** ：如果主节点工作异常，Sentinel 可启动故障转移过程，将副本提升为主节点，重新配置其他副本使用新主节点，并通知应用程序使用新地址
  * **配置提供者（Configuration provider）** ：Sentinel 充当客户端服务发现的权威来源，客户端连接 Sentinel 以获取当前负责给定服务的 Redis 主节点地址

## Sentinel 作为分布式系统

Sentinel 设计为多个 Sentinel 进程协作运行的配置。优势包括：

  1. 故障检测在多个 Sentinel 就主节点不可用达成一致时执行，降低误报概率
  2. Sentinel 即使并非所有 Sentinel 进程都在工作也能正常运行

## Sentinel 快速入门

### 获取 Sentinel

当前 Sentinel 版本称为 **Sentinel 2** ，自 Redis 2.8 起随稳定版本发布。Sentinel 版本 1（随 Redis 2.6 发布）已弃用。

### 运行 Sentinel
    
    
    redis-sentinel /path/to/sentinel.conf
    

或直接使用 redis-server：
    
    
    redis-server /path/to/sentinel.conf --sentinel
    

**必须使用配置文件运行 Sentinel** ，因为系统会使用该文件保存当前状态以便重启时重新加载。

Sentinel 默认监听 TCP 端口 **26379** ，因此服务器必须开放此端口以接收其他 Sentinel 实例的连接。

### 部署前须知

  1. 至少需要 **三个 Sentinel 实例** 才能实现稳健部署
  2. 三个 Sentinel 实例应放置在独立故障的计算机或虚拟机上（不同物理服务器或不同可用区）
  3. Sentinel + Redis 分布式系统不保证故障期间已确认的写入被保留，因为 Redis 使用异步复制
  4. 客户端需要 Sentinel 支持
  5. 必须定期在开发环境（甚至生产环境）中测试 HA 设置
  6. **Sentinel、Docker 或其他 NAT/端口映射应谨慎混合使用** ：Docker 执行端口重映射，会破坏 Sentinel 自动发现其他 Sentinel 进程和副本列表的功能

### 配置 Sentinel

最小配置示例：
    
    
    sentinel monitor mymaster 127.0.0.1 6379 2
    sentinel down-after-milliseconds mymaster 60000
    sentinel failover-timeout mymaster 180000
    sentinel parallel-syncs mymaster 1
    

`sentinel monitor` 参数含义：
    
    
    sentinel monitor <master-name> <ip> <port> <quorum>
    

  * **quorum（法定人数）** ：需要同意主节点不可达的 Sentinel 数量，以真正标记主节点故障并启动故障转移
  * 但 quorum 仅用于**检测故障** 。要实际执行故障转移，需要 Sentinel 的**多数（majority）** 授权

例如，5 个 Sentinel 实例，quorum 设为 2：

  * 如果 2 个 Sentinel 同时认为主节点不可达，其中一个将尝试启动故障转移
  * 如果至少有 3 个 Sentinel 可达，故障转移将被授权并实际开始

### 其他 Sentinel 选项

  * `down-after-milliseconds`：实例不可达（不回复 PING 或回复错误）的时间（毫秒），Sentinel 开始认为它已宕机
  * `parallel-syncs`：故障转移后，可同时重新配置为使用新主节点的副本数量

### 部署示例

#### 示例 1：仅两个 Sentinel —— 不要这样做
    
    
    +----+         +----+
    | M1 |---------| R1 |
    | S1 |         | S2 |
    +----+         +----+
    

此设置有问题：如果 M1 所在机器停止工作，S1 也停止工作，另一端的 S2 无法授权故障转移，系统将不可用。

**请始终在三个不同的机器上部署至少三个 Sentinel。**

#### 示例 2：三台机器的基本设置
    
    
           +----+
           | M1 |
           | S1 |
           +----+
              |
    +----+    |    +----+
    | R2 |----+----| R3 |
    | S2 |         | S3 |
    +----+         +----+
    

配置：quorum = 2

如果 M1 故障，S2 和 S3 将就故障达成一致并能够授权故障转移。

可使用以下配置减轻客户端与旧主节点分区时写入丢失的问题：
    
    
    min-replicas-to-write 1
    min-replicas-max-lag 10
    

#### 示例 3：Sentinel 在客户端机器上

当只有两台 Redis 机器可用时，可将 Sentinel 放在客户端所在位置：
    
    
                +----+         +----+
                | M1 |----+----| R1 |
                |    |    |    |    |
                +----+    |    +----+
                          |
             +------------+------------+
             |            |            |
          +----+        +----+      +----+
          | C1 |        | C2 |      | C3 |
          | S1 |        | S2 |      | S3 |
          +----+        +----+      +----+
    

### Sentinel、Docker、NAT 和可能的问题

Docker 使用端口映射技术，这会在两个方面造成 Sentinel 问题：

  1. Sentinel 自动发现其他 Sentinel 不再工作，因为基于 hello 消息宣布的端口和 IP 地址可能被重映射
  2. 副本列表中的地址和端口可能不正确

**除非指示 Docker 1:1 映射端口，否则目前无法使用 Sentinel 监控部署在 Docker 中的主副本实例。**

可使用以下配置指令强制 Sentinel 宣布特定 IP 和端口：
    
    
    sentinel announce-ip <ip>
    sentinel announce-port <port>
    

Docker 可运行在 _host networking mode_ （`--net=host`），此模式下端口不重映射，不会产生问题。

### IP 地址和 DNS 名称

自 6.2 版本起，Sentinel 可选支持主机名，默认禁用。启用时需注意：

  1. 名称解析配置必须可靠且能快速解析地址
  2. 应到处使用主机名，避免混合使用主机名和 IP 地址

启用 `resolve-hostnames` 允许 Sentinel 接受主机名作为 `sentinel monitor` 命令和副本地址的一部分。 启用 `announce-hostnames` 使 Sentinel 在回复客户端、写入配置文件等时使用主机名而非 IP 地址。

## Sentinel API

Sentinel 提供 API 用于检查状态、监控主副本健康、订阅通知以及运行时更改配置。

### Sentinel 命令

  * **SENTINEL CONFIG GET`<name>`** (>= 6.2)：获取全局 Sentinel 配置参数
  * **SENTINEL CONFIG SET`<name>` `<value>`** (>= 6.2)：设置全局 Sentinel 配置参数
  * **SENTINEL CKQUORUM`<master name>`**：检查当前配置是否能达到故障转移所需的 quorum 和 majority
  * **SENTINEL FLUSHCONFIG** ：强制 Sentinel 将配置重写至磁盘
  * **SENTINEL FAILOVER`<master name>`**：强制故障转移
  * **SENTINEL GET-MASTER-ADDR-BY-NAME`<master name>`**：返回主节点的 IP 和端口
  * **SENTINEL INFO-CACHE** (>= 3.2)：返回缓存的 INFO 输出
  * **SENTINEL MASTER`<master name>`**：显示指定主节点的状态和信息
  * **SENTINEL MASTERS** ：显示监控的主节点列表及其状态
  * **SENTINEL MONITOR** ：开始监控
  * **SENTINEL REMOVE`<name>`**：停止监控
  * **SENTINEL REPLICAS`<master name>`** (>= 5.0)：显示主节点的副本列表
  * **SENTINEL SENTINELS`<master name>`**：显示主节点的 Sentinel 实例列表
  * **SENTINEL SET** ：设置监控配置
  * **SENTINEL RESET`<pattern>`**：重置匹配名称的所有主节点

### 运行时重新配置 Sentinel

  * **SENTINEL MONITOR`<name>` `<ip>` `<port>` `<quorum>`**：开始监控新主节点
  * **SENTINEL REMOVE`<name>`**：移除指定主节点
  * **SENTINEL SET`<name>` [ `<option>` `<value>` ...]**：更改特定主节点的配置参数

### 添加或移除 Sentinel

添加新 Sentinel 很简单：启动配置为监控当前活动主节点的新 Sentinel，10 秒内它将获取其他 Sentinel 和副本列表。

移除 Sentinel 较复杂：**Sentinel 永远不会忘记已见过的 Sentinel** ，即使长时间不可达。要移除 Sentinel：

  1. 停止要移除的 Sentinel 进程
  2. 向所有其他 Sentinel 实例发送 `SENTINEL RESET *` 命令
  3. 检查所有 Sentinel 就当前活动 Sentinel 数量达成一致

### Pub/Sub 消息

客户端可使用 Sentinel 作为 Redis 兼容的 Pub/Sub 服务器订阅特定事件通知：

  * **+sdown** ：实例进入主观下线（SDOWN）状态
  * **-sdown** ：实例不再处于 SDOWN 状态
  * **+odown** ：实例进入客观下线（ODOWN）状态
  * **-odown** ：实例不再处于 ODOWN 状态
  * **+failover-detected** ：检测到故障转移开始
  * **+slave-reconf-done** ：副本已与新主节点同步
  * **switch-master** ：主节点 IP 和地址已更改（**外部用户最感兴趣的消息** ）

## 故障状态：SDOWN 和 ODOWN

  * **SDOWN（主观下线）** ：单个 Sentinel 实例认为 Redis 实例不可用。当 Sentinel 在配置的 `down-after-milliseconds` 时间内未收到 PING 的有效回复时达到
  * **ODOWN（客观下线）** ：当足够数量的 Sentinel（至少达到配置的 quorum）具有 SDOWN 条件，并通过 `SENTINEL is-master-down-by-addr` 命令从其他 Sentinel 获得反馈时达到

SDOWN 不足以触发故障转移，必须达到 ODOWN 状态才能触发。

## 副本选择和优先级

当 Sentinel 准备执行故障转移时，按以下标准评估副本：

  1. 与主节点断开连接的时间
  2. 副本优先级（`replica-priority`）
  3. 已处理的复制偏移量
  4. Run ID

副本优先级配置：

  * 如果 `replica-priority` 设为 0，该副本永远不会被提升为主节点
  * 优先级数字**越低** 越受 Sentinel 青睐

## Sentinel 和 Redis 认证

### ACL 认证（Redis 6+）

Sentinel 配置需包含：
    
    
    sentinel auth-user <master-name> <username>
    sentinel auth-pass <master-name> <password>
    

### 密码认证（Redis 6 之前）

在所有实例（主节点和副本）中设置 `requirepass` 和 `masterauth`。Sentinel 配置需包含：
    
    
    sentinel auth-pass <master-name> <password>
    

### Sentinel 实例自身认证

自 Redis 6.2 起，Sentinel 实例可通过 ACL 保护：
    
    
    sentinel sentinel-user <username>
    sentinel sentinel-pass <password>
    

自 Redis 5.0.1 起支持仅密码认证：
    
    
    requirepass "your_password_here"
    

## 高级概念

### 配置纪元（Configuration epochs）

Sentinel 需要获得多数授权才能启动故障转移。被授权后，Sentinel 获得唯一的**配置纪元** 编号，用于版本控制故障转移后的新配置。

### 配置传播

故障转移成功后，Sentinel 开始广播新配置，其他 Sentinel 通过 Pub/Sub 消息在 `__sentinel__:hello` 频道上持续广播其配置版本。较大版本号总是胜过较小版本号。

### 分区下的一致性

Redis + Sentinel 整体是一个**最终一致性系统** ，合并函数是**最后故障转移获胜** ，旧主节点的数据将被丢弃以复制当前主节点的数据。

避免已确认写入丢失的唯一方法：

  1. 使用同步复制（及适当的共识算法）
  2. 使用不同版本可合并的最终一致性系统

### TILT 模式

当检测到可能降低系统可靠性的异常情况时，Sentinel 可进入特殊的"保护"模式 TILT：

  * 停止所有操作
  * 开始对 `SENTINEL is-master-down-by-addr` 请求回复否定
  * 如果一切正常持续 30 秒，则退出 TILT 模式