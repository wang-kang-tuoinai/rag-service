---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/13-redis-debugging.html
---

# Redis 调试指南

Redis 提供多种调试工具和方法，帮助开发者和运维人员诊断问题。

## DEBUG 命令

Redis 提供 DEBUG 命令用于各种调试操作。

### DEBUG SEGFAULT

使 Redis 服务器崩溃，模拟段错误。用于测试崩溃恢复机制：
    
    
    redis-cli debug segfault
    

**警告** ：仅用于测试环境！

### DEBUG OOM

使 Redis 耗尽内存：
    
    
    redis-cli debug oom
    

### DEBUG LOADAOF

重新加载 AOF 文件：
    
    
    redis-cli debug loadaof
    

### DEBUG RELOAD

保存 RDB 文件并重新加载：
    
    
    redis-cli debug reload
    

可选参数：

  * `NOSAVE`：不保存当前数据集
  * `MERGE`：将当前数据集与磁盘上的数据集合并

### DEBUG OBJECT

获取键的内部信息：
    
    
    redis-cli debug object mykey
    

输出示例：
    
    
    Value at:0x7f8b4c0b4030 refcount:1 encoding:raw serializedlength:5 lru:16486158 lru_seconds_idle:0
    

字段说明：

  * `Value at`：值的内存地址
  * `refcount`：引用计数
  * `encoding`：内部编码（raw、int、embstr、ziplist 等）
  * `serializedlength`：序列化后的长度
  * `lru`：LRU 时钟值
  * `lru_seconds_idle`：空闲秒数

### DEBUG SDSLEN

获取 SDS（Simple Dynamic String）长度信息：
    
    
    redis-cli debug sdslen mykey
    

### DEBUG POPULATE

用随机键填充数据库（用于测试）：
    
    
    # 创建 100000 个随机键
    redis-cli debug populate 100000
    
    # 创建指定前缀的键
    redis-cli debug populate 100000 myprefix 10
    

### DEBUG SLEEP

让 Redis 睡眠指定秒数（用于测试）：
    
    
    redis-cli debug sleep 10
    

### DEBUG SET-ACTIVE-EXPIRE

启用或禁用主动过期：
    
    
    redis-cli debug set-active-expire 0  # 禁用
    redis-cli debug set-active-expire 1  # 启用
    

### DEBUG QUICKLIST-PACKED-THRESHOLD

设置 quicklist 压缩阈值：
    
    
    redis-cli debug quicklist-packed-threshold 2kb
    

## 日志调试

### 日志级别

Redis 支持以下日志级别：

  * `debug`：大量信息，用于开发/调试
  * `verbose`：许多信息，但不如 debug 多
  * `notice`：适度详细，生产环境推荐
  * `warning`：仅记录非常重要/关键的消息

配置：
    
    
    redis-cli config set loglevel debug
    

### 慢查询日志

记录执行时间超过指定阈值的命令：
    
    
    # 设置阈值（微秒）
    redis-cli config set slowlog-log-slower-than 10000
    
    # 设置日志长度
    redis-cli config set slowlog-max-len 128
    
    # 查看慢查询日志
    redis-cli slowlog get 10
    
    # 查看慢查询日志长度
    redis-cli slowlog len
    
    # 清空慢查询日志
    redis-cli slowlog reset
    

慢查询日志条目格式：
    
    
    1) 1) (integer) 1          # 唯一 ID
       2) (integer) 1648615800  # 时间戳
       3) (integer) 12345       # 执行时间（微秒）
       4) 1) "GET"              # 命令
          2) "mykey"            # 参数
    

## 使用 GDB 调试

### 附加到运行中的 Redis
    
    
    # 找到 Redis PID
    pgrep redis-server
    
    # 使用 GDB 附加
    sudo gdb -p <redis-pid>
    

### 常用 GDB 命令
    
    
    # 查看调用栈
    bt
    
    # 查看所有线程
    info threads
    
    # 切换到特定线程
    thread 1
    
    # 查看变量
    p server
    
    # 设置断点
    b processCommand
    
    # 继续执行
    c
    
    # 单步执行
    n
    
    # 打印当前命令
    p (struct redisCommand *)c->cmd
    

### 生成核心转储
    
    
    # 启用核心转储
    ulimit -c unlimited
    
    # 配置核心转储路径
    echo '/var/crash/core.%e.%p' | sudo tee /proc/sys/kernel/core_pattern
    
    # 触发段错误（测试）
    redis-cli debug segfault
    

### 分析核心转储
    
    
    gdb /usr/local/bin/redis-server /var/crash/core.redis-server.1234
    
    (gdb) bt full        # 完整调用栈
    (gdb) info registers # 寄存器信息
    (gdb) x/20i $pc      # 反汇编当前位置
    

## 使用 Valgrind

Valgrind 是内存错误检测工具，可用于检测 Redis 的内存问题。

### 安装
    
    
    sudo apt-get install valgrind
    

### 使用
    
    
    # 基本使用
    valgrind --leak-check=full redis-server /etc/redis/redis.conf
    
    # 详细输出
    valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes   --log-file=valgrind.log redis-server /etc/redis/redis.conf
    
    # 仅检测内存错误（更快）
    valgrind --tool=memcheck redis-server /etc/redis/redis.conf
    

**注意** ：Valgrind 会显著降低 Redis 性能，仅用于测试环境。

## 使用 strace

strace 跟踪系统调用，可用于诊断 I/O 问题。
    
    
    # 跟踪 Redis 系统调用
    sudo strace -p $(pgrep redis-server)
    
    # 跟踪文件操作
    sudo strace -e trace=file -p $(pgrep redis-server)
    
    # 跟踪网络操作
    sudo strace -e trace=network -p $(pgrep redis-server)
    
    # 跟踪内存操作
    sudo strace -e trace=memory -p $(pgrep redis-server)
    
    # 记录到文件
    sudo strace -o redis.strace -p $(pgrep redis-server)
    

## 使用 ltrace

ltrace 跟踪库函数调用：
    
    
    sudo ltrace -p $(pgrep redis-server)
    

## 网络调试

### 使用 tcpdump
    
    
    # 捕获 Redis 流量
    sudo tcpdump -i any port 6379 -w redis.pcap
    
    # 分析
    sudo tcpdump -r redis.pcap -A | head -20
    

### 使用 Wireshark

  1. 使用 tcpdump 捕获流量
  2. 在 Wireshark 中打开
  3. 使用 Redis 协议解析器（如果可用）

### 使用 redis-cli 的 raw 模式
    
    
    # 查看原始协议数据
    redis-cli --raw monitor
    
    # 使用管道测试
    redis-cli --pipe < commands.txt
    

## 内存调试

### 使用 jemalloc 的 prof 功能
    
    
    # 编译时启用
    make MALLOC=jemalloc CFLAGS="-DJE_MALLOC_PROF" 
    
    # 生成堆转储
    redis-cli debug mallctl prof.dump
    

### 使用 massif（Valgrind 工具）
    
    
    valgrind --tool=massif redis-server /etc/redis/redis.conf
    ms_print massif.out.* > massif.txt
    

## 性能调试

### 使用 perf
    
    
    # 记录性能数据
    sudo perf record -g -p $(pgrep redis-server) -- sleep 60
    
    # 生成报告
    sudo perf report
    
    # 生成火焰图
    sudo perf script | ./stackcollapse-perf.pl | ./flamegraph.pl > redis.svg
    

### 使用 eBPF/bcc
    
    
    # 安装 bcc
    cd /usr/share/bcc/tools
    
    # 跟踪 Redis 的 off-CPU 时间
    ./offcputime -p $(pgrep redis-server) 30
    
    # 跟踪 Redis 的文件系统操作
    ./biosnoop -p $(pgrep redis-server)
    
    # 跟踪 Redis 的内存分配
    ./memleak -p $(pgrep redis-server)
    

## Lua 脚本调试

### 使用 EVAL 调试
    
    
    # 测试脚本
    redis-cli eval "return redis.call('ping')" 0
    
    # 打印调试信息
    redis-cli eval "redis.log(redis.LOG_DEBUG, 'debug message') return 1" 0
    

### Lua 日志级别
    
    
    redis.log(redis.LOG_DEBUG, "debug message")
    redis.log(redis.LOG_VERBOSE, "verbose message")
    redis.log(redis.LOG_NOTICE, "notice message")
    redis.log(redis.LOG_WARNING, "warning message")
    

日志输出到 Redis 日志文件。

## 模块调试

### 加载模块
    
    
    redis-cli module load /path/to/module.so
    

### 查看已加载模块
    
    
    redis-cli module list
    

### 卸载模块
    
    
    redis-cli module unload <module-name>
    

## 测试工具

### redis-cli 测试模式
    
    
    # 扫描数据库
    redis-cli --scan --pattern 'user:*'
    
    # 大键扫描
    redis-cli --bigkeys
    
    # 内存键扫描
    redis-cli --memkeys
    
    # 统计模式
    redis-cli --stat
    

### 使用 Redis 测试套件
    
    
    # 运行测试
    cd redis-src
    cd tests
    ./run-tests
    
    # 运行特定测试
    ./run-tests --single unit/type/string
    

## 调试最佳实践

  1. **始终在非生产环境测试调试命令**

     * DEBUG SEGFAULT、`DEBUG OOM` 等命令会导致服务器崩溃
  2. **使用日志级别递增**

     * 从 `notice` 开始，必要时提高到 `verbose` 或 `debug`
  3. **收集完整信息**

     * Redis 版本、操作系统、配置文件、日志、崩溃转储
  4. **使用版本控制**

     * 在修改配置前备份
     * 记录所有更改
  5. **监控关键指标**

     * 内存使用、CPU 使用、延迟、连接数
  6. **使用适当的工具**

     * 内存问题：Valgrind、jemalloc prof
     * 性能问题：perf、flamegraph
     * 网络问题：tcpdump、Wireshark
     * 崩溃问题：GDB、核心转储