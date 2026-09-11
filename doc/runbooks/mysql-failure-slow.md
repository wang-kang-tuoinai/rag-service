---
id: runbook-mysql-failure-slow
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: mysql
deployment: docker-compose
---

# MySQL 调用失败或耗时升高

## 适用范围与症状
列表/详情/写入失败，或 Trace 显示 MySQL 路径较慢。

## 项目行为与证据线索
仓储异常包装 ErrMySQL 并可能记录 `internal server error in mysql`。Span 为 mysql.Create/GetById/List/Update/Delete，status_desc 分别可为 create/query/list/update/delete failed。Create/Delete 1s、GetById 1500ms、List/Update 2s context；不是固定接口耗时。

## Agent 可执行的只读验证
1. query_trace_stats 找到相关入口，search_traces 按 min_duration_ms 查慢请求，另查 failed。
2. get_trace_detail 查看 MySQL 仓储和 SQL 子 Span 的耗时、status_desc、error，保留正常慢请求。
3. search_logs(trace_id=实际ID) 核对业务库错误，避免把 obs-mysql 日志写入问题混为业务查询失败。
4. GET 若此前 Redis 失败，区分 Redis 等待和后续数据库时间；Update 包含更新后回读，不等于单条 SQL。

## 需要人工补充的检查
需要人工检查数据库连接、连接池等待、慢查询、执行计划及锁等待。当前工具不能直接查询 SQL 或数据库指标，Trace 本身未必足以区分这些原因。

## 处理建议、影响与恢复验证
依据人工验证修复连接配置或慢查询原因，不仅通过提高超时掩盖问题。改索引、终止会话等有数据库影响，应单独评估。恢复后同条件查询并比较耗时与失败数量。

## 不能据此得出的结论
较长 mysql Span 不能直接证明缺索引或锁等待。达到 context deadline 不证明 MySQL 宕机；根 self_ms 高也不是数据库耗时证据。
