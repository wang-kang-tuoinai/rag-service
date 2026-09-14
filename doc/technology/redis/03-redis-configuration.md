---
doc_type: technology
component: redis
source_url: https://redis.com.cn/management/03-redis-configuration.html
---

# Redis 配置指南

Redis 可以在没有配置文件的情况下使用内置默认配置启动，但这仅推荐用于测试和开发目的。

配置 Redis 的正确方式是提供 Redis 配置文件，通常称为 `redis.conf`。从 Redis 8 开始，有两个配置文件：

  * `redis.conf` — 仅包含 Redis 服务器的配置设置
  * `redis-full.conf` — 包含 Redis 服务器和所有可用组件的配置设置：Redis Search、Redis Time Series 和 Redis 概率数据结构。此文件第一行为 `include redis.conf`，在启动时引入 Redis 服务器配置。

如果从源码构建 Redis 且选择不构建可用组件，可以使用 `redis.conf` 作为配置文件。

## 配置指令格式

每个配置指令格式非常简单：
    
    
    keyword argument1 argument2 ... argumentN
    

示例：
    
    
    replicaof 127.0.0.1 6380
    

可以使用（双引号或单引号）提供包含空格的字符串参数：
    
    
    requirepass "hello world"
    

单引号字符串可包含反斜杠转义的字符，双引号字符串还可包含使用反斜杠十六进制表示法编码的任何 ASCII 符号，如 `\xff`。

配置指令列表及其注释说明的含义和预期用途，可在 Redis 发行版附带的自文档化示例文件 `redis.conf` 和 `redis-full.conf` 中找到。

## 通过命令行传递参数

也可以直接通过命令行传递 Redis 配置参数，这对测试非常有用：
    
    
    ./redis-server --port 6380 --replicaof 127.0.0.1 6379
    

命令行参数的格式与 redis.conf 中的格式完全相同，只是关键字前缀为 `--`。

## 运行时更改配置

可以在服务器运行时重新配置 Redis，无需停止和重启服务，使用特殊命令 CONFIG SET 和 CONFIG GET。

并非所有配置指令都支持这种方式，但大多数都支持。运行时修改配置不会影响 `redis.conf` 和 `redis-full.conf` 文件，因此下次重启 Redis 时将使用旧配置。

确保也相应修改配置文件，可以使用 CONFIG REWRITE 自动扫描配置文件并更新与当前配置值不匹配的字段。

## 将 Redis 配置为缓存

如果计划将 Redis 用作缓存，其中每个键都有过期时间，可以考虑以下配置（以 2MB 内存限制为例）：
    
    
    maxmemory 2mb
    maxmemory-policy allkeys-lru
    

在此配置中，应用程序无需使用 EXPIRE 命令为键设置生存时间，因为所有键都会在达到 2MB 内存限制时使用近似 LRU 算法被逐出。

在此配置中，Redis 的行为类似于 memcached。