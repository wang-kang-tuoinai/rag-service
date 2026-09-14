---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/10-redis-latency.html
---

# Redis 延迟诊断指南

Redis 以其高性能著称，但在某些情况下可能出现高延迟。本文介绍如何诊断和解决 Redis 延迟问题。

## 测量延迟

### 使用 redis-cli 测量延迟
    
    
    # 持续测量延迟
    redis-cli --latency
    
    # 测量 100 次采样
    redis-cli --latency -i 100
    
    # 测量延迟历史（每 15 秒输出一行）
    redis-cli --latency-history
    
    # 测量延迟分布直方图
    redis-cli --latency-dist
    

### 使用内置 LATENCY 命令

自 Redis 2.8.13 起，内置延迟监控框架：
    
    
    # 查看延迟监控数据
    redis-cli latency latest
    
    # 查看延迟事件历史
    redis-cli latency history <event-name>
    
    # 查看延迟事件统计
    redis-cli latency stats <event-name>
    
    # 查看延迟事件摘要
    redis-cli latency doctor
    
    # 重置延迟监控数据
    redis-cli latency reset
    

## 常见延迟原因

### 1\. 慢命令

使用 SLOWLOG 识别慢命令：
    
    
    # 获取最近的 10 条慢查询
    redis-cli slowlog get 10
    
    # 设置慢查询阈值（微秒）
    redis-cli config set slowlog-log-slower-than 10000
    

常见慢命令：

  * KEYS：扫描整个键空间，O(N) \- HGETALL、LRANGE、SMEMBERS：返回大量数据
  * SORT：复杂排序操作
  * ZUNIONSTORE、ZINTERSTORE：集合操作

**解决方案** ：

  * 用 SCAN 替代 KEYS
  * 限制返回数据量（使用 `COUNT` 参数）
  * 优化数据结构使用

### 2\. 大键值

大键值会增加网络传输和序列化时间。

**检测** ：
    
    
    redis-cli --bigkeys
    

**解决方案** ：

  * 拆分大键为多个小键
  * 使用哈希分片
  * 压缩数据

### 3\. 内存交换（Swap）

如果 Redis 内存超出物理内存，操作系统会将部分内存交换到磁盘，导致严重延迟。

**检测** ：
    
    
    # 检查 Redis 进程的内存使用情况
    redis-cli info memory
    
    # 检查系统交换使用情况
    cat /proc/swaps
    free -m
    

**解决方案** ：

  * 增加物理内存
  * 设置 `maxmemory` 限制
  * 优化内存使用
  * 禁用交换：`sudo swapoff -a`

### 4\. 持久化阻塞

AOF 重写和 RDB 保存可能导致延迟峰值。

**检测** ：
    
    
    redis-cli info persistence
    

关注：

  * `rdb_last_bgsave_status`
  * `aof_last_rewrite_status`
  * `aof_last_write_status`

**解决方案** ：

  * 使用 `no-appendfsync-on-rewrite yes`（在重写期间不 fsync）
  * 调整重写触发条件
  * 使用更快的磁盘（SSD）
  * 考虑无盘复制

### 5\. 透明大页（Transparent Huge Pages）

Linux 的透明大页功能可能导致 Redis 延迟问题。

**检测** ：
    
    
    cat /sys/kernel/mm/transparent_hugepage/enabled
    

**解决方案** ：
    
    
    # 临时禁用
    echo never > /sys/kernel/mm/transparent_hugepage/enabled
    
    # 永久禁用（添加到 /etc/rc.local 或 systemd 服务）
    

### 6\. 网络问题

网络延迟和带宽限制会影响 Redis 性能。

**检测** ：
    
    
    # 使用 ping 测试网络延迟
    ping <redis-host>
    
    # 使用 iperf 测试带宽
    iperf -c <redis-host>
    

**解决方案** ：

  * 将客户端和 Redis 部署在同一数据中心
  * 使用本地连接（Unix 套接字）
  * 优化网络配置

### 7\. 系统调用延迟

某些系统调用（如 `fsync`）可能导致延迟。

**检测** ：
    
    
    # 使用 strace 跟踪系统调用
    strace -T -e trace=fsync,fdatasync -p <redis-pid>
    

**解决方案** ：

  * 调整 AOF fsync 策略
  * 使用更快的存储

### 8\. CPU 竞争

如果 Redis 与其他 CPU 密集型进程共享 CPU，可能出现延迟。

**检测** ：
    
    
    top -p <redis-pid>
    htop
    

**解决方案** ：

  * 为 Redis 分配专用 CPU
  * 使用 `taskset` 绑定 CPU
  * 隔离 Redis 服务器

## 延迟监控事件

Redis 内置延迟监控跟踪以下事件：

事件 | 说明  
---|---  
`command` | 命令执行延迟  
`fast-command` | 快速命令执行延迟  
`fork` | fork 操作延迟  
`rdb-unlink-temp-file` | 删除临时 RDB 文件  
`aof-write` | AOF 写入延迟  
`aof-write-pending-fsync` | 等待 fsync 的 AOF 写入  
`aof-write-active-child` | 子进程活跃时的 AOF 写入  
`aof-write-alone` | 无子进程时的 AOF 写入  
`aof-fsync` | AOF fsync 延迟  
`aof-rename` | AOF 重命名延迟  
`aof-close` | AOF 关闭延迟  
`aof-rewrite-diff-write` | AOF 重写差异写入  
`active-defrag-cycle` | 主动碎片整理周期  
  
## 延迟诊断流程
    
    
    1. 测量基线延迟
       └─ redis-cli --latency
    
    2. 检查是否有延迟峰值
       └─ redis-cli latency latest
    
    3. 检查慢查询
       └─ redis-cli slowlog get
    
    4. 检查内存使用情况
       └─ redis-cli info memory
    
    5. 检查持久化状态
       └─ redis-cli info persistence
    
    6. 检查系统资源
       └─ top, iostat, vmstat
    
    7. 运行 LATENCY DOCTOR
       └─ redis-cli latency doctor
    

## 最佳实践

  * 始终启用延迟监控：`CONFIG SET latency-monitor-threshold 100`
  * 定期运行 `redis-cli --latency-history` 建立延迟基线
  * 使用 LATENCY DOCTOR 获取自动诊断建议
  * 监控 `slowlog` 并优化慢查询
  * 避免在 Redis 服务器上运行其他 CPU/内存密集型进程
  * 使用 SSD 存储并确保有足够的 IOPS
  * 禁用透明大页
  * 确保 `vm.overcommit_memory = 1`