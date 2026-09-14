---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/08-redis-benchmarks.html
---

# Redis 基准测试指南

## 快速基准测试

Redis 包含 `redis-benchmark` 工具，模拟来自 N 个客户端同时发送 M 个查询的命令（类似 Apache 的 `ab` 工具）。

### 基本用法
    
    
    # 在本地运行，使用默认参数（50 个客户端，每个 100000 次请求）
    redis-benchmark
    
    # 指定主机和端口
    redis-benchmark -h 127.0.0.1 -p 6379 -t set,lpush -n 100000 -q
    

### 常用选项

选项 | 说明  
---|---  
`-h <hostname>` | 服务器主机名（默认 127.0.0.1）  
`-p <port>` | 服务器端口（默认 6379）  
`-s <socket>` | 服务器套接字  
`-a <password>` | 认证密码  
`-c <clients>` | 并发连接数（默认 50）  
`-n <requests>` | 总请求数（默认 100000）  
`-d <size>` | 键值大小（字节，默认 3）  
`-t <tests>` | 仅运行逗号分隔的测试  
`-q` | 安静模式，仅显示 QPS  
`--csv` | 以 CSV 格式输出  
`-l` | 循环运行基准测试  
`-P <numreq>` | 使用管道（pipeline）发送 numreq 个请求  
  
### 测试示例
    
    
    # 仅测试 SET 和 LPUSH 命令，安静模式
    redis-benchmark -t set,lpush -q
    
    # 使用管道发送 16 个命令
    redis-benchmark -n 1000000 -t set,get -P 16 -q
    
    # 使用 100 字节大小的值
    redis-benchmark -d 100 -t set,get -n 100000 -q
    
    # 使用 100 个并发连接
    redis-benchmark -c 100 -t set,get -n 100000 -q
    

### 管道（Pipeline）

管道是 Redis 客户端的重要优化。`redis-benchmark` 支持通过 `-P` 选项测试管道性能：
    
    
    # 不使用管道（默认）
    redis-benchmark -t set -n 1000000 -q
    
    # 使用管道 16 个命令
    redis-benchmark -t set -n 1000000 -P 16 -q
    

管道能显著提升吞吐量，因为减少了网络往返时间（RTT）。

## 影响基准测试结果的因素

  1. **网络延迟** ：客户端与服务器之间的网络延迟对结果影响巨大。建议在本地测试或使用与生产环境相同的网络条件
  2. **CPU 性能** ：Redis 是单线程的，CPU 性能直接影响 QPS
  3. **内存速度** ：Redis 是内存数据库，内存带宽影响性能
  4. **持久化配置** ：启用 AOF 或 RDB 持久化会降低写入性能
  5. **客户端数量** ：增加并发连接数通常会提高吞吐量，直到达到 CPU 或网络瓶颈
  6. **键值大小** ：更大的值会降低 QPS
  7. **命令复杂度** ：O(N) 命令（如 HGETALL、LRANGE）比 O(1) 命令慢得多

## 基准测试注意事项

  * 不要在生产服务器上运行基准测试，除非你知道自己在做什么
  * 基准测试应运行足够长的时间以稳定结果
  * 多次运行并取平均值
  * 确保测试数据量不会导致内存交换（swap）
  * 考虑使用 `redis-benchmark` 的 `-r` 选项生成随机键，避免测试缓存效应

## 解读结果
    
    
    ====== SET ======
      100000 requests completed in 1.23 seconds
      50 parallel clients
      3 bytes payload
      keep alive: 1
    
    99.99% <= 1 milliseconds
    99.99% <= 2 milliseconds
    100.00% <= 2 milliseconds
    81300.81 requests per second
    

关键指标：

  * **requests per second (RPS/QPS)** ：每秒请求数，最重要的吞吐量指标
  * **延迟百分位数** ：99.99% <= 2 milliseconds 表示 99.99% 的请求在 2ms 内完成
  * **总耗时** ：完成所有请求的总时间