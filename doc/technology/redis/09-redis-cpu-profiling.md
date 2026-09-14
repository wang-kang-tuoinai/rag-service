---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/09-redis-cpu-profiling.html
---

# Redis CPU 分析指南

Redis 是单线程的，因此 CPU 分析相对简单。了解 Redis 如何使用 CPU 有助于识别性能瓶颈。

## 使用 perf 进行 CPU 分析

`perf` 是 Linux 上的性能分析工具，可用于分析 Redis 的 CPU 使用情况。

### 安装 perf
    
    
    # Ubuntu/Debian
    sudo apt-get install linux-tools-common linux-tools-generic
    
    # CentOS/RHEL
    sudo yum install perf
    

### 分析 Redis 进程
    
    
    # 找到 Redis 进程 ID
    pgrep redis-server
    
    # 记录 30 秒的 CPU 性能数据
    sudo perf record -g -p <redis-pid> -- sleep 30
    
    # 生成报告
    sudo perf report
    

### 常用 perf 命令
    
    
    # 实时查看热点函数
    sudo perf top -p <redis-pid>
    
    # 记录并生成火焰图
    sudo perf record -F 99 -a -g -- sleep 60
    sudo perf script | ./stackcollapse-perf.pl | ./flamegraph.pl > redis.svg
    

## 使用 gprof 分析

Redis 支持使用 gprof 进行编译时分析：
    
    
    # 编译时启用 gprof
    make CFLAGS="-pg" LDFLAGS="-pg"
    
    # 运行 Redis 一段时间后停止
    # 生成 gmon.out 文件
    
    # 分析结果
    gprof redis-server gmon.out > analysis.txt
    

## 火焰图（Flame Graphs）

火焰图是可视化 CPU 分析结果的最佳方式。

### 生成火焰图步骤
    
    
    # 1. 克隆火焰图工具
    git clone https://github.com/brendangregg/FlameGraph.git
    cd FlameGraph
    
    # 2. 记录 perf 数据
    sudo perf record -F 99 -p <redis-pid> -g -- sleep 60
    
    # 3. 生成火焰图
    sudo perf script | ./stackcollapse-perf.pl | ./flamegraph.pl > redis-flamegraph.svg
    

### 解读火焰图

  * **宽度** ：表示该函数在采样中出现的频率（CPU 时间占比）
  * **高度** ：表示调用栈深度
  * **颜色** ：仅用于区分不同函数，无特殊含义
  * **底部** ：是主线程的入口
  * **顶部** ：是实际执行 CPU 工作的函数

## 常见 CPU 瓶颈

### 1\. 命令处理

如果 `call()` 或 `processCommand()` 占用大量 CPU，说明 Redis 正在处理大量命令。考虑：

  * 使用管道（pipeline）减少网络往返
  * 优化命令使用，避免 O(N) 命令
  * 考虑使用 Redis Cluster 分片

### 2\. 序列化/反序列化

`addReply()` 相关函数占用高说明网络 I/O 或协议序列化是瓶颈。考虑：

  * 减少键值大小
  * 使用二进制协议客户端
  * 启用压缩

### 3\. 持久化

`rdbSave()` 或 `aofRewrite()` 占用高说明持久化是瓶颈。考虑：

  * 使用无盘复制
  * 调整持久化策略
  * 使用更快的磁盘

### 4\. 内存管理

`zmalloc()` 或 `free()` 占用高说明内存分配是瓶颈。考虑：

  * 使用 jemalloc 或 tcmalloc
  * 减少内存碎片
  * 优化数据结构使用

## 使用 MONITOR 命令

虽然 MONITOR 命令会显著降低性能，但可用于了解 Redis 正在执行哪些命令：
    
    
    redis-cli monitor
    

**警告** ：不要在生产环境的高负载实例上使用 MONITOR，它会使性能降低 50% 以上。

## 使用 SLOWLOG

SLOWLOG 是更安全的性能分析工具：
    
    
    # 查看慢查询日志
    redis-cli slowlog get 10
    
    # 配置慢查询阈值（微秒）
    redis-cli config set slowlog-log-slower-than 10000
    
    # 配置慢查询日志长度
    redis-cli config set slowlog-max-len 128
    

## 分析结果示例

典型的 Redis CPU 使用分布：

组件 | 正常占比 | 异常占比  
---|---|---  
命令处理 | 40-60% | > 80%  
网络 I/O | 10-20% | > 30%  
持久化 | 5-15% | > 30%  
内存管理 | 5-10% | > 20%  
空闲 | 10-20% | < 5%  
  
如果命令处理占比过高，说明 Redis 正在满负荷运行，需要考虑扩展。