---
id: technology-redis-large-keys
doc_type: technology
project: ops-agent
service: common
component: redis
deployment: standalone
version: "7.x"
source_url: "https://redis.io/docs/latest/commands/memory-usage/"
---

# Redis 大键识别、扫描与删除

## 适用范围与症状
单键读写或删除较慢，响应体较大，怀疑数据集中在少数键中。

## 识别依据
大键需要结合字节数、元素数、访问方式和业务预算判断，不能仅使用固定元素数量。
MEMORY USAGE 返回键及值的内存估计；嵌套类型可能采样。元素数量不等于占用字节数。

## 验证方法
先定位可疑键，再人工查看类型、大小及相关慢命令。全库排查可采用渐进式 SCAN，但完整遍历仍有开销；COUNT 是提示而非严格返回上限，扫描也不是一致性快照，可能重复返回键。
不为排查而直接执行 KEYS * 或读取整个大集合。

## 处理与边界
确认大键后评估拆分数据、限制单次返回量。UNLINK 将键从键空间移除，内存释放交给后台处理；它仍是删除操作，不会保留业务数据。
调整淘汰策略不是修复大键的直接方案，不能在未确认数据用途时批量删除。
