---
id: technology-redis-latency-diagnosis
doc_type: technology
project: ops-agent
service: common
component: redis
deployment: standalone
version: "7.x"
source_url: "https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/"
---

# Redis 客户端延迟与服务端延迟的区分

## 适用范围与症状
Redis 7.x 单机使用中，客户端请求变慢或超时，但尚未确定时间消耗在哪一层。

## 机制与区分
客户端观测耗时可能包含连接获取、网络往返、服务端等待及命令执行。Redis Span 变长只能定位到调用路径，不能单独证明 Redis 命令执行慢。
--latency 测量往返响应；--intrinsic-latency 测量运行主机的调度延迟，不连接 Redis，也不测量请求排队时间。

## 验证方法
先关联慢 Trace 的操作、错误和时间段，再请人工比较客户端侧与 Redis 所在主机的延迟、慢日志及宿主机负载。连接池等待需客户端侧证据。
--intrinsic-latency 会消耗 CPU，适合受控环境；不要在繁忙主机上直接当作无成本探针。

## 处理边界
按同环境基线和业务延迟目标判断异常，不使用固定“超过两倍就故障”的通用标准。现有观测工具不执行 Redis 或操作系统命令。
