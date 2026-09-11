---
id: arch-user-flows
doc_type: architecture
project: ops-agent
service: ops-agent-backend
component: application
deployment: docker-compose
---

# 用户接口调用路径与失败语义

## 路由与顺序
| 路由 | 主要路径 |
|---|---|
| POST /api/v1/users | 参数校验 → bcrypt → MySQL Create → 尝试缓存 → 布隆 Add → 尝试注册事件发布 |
| GET /api/v1/users/:id | ID 解析 → 布隆检查 → Redis GET → 按结果返回或查 MySQL |
| GET /api/v1/users | 分页参数处理 → cache.List → mysql.List；当前不缓存列表 |
| PUT /api/v1/users/:id | 参数校验 → Redis 加锁 → MySQL 更新/回读 → 删除缓存 → 尝试解锁 |
| DELETE /api/v1/users/:id | 布隆检查 → MySQL 删除 → 尝试删除缓存 |
入口 operation 应复制 traces/stats 返回值，日志 route 使用路由模板，不用具体用户 ID 替代 :id。

## 缓存的真实分支
GET 命中：反序列化缓存后返回；JSON 解析失败直接向上返回 ErrCache，不回源。
GET 未命中（redis.Nil）：记录 DEBUG cache miss，查库，成功后尝试回填。
GET 其他 Redis 错误：记录 WARN 和异常，直接查库，此分支不回填。
Create 的缓存写入失败、Update/Delete 的缓存删除失败均不回滚已成功的数据库操作。缓存 TTL 为 10 分钟。
因此 Redis 不可用不等于所有接口失败；列表绕过缓存，但更新加锁失败会阻止进入更新逻辑。

## HTTP 和错误分类
用户不存在为 404；重复用户和锁冲突为 409；非法参数为 400；未预期错误为 500。创建、更新成功使用 200。
注册消息发布失败记录 WARN 和 handler.create.user 的异常，仍返回创建成功；不能因消息失败推断数据库创建失败。
bcrypt 在 handler.create.user 内，没有独立业务 Span，因此其耗时可能落在该节点 self_ms 中；这不是已证明的 CPU 瓶颈。

## 布隆过滤器边界
进程内过滤器启动时加载数据库 ID，创建成功时加入。GET/Delete 在查询前拦截不在过滤器的字符串 ID；删除不移除位。数据库外部新增、启动加载失败等情形需核对过滤器同步。
ID 先解析为数字，但布隆查询仍使用原始字符串；例如非规范的前导零形式可能与创建时的十进制 ID 字符串不一致。被拦截不等于数据库中已证实不存在。
