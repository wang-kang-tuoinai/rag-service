---
id: technology-redis-expiration-eviction
doc_type: technology
project: ops-agent
service: common
component: redis
deployment: standalone
version: "7.x"
source_url: "https://redis.io/docs/latest/develop/reference/eviction/"
---

# Redis 过期、内存淘汰与缓存未命中

## 适用范围与症状
缓存未命中增加、TTL 行为异常，或达到内存限制后部分写入报错。

## 过期与淘汰
过期由键的到期时间决定，Redis 通过访问时检查和主动清理处理过期键。物理内存尚未释放不意味着普通 GET 会返回已过期值。
淘汰由内存压力及 maxmemory-policy 决定，键可能在 TTL 到期前被淘汰。maxmemory-samples 与近似淘汰采样有关，不是主动过期扫描数量开关。

## 策略区别
allkeys-* 从所有键中选择；volatile-* 仅从设置过期时间的键中选择。LRU 侧重最近访问，LFU 侧重访问频度；volatile-ttl 倾向剩余寿命短的键。
noeviction 不靠淘汰腾空间，超限时需要分配内存的写入可能报错；不是所有命令均被拒绝。候选不足时 volatile 策略也可能无法满足写入。

## 验证方法
人工检查 maxmemory、maxmemory-policy，以及相邻时刻 expired_keys、evicted_keys 的增量。
TTL 返回秒，-1 表示存在但未设置过期，-2 表示不存在；单次 -2 无法区分过期、淘汰、显式删除或从未写入。

## 处理边界
缓存、分布式锁和不可丢失的数据不应被等同看待。改变淘汰策略可能影响锁和一致性；先确认实例中数据用途。相同 TTL 不必然同时过期，还需结合写入时间。
