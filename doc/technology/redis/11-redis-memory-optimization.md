---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/11-redis-memory-optimization.html
---

# Redis 内存优化指南

Redis 是内存数据库，内存优化至关重要。本文介绍如何优化 Redis 的内存使用。

## 内存使用分析

### 查看内存统计
    
    
    redis-cli info memory
    

关键指标：

指标 | 说明  
---|---  
`used_memory` | Redis 分配器分配的总字节数  
`used_memory_human` | 人类可读的 used_memory  
`used_memory_rss` | 操作系统看到的 Redis 驻留集大小  
`used_memory_peak` | 峰值内存使用  
`used_memory_lua` | Lua 引擎使用的内存  
`mem_fragmentation_ratio` | 内存碎片率（used _memory_ rss / used_memory）  
`mem_allocator` | 使用的内存分配器  
  
### 内存碎片

碎片率 = `used_memory_rss` / `used_memory`

  * **1.0-1.5** ：正常
  * **> 1.5**：可能存在内存碎片
  * **< 1.0**：可能使用了交换（swap）

**减少碎片** ：

  * 重启 Redis（RDB/AOF 持久化后重启可重建内存）
  * 使用主动碎片整理（Redis 4.0+）
  * 使用 jemalloc 分配器

### 主动碎片整理（Active Defragmentation）

Redis 4.0+ 支持：
    
    
    # 启用主动碎片整理
    redis-cli config set activedefrag yes
    
    # 配置触发阈值
    redis-cli config set active-defrag-threshold-lower 10
    redis-cli config set active-defrag-threshold-upper 100
    
    # 配置 CPU 使用率
    redis-cli config set active-defrag-cycle-min 5
    redis-cli config set active-defrag-cycle-max 75
    

## 数据结构优化

### 1\. 使用合适的数据类型

场景 | 推荐类型 | 替代方案  
---|---|---  
简单键值 | String | -  
对象属性 | Hash | 多个 String  
列表/队列 | List | -  
去重集合 | Set | -  
排序集合 | Sorted Set | -  
位图操作 | Bitmap | Set  
计数器 | String (INCR) | Hash  
地理位置 | Geo | Sorted Set  
HyperLogLog | 基数统计 | Set  
  
### 2\. 使用 Hash 存储对象

将对象存储为 Hash 而非多个 String 键：
    
    
    # 不推荐（多个 String）
    SET user:1000:name "John"
    SET user:1000:age 30
    SET user:1000:city "NYC"
    
    # 推荐（单个 Hash）
    HSET user:1000 name "John" age 30 city "NYC"
    

Hash 使用 ziplist 编码时非常内存高效。

### 3\. 配置 ziplist 阈值

Redis 对小集合使用 ziplist 编码（内存高效）：
    
    
    # Hash 使用 ziplist 的最大条目数
    hash-max-ziplist-entries 512
    
    # Hash 使用 ziplist 的最大值大小（字节）
    hash-max-ziplist-value 64
    
    # List 使用 ziplist 的最大条目数
    list-max-ziplist-entries 512
    list-max-ziplist-value 64
    
    # Set 使用 intset 的最大条目数
    set-max-intset-entries 512
    
    # Sorted Set 使用 ziplist 的最大条目数
    zset-max-ziplist-entries 128
    zset-max-ziplist-value 64
    

调整这些值以平衡内存使用和 CPU 性能。

### 4\. 使用整数集合（Intset）

当 Set 只包含整数时，Redis 使用 intset 编码，非常内存高效。

### 5\. 使用 Bitmap

对于大量布尔值，Bitmap 比 Set 节省大量内存：
    
    
    # 设置用户 1000 在线
    SETBIT online 1000 1
    
    # 检查用户 1000 是否在线
    GETBIT online 1000
    
    # 统计在线用户数
    BITCOUNT online
    

### 6\. 使用 HyperLogLog

对于基数统计（唯一计数），HyperLogLog 使用固定 12KB 内存：
    
    
    PFADD visitors user1 user2 user3
    PFCOUNT visitors
    

## 键优化

### 1\. 使用短键名

键名也占用内存。使用缩写：
    
    
    # 不推荐
    user:profile:1000
    
    # 推荐
    u:p:1000
    

### 2\. 使用 Hash 分片

对于大量小键，使用 Hash 分片减少键数量：
    
    
    # 将 user:1000 到 user:9999 的数据分片到 100 个 Hash
    HSET user:10 name "John" age 30  # user:10 包含 user:1000-user:1099
    

### 3\. 设置过期时间

为临时数据设置 TTL：
    
    
    EXPIRE session:12345 3600
    

### 4\. 使用 LRU/LFU 逐出

当内存达到 `maxmemory` 时，使用逐出策略：
    
    
    # 配置 maxmemory
    maxmemory 2gb
    
    # 配置逐出策略
    maxmemory-policy allkeys-lru
    

逐出策略：

策略 | 说明  
---|---  
`noeviction` | 不逐出，写入时返回错误  
`allkeys-lru` | 逐出最近最少使用的键  
`allkeys-lfu` | 逐出最不经常使用的键  
`allkeys-random` | 随机逐出键  
`volatile-lru` | 逐出设置了 TTL 的最近最少使用键  
`volatile-lfu` | 逐出设置了 TTL 的最不经常使用键  
`volatile-random` | 随机逐出设置了 TTL 的键  
`volatile-ttl` | 逐出 TTL 最短的键  
  
## 配置优化

### 1\. 使用 jemalloc

jemalloc 通常比 glibc malloc 有更好的内存分配特性：
    
    
    # 编译时指定
    make MALLOC=jemalloc
    

### 2\. 禁用不必要的功能
    
    
    # 如果不需要，禁用 Lua 脚本
    # 如果不需要，禁用 AOF
    # 如果不需要，禁用 RDB
    

### 3\. 压缩

对于大值，在客户端压缩数据：
    
    
    import zlib
    
    # 压缩
    compressed = zlib.compress(json.dumps(data).encode())
    r.set('key', compressed)
    
    # 解压
    decompressed = zlib.decompress(r.get('key'))
    

## 监控内存使用

### 使用 MEMORY 命令
    
    
    # 查看键的内存使用
    redis-cli memory usage mykey
    
    # 查看键的内存统计
    redis-cli memory stats
    
    # 查看键的编码方式
    redis-cli debug object mykey
    

### 使用 --bigkeys
    
    
    redis-cli --bigkeys
    

这会扫描数据库并报告每种数据类型的最大键。

### 使用 --memkeys
    
    
    redis-cli --memkeys
    

报告内存使用最多的键。

## 内存优化检查清单

  * [ ] 使用 `info memory` 检查碎片率
  * [ ] 使用 `--bigkeys` 识别大键
  * [ ] 使用 Hash 替代多个 String 存储对象
  * [ ] 调整 ziplist 阈值
  * [ ] 使用 Bitmap/HyperLogLog 替代 Set 进行统计
  * [ ] 设置合理的 `maxmemory` 和逐出策略
  * [ ] 为临时数据设置 TTL
  * [ ] 使用短键名
  * [ ] 考虑启用主动碎片整理
  * [ ] 在客户端压缩大值
  * [ ] 使用 jemalloc 分配器
  * [ ] 监控 `used_memory_peak` 了解峰值使用