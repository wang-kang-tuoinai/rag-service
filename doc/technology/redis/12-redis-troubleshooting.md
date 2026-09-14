---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/12-redis-troubleshooting.html
---

# Redis 故障排查指南

本文介绍 Redis 常见问题的排查方法。

## 启动问题

### Redis 无法启动

**检查日志** ：
    
    
    tail -f /var/log/redis/redis-server.log
    # 或
    redis-server /etc/redis/redis.conf --loglevel debug
    

**常见问题** ：

  1. **端口被占用**
         
         # Creating Server TCP listening socket *:6379: bind: Address already in use
         

解决：找到占用端口的进程并停止，或更改 Redis 端口

  2. **权限问题**
         
         # Can't open the append-only file: Permission denied
         

解决：确保 Redis 用户对数据目录有读写权限

  3. **内存不足**
         
         # Can't allocate memory
         

解决：增加内存或调整 `maxmemory` 设置

  4. **AOF 文件损坏**
         
         # Bad file format reading the append only file
         

解决：使用 `redis-check-aof --fix` 修复

## 连接问题

### 无法连接到 Redis

**检查步骤** ：

  1. **Redis 是否运行** ：
         
         redis-cli ping
         # 应返回 PONG
         

  2. **检查端口** ：
         
         netstat -tlnp | grep redis
         ss -tlnp | grep redis
         

  3. **防火墙设置** ：
         
         sudo iptables -L -n | grep 6379
         sudo ufw status
         

  4. **绑定地址** ： 检查 `redis.conf` 中的 `bind` 配置。如果绑定到 `127.0.0.1`，只能从本地连接。

  5. **保护模式** ： 如果 Redis 未设置密码且绑定到所有接口，会进入保护模式，拒绝外部连接。

### 连接数过多
    
    
    # 查看当前连接数
    redis-cli info clients
    
    # 查看连接详情
    redis-cli client list
    

**解决** ：

  * 增加 `maxclients` 配置
  * 检查是否有连接泄漏（未关闭的连接）
  * 使用连接池
  * 检查 `timeout` 配置，确保空闲连接会被关闭

## 性能问题

### 响应缓慢

**诊断步骤** ：

  1. **检查延迟** ：
         
         redis-cli --latency
         redis-cli latency doctor
         

  2. **检查慢查询** ：
         
         redis-cli slowlog get 10
         

  3. **检查内存交换** ：
         
         redis-cli info memory | grep used_memory_rss
         # 如果 used_memory_rss 远大于 used_memory，可能存在交换
         

  4. **检查 CPU 使用** ：
         
         top -p $(pgrep redis-server)
         

  5. **检查持久化** ：
         
         redis-cli info persistence
         # 检查是否有正在进行的 bgsave 或 aof rewrite
         

### 内存使用过高

**诊断** ：
    
    
    redis-cli info memory
    redis-cli --bigkeys
    redis-cli memory stats
    

**解决** ：

  * 设置 `maxmemory` 限制
  * 配置逐出策略
  * 优化数据结构（见内存优化指南）
  * 删除不必要的数据
  * 启用主动碎片整理

### 高 CPU 使用

**诊断** ：
    
    
    # 使用 perf 分析
    sudo perf top -p $(pgrep redis-server)
    
    # 使用 MONITOR（谨慎使用，会影响性能）
    redis-cli monitor
    

**常见原因** ：

  * 大量复杂查询
  * 大键值操作
  * 持久化操作
  * Lua 脚本执行时间过长

## 数据问题

### 数据丢失

**可能原因** ：

  1. **未启用持久化**

     * 检查 `redis-cli info persistence`
     * 确保 `rdb_bgsave_in_progress` 或 `aof_enabled` 不为 0
  2. **AOF 被截断**

     * 检查日志中的 AOF 相关错误
     * 使用 `redis-check-aof` 检查 AOF 文件
  3. **主节点故障转移**

     * 如果主节点未持久化，故障转移后数据可能丢失
     * 确保主节点启用持久化
  4. **maxmemory 逐出**

     * 检查 `evicted_keys` 统计
     * 调整 `maxmemory-policy`

### 数据不一致

**复制延迟** ：
    
    
    redis-cli info replication
    # 检查 master_repl_offset 和 slave_repl_offset 差异
    

**解决** ：

  * 检查网络延迟
  * 检查副本负载
  * 考虑使用同步复制（WAIT 命令）

## 持久化问题

### RDB 保存失败

**检查** ：
    
    
    redis-cli info persistence
    # 检查 rdb_last_bgsave_status
    

**常见原因** ：

  * 磁盘空间不足
  * 权限问题
  * `fork()` 失败（内存不足）
  * 磁盘 I/O 错误

### AOF 重写失败

**检查** ：
    
    
    redis-cli info persistence
    # 检查 aof_last_bgrewrite_status
    

**解决** ：

  * 检查磁盘空间
  * 检查权限
  * 手动触发重写：`redis-cli bgrewriteaof`

## 集群问题

### 集群节点无法通信

**检查** ：
    
    
    redis-cli cluster nodes
    redis-cli cluster info
    

**常见问题** ：

  * 端口未开放（需要数据端口和集群总线端口）
  * 防火墙阻止
  * NAT/端口映射问题
  * 节点 ID 冲突

### 集群槽分配问题
    
    
    # 检查槽分配
    redis-cli cluster slots
    
    # 修复集群
    redis-cli --cluster fix <node-ip>:<port>
    

### 脑裂（Split-brain）

当网络分区导致多个节点认为自己是主节点时发生。

**解决** ：

  * 检查网络连接
  * 使用 CLUSTER FAILOVER 手动故障转移
  * 必要时使用 CLUSTER RESET

## 日志分析

### 启用详细日志
    
    
    redis-cli config set loglevel debug
    

### 常见日志消息

日志消息 | 含义 | 解决  
---|---|---  
`WARNING overcommit_memory is set to 0!` | 内核 overcommit 设置不正确 | `echo 1 > /proc/sys/vm/overcommit_memory`  
`WARNING you have Transparent Huge Pages enabled` | 透明大页可能导致延迟 | 禁用透明大页  
`OOM command not allowed` | 达到 maxmemory 限制 | 增加内存或配置逐出策略  
`Can't save in background: fork: Cannot allocate memory` | fork 失败 | 启用 overcommit 或减少内存使用  
`SLOWLOG: Slow query detected` | 慢查询 | 优化查询或数据结构  
  
## 使用 redis-cli 诊断工具
    
    
    # 检查服务器状态
    redis-cli info
    
    # 检查所有信息
    redis-cli info all
    
    # 实时监控
    redis-cli --stat
    
    # 扫描大键
    redis-cli --bigkeys
    
    # 扫描内存使用
    redis-cli --memkeys
    
    # 检查延迟
    redis-cli --latency
    
    # 检查延迟历史
    redis-cli --latency-history
    
    # 检查延迟分布
    redis-cli --latency-dist
    

## 紧急恢复

### 从 RDB 恢复
    
    
    # 停止 Redis
    redis-cli shutdown
    
    # 备份当前数据
    cp dump.rdb dump.rdb.backup
    
    # 恢复旧 RDB
    cp backup.rdb dump.rdb
    
    # 启动 Redis
    redis-server /etc/redis/redis.conf
    

### 从 AOF 恢复
    
    
    # 停止 Redis
    redis-cli shutdown
    
    # 备份 AOF
    cp appendonly.aof appendonly.aof.backup
    
    # 修复 AOF
    redis-check-aof --fix appendonly.aof
    
    # 启动 Redis
    redis-server /etc/redis/redis.conf
    

### 数据迁移
    
    
    # 使用 redis-cli --cluster import
    redis-cli --cluster import <target-node> --cluster-from <source-node> --cluster-copy
    
    # 或使用 redis-shake 等工具
    

## 联系支持

如果以上方法无法解决问题：

  1. 收集以下信息：

     * Redis 版本
     * 配置文件
     * 日志文件
     * `redis-cli info all` 输出
     * 操作系统和内核版本
     * 硬件配置
  2. 在 Redis GitHub Issues 或邮件列表中寻求帮助