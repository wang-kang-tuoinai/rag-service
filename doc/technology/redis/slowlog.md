---
id: technology-redis-slowlog
doc_type: technology
project: ops-agent
service: common
component: redis
deployment: standalone
version: "7.x"
source_url: "https://redis.io/docs/latest/commands/slowlog-get/"
---

# Redis 慢日志的含义与排查边界

## 适用范围与症状
怀疑高耗时 Redis 命令，或客户端超时但慢日志为空。

## 机制与指标
SLOWLOG 记录超过配置阈值的命令执行时间，不包含与客户端通信的 I/O 时间，不能代表端到端延迟。
slowlog-log-slower-than 的单位为微秒；slowlog-max-len 控制保留条数。阈值、有限长度和重启都会影响能否找到历史记录。

## 验证方法
人工使用 SLOWLOG GET 10 读取有限条记录，核对时间、命令、参数规模和耗时，再与应用 Trace 对齐。
同时核对慢日志配置。日志为空可能是未超过阈值、记录被覆盖或延迟发生在其他环节，不能排除调用路径异常。

## 处理边界
有慢命令证据时再评估缩小操作范围或调整数据组织。调低记录阈值只是提高可见性，不会让命令变快。
不要在取证前 SLOWLOG RESET；参数可能包含业务数据，输出需适当处理。
