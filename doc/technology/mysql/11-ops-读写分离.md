---
id: technology-mysql-read-write-splitting
doc_type: technology
component: mysql
source_url: https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87.md
---

# 读写分离

## 介绍

读写分离,简单地说是把对数据库的读和写操作分开,以对应不同的数据库服务器。主数据库提供写操作，从数据库提供读操作，这样能有效地减轻单台数据库的压力。

通过MyCat即可轻易实现上述功能，不仅可以支持MySQL，也可以支持Oracle和SQL Server。

## 一主一从

### 原理

MySQL的主从复制，是基于二进制日志（binlog）实现的。

### 环境准备

| 主机            | 角色   | 用户名 | 密码 |
| --------------- | ------ | ------ | ---- |
| 192.168.200.211 | master | root   | 1234 |
| 192.168.200.212 | slave  | root   | 1234 |

主从复制的搭建，可以参考前面课程中讲解的步骤操作。

## 一主一从读写分离

### 配置

MyCat控制后台数据库的读写分离和负载均衡由schema.xml文件datahost标签的balance属性控制。

| 参数值 | 含义                                                         |
| ------ | ------------------------------------------------------------ |
| 0      | 不开启读写分离机制 所有读操作都发送到当前可用的writeHost上   |
| 1      | 全部的readHost与备用的writeHost都参与select语句的负载均衡（主要针对于双主双从模式） |
| 2      | 所有的读写操作都随机在writeHost，readHost上分发              |
| 3      | 所有的读请求随机分发到writeHost对应的readHost上执行，writeHost不负担读压力 |

### 测试

连接Mycat，并在Mycat中执行DML、DQL查看是否能够进行读写分离。

问题：主节点Master宕机之后，业务系统就只能够读，而不能写入数据了。

## 双主双从

### 介绍

一个主机 Master1 用于处理所有写请求，它的从机 Slave1 和另一台主机 Master2 还有它的从机 Slave2 负责所有读请求。当 Master1 主机宕机后，Master2 主机负责写请求，Master1 、Master2 互为备机。架构图如下: 

### 准备工作

我们需要准备5台服务器，具体的服务器及软件安装情况如下：

| 编号 | IP              | 预装软件     | 角色              |
| ---- | --------------- | ------------ | ----------------- |
| 1    | 192.168.200.210 | MyCat、MySQL | MyCat中间件服务器 |
| 2    | 192.168.200.211 | MySQL        | M1                |
| 3    | 192.168.200.212 | MySQL        | S1                |
| 4    | 192.168.200.213 | MySQL        | M2                |
| 5    | 192.168.200.214 | MySQL        | S2                |

关闭以上所有服务器的防火墙：

• systemctl stop firewalld

• systemctl disable firewalld

### 搭建

➢ 主库配置（ Master1-192.168.200.211 ）

1. 修改配置文件 /etc/my.cnf

```sql
#mysql服务id，保证整个集群环境中唯一，取值范围：1-2^32-1，默认为1
server-id=1
#指定同步的数据库
binlog-do-db=db01
binlog-do-db=db02
binlog-do-db=db03
#在作为从数据库的时候，有写入操作也要更新二进制日志文件
log-slave-updates
```

2. 重启MySQL服务器

```sql
systemctl restart mysqld
```

➢ 主库配置（ Master2-192.168.200.213 ）

1. 修改配置文件 /etc/my.cnf

```xml
#mysql服务id，保证整个集群环境中唯一，取值范围：1-2^32-1，默认为1
server-id=3
#指定同步的数据库
binlog-do-db=db01
binlog-do-db=db02
binlog-do-db=db03
#在作为从数据库的时候，有写入操作也要更新二进制日志文件
log-slave-updates
```

2. 重启MySQL服务器

```xml
systemctl restart mysqld
```

➢ 两台主库创建账户并授权

```sql
#创建itcast用户，并设置密码，该用户可在任意主机连接该mysql服务
create user 'itcast'@'%' identified with mysql_native_password by 'Root@123456';
#为'itcast'@'%'用户分配主从复制权限
grant replication slave on *.* to 'itcast'@'%';
```

通过指令，查看两台主库的二进制日志坐标

```sql
show master status;
```

➢ 从库配置（ Slave1-192.168.200.212 ）

1. 修改配置文件 /etc/my.cnf

   ```xml
   #mysql服务id，保证整个集群环境中唯一，取值范围：1-2^32-1，默认为1
   server-id=2
   ```

2. 重启MySQL服务器

```sql
systemctl restart mysqld
```

➢ 从库配置（ Slave2-192.168.200.214 ）

1. 修改配置文件 /etc/my.cnf

```xml
#mysql服务id，保证整个集群环境中唯一，取值范围：1-2^32-1，默认为1
server-id=2
```

2. 重启MySQL服务器

```sql
systemctl restart mysqld
```

➢ 两台从库配置关联的主库

需要注意slave1对应的是master1，slave2对应的是master2。

```sql
change master to master_host='xxx.xxx.xxx.xxx', master_user='xxx', master_password='xxx',master_log_file='xxx', master_log_pos=xxx;
```

启动两台从库主从复制，查看从库状态

```sq
start slave;
show slave status \G;
```

➢ 两台主库相互复制

Master2 复制 Master1，Master1 复制 Master2。

```sql
change master to master_host='xxx.xxx.xxx.xxx', master_user='xxx', master_password='xxx',master_log_file='xxx', master_log_pos=xxx;
```

启动两台从库主从复制，查看从库状态

```sql
start slave;
show slave status \G;
```

### 测试

分别在两台主库Master1、Master2上执行DDL、DML语句，查看涉及到的数据库服务器的数据同步情况。

```sql
create database db01;
use db01;
create table tb_user(
    id int(11) not null primary key,
    name varchar(50) not null,
    sex varchar(1)
)engine=innodb default charset=utf8mb4;

insert into tb_user(id, name, sex) values(1,'完颜亮', '1');
insert into tb_user(id, name, sex) values(2,'完颜宗弼', '1');
insert into tb_user(id, name, sex) values(3,'完颜雍', '0');
insert into tb_user(id, name, sex) values(4,'朱五四', '1');
insert into tb_user(id, name, sex) values(5,'朱四九', '0');
```

## 双主双从读写分离

### 配置

MyCat控制后台数据库的读写分离和负载均衡由schema.xml文件datahost标签的balance属性控制，通过writeType及switchType来完成失败自动切换的。

### 测试

登录MyCat，测试查询及更新操作，判定是否能够进行读写分离，以及读写分离的策略是否正确。

当主库挂掉一个之后，是否能够自动切换。
