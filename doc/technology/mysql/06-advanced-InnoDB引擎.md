---
doc_type: technology
component: mysql
source_url: https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87.md
---

# InnoDB引擎

## 逻辑存储结构

## 架构
MySQL5.5 版本开始，默认使用InnoDB存储引擎，它擅长事务处理，具有崩溃恢复特性，在日常开发中使用非常广泛。下面是InnoDB架构图，左侧为内存结构，右
侧为磁盘结构。

**架构-内存架构**

**架构-磁盘结构**

**架构-后台线程**

1. Master Thread
    核心后台线程，负责调度其他线程，还负责将缓冲池中的数据异步刷新到磁盘中, 保持数据的一致性，
    还包括脏页的刷新、合并插入缓存、undo页的回收 。

2. IO Thread
    在InnoDB存储引擎中大量使用了AIO来处理IO请求, 这样可以极大地提高数据库的性能，而IO 
    Thread主要负责这些IO请求的回调。

  | 线程类型             | 默认个数 | 职责                         |
  | -------------------- | -------- | ---------------------------- |
  | Read thread          | 4        | 负责读操作                   |
  | Write thread         | 4        | 负责写操作                   |
  | Log thread           | 1        | 负责将日志缓冲区刷新到磁盘   |
  | Insert buffer thread | 1        | 负责将写缓冲区内容刷新到磁盘 |

3. Purge Thread
    主要用于回收事务已经提交了的undo log，在事务提交之后，undo log可能不用了，就用它来回收。

4. Page Cleaner Thread
协助 Master Thread 刷新脏页到磁盘的线程，它可以减轻 Master Thread 的工作压力，减少阻塞。

## 事务原理
⚫ 事务
事务 是一组操作的集合，它是一个不可分割的工作单位，事务会把所有的操作作为一个整体一起向系统提交或撤销操作请求，即这些操作
要么同时成功，要么同时失败。

⚫ 特性
• 原子性（Atomicity）：事务是不可分割的最小操作单元，要么全部成功，要么全部失败。
• 一致性（Consistency）：事务完成时，必须使所有的数据都保持一致状态。
• 隔离性（Isolation）：数据库系统提供的隔离机制，保证事务在不受外部并发操作影响的独立环境下运行。
• 持久性（Durability）：事务一旦提交或回滚，它对数据库中的数据的改变就是永久的。

⚫ redo log

重做日志，记录的是事务提交时数据页的物理修改，是用来实现事务的持久性。
该日志文件由两部分组成：重做日志缓冲（redo log buffer）以及重做日志文件（redo log file）,前者是在内存中，后者在磁盘中。当事务
提交之后会把所有修改信息都存到该日志文件中, 用于在刷新脏页到磁盘,发生错误时, 进行数据恢复使用。

⚫ undo log

回滚日志，用于记录数据被修改前的信息 , 作用包含两个 : 提供回滚 和 MVCC(多版本并发控制) 。
undo log和redo log记录物理日志不一样，它是逻辑日志。可以认为当delete一条记录时，undo log中会记录一条对应的insert记录，反之亦然，当update一条记录时，它记录一条对应相反的update记录。当执行rollback时，就可以从undo log中的逻辑记录读取到相应的内容并进行回滚。
Undo log销毁：undo log在事务执行时产生，事务提交时，并不会立即删除undo log，因为这些日志可能还用于MVCC。
Undo log存储：undo log采用段的方式进行管理和记录，存放在前面介绍的 rollback segment 回滚段中，内部包含1024个undo log segment。

## MVCC
### MVCC-基本概念
⚫ 当前读
读取的是记录的最新版本，读取时还要保证其他并发事务不能修改当前记录，会对读取的记录进行加锁。对于我们日常的操作，如：
select ... lock in share mode(共享锁)，select ... for update、update、insert、delete(排他锁)都是一种当前读。
⚫ 快照读
简单的select（不加锁）就是快照读，快照读，读取的是记录数据的可见版本，有可能是历史数据，不加锁，是非阻塞读。
• Read Committed：每次select，都生成一个快照读。
• Repeatable Read：开启事务后第一个select语句才是快照读的地方。
• Serializable：快照读会退化为当前读。
⚫ MVCC
全称 Multi-Version Concurrency Control，多版本并发控制。指维护一个数据的多个版本，使得读写操作没有冲突，快照读为MySQL实现
MVCC提供了一个非阻塞读功能。MVCC的具体实现，还需要依赖于数据库记录中的三个隐式字段、undo log日志、readView。
### MVCC-实现原理
⚫ 记录中的隐藏字段

⚫ undo log
回滚日志，在insert、update、delete的时候产生的便于数据回滚的日志。
当insert的时候，产生的undo log日志只在回滚时需要，在事务提交后，可被立即删除。
而update、delete的时候，产生的undo log日志不仅在回滚时需要，在快照读时也需要，不会立即被删除。
⚫ undo log版本链

不同事务或相同事务对同一条记录进行修改，会导致该记录的undolog生成一条记录版本链表，链表的头部是最新的旧记录，链表尾部是最早的旧记录。
⚫ readview
ReadView（读视图）是 快照读 SQL执行时MVCC提取数据的依据，记录并维护系统当前活跃的事务（未提交的)id。
ReadView中包含了四个核心字段：

| 字段           | 含义                                                 |
| -------------- | ---------------------------------------------------- |
| m_ids          | 当前活跃的事务ID集合                                 |
| min_trx_id     | 最小活跃事务ID                                       |
| max_trx_id     | 预分配事务ID，当前最大事务ID+1（因为事务ID是自增的） |
| creator_trx_id | ReadView创建者的事务ID                               |

不同的隔离级别，生成ReadView的时机不同：
➢ READ COMMITTED ：在事务中每一次执行快照读时生成ReadView。 
➢ REPEATABLE READ：仅在事务中第一次执行快照读时生成ReadView，后续复用该ReadView。
RC隔离级别下，在事务中每一次执行快照读时生成ReadView。

RR隔离级别下，仅在事务中第一次执行快照读时生成ReadView，后续复用该ReadView。
