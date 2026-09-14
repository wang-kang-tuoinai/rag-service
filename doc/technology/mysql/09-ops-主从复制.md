---
doc_type: technology
component: mysql
source_url: https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87/MySQL%E8%BF%90%E7%BB%B4%E7%AF%87.md
---

# 主从复制

## 概述

主从复制是指将主数据库的DDL 和 DML 操作通过二进制日志传到从库服务器中，然后在从库上对这些日志重新执行（也叫重做），从而使得从库和主库的数据保持同步。

MySQL支持一台主库同时向多台从库进行复制， 从库同时也可以作为其他从服务器的主库，实现链状复制。

MySQL 复制的有点主要包含以下三个方面：

1. 主库出现问题，可以快速切换到从库提供服务。

2. 实现读写分离，降低主库的访问压力。

3. 可以在从库中执行备份，以避免备份期间影响主库服务。

## 原理

MySQL 的主从复制原理如下。

从上图来看，复制分成三步：

1. Master 主库在事务提交时，会把数据变更记录在二进制日志文件 Binlog 中。

2. 从库读取主库的二进制日志文件 Binlog ，写入到从库的中继日志 Relay Log 。

3. slave重做中继日志中的事件，将改变反映它自己的数据。

## 搭建

### 服务器准备

准备好两台服务器之后，在上述的两台服务器中分别安装好MySQL，并完成基础的初始化准备工作。

### 主库的配置

1.修改配置文件 /etc/my.cnf

```sql
#mysql服务id，保证整个集群环境中唯一，取值范围：1-2^(32-1)，默认为1
server-id=1
#是否只读，1代表只读，0代表读写
read-only=0
#忽略的数据 指不需要同步的数据库
#binlog-ignore-db=mysql
#binlog-do-db=db01
```

2.重启MySQL服务

```sql
systemctl restart mysqld
```

3.登录MySQL，创建远程连接的账号，并授予主从复制权限

```sql
#创建itcast用户，并设置密码，该用户可在任意主机连接该MySQL服务
create user 'itcast'@'%' identified with mysql_native_password by 'Root@123456';
#为itcast@%用户分配主从复制权限
grant replication slave on *.* to 'itcast'@'%';
```

4.通过指令，查看二进制日志坐标

```sql
show master status;
```

字段含义说明：

​	file : 从哪个日志文件开始推送日志文件

​	position ： 从哪个位置开始推送日志

​	binlog_ignore_db : 指定不需要同步的数据库 

### 从库的配置

1.修改配置文件/etc/my.cnf

```sql
#mysql服务id，保证整个集群环境中唯一，取值范围：1-2^(32-1)，和主库不一样即可
server-id=2
#是否只读，1代表只读，0代表读写
read-only=1
```

2.重启MySQL服务

```sql
systemctl restart mysqld
```

3.登录MySQL，设置主库配置

```sql
change replication source to source_host='192.168.10.102',source_user='itcast',source_password='Root@123456',source_log_file='binlog.000004',source_log_pos=1985;
```

上述是8.0.23中的语法，如果MySQL是8.0.23之前版本，执行如下SQL：

```sql
change master to master_host='192.168.10.102',master_user='itcast',master_password='Root@123456',master_log_file='binlog.000004',master_log_pos=743;
```

| 参数名          | 含义               | 8.0.23之前      |
| --------------- | ------------------ | --------------- |
| source_host     | 主库IP地址         | master_host     |
| source_user     | 连接主库的用户名   | master_user     |
| source_password | 连接主库的密码     | master_password |
| source_log_file | binlog日志文件名   | master_log_file |
| source_log_pos  | binlog日志文件位置 | master_log_pos  |

4.开启同步操作

```sql
start replica; #after 8.0.22
start slave; #before 8.0.22
```

5.查看主从同步状态

```sql
show replica status\G; #after 8.0.22
show slave status; #before 8.0.22
```

### 测试

1.在主库上创建数据库、表，并插入数据

```sql
create database db01;
use db01;
CREATE TABLE tb_user (
	id INT (10) PRIMARY KEY NOT NULL auto_increment,
	username VARCHAR (255),
	age INT (10)
) ENGINE = INNODB DEFAULT CHARSET = utf8mb4;
INSERT INTO tb_user(id, name, sex) VALUES(NULL, '完颜雍', 10)(NULL, '完颜宗弼', 10);
```

2.在从库中查询数据，验证主从是否同步

### 总结

1.概述

将主库的数据变更同步到从库，从而保证主库和从库数据一致。

数据备份、失败迁移，读写分离，降低单库读写压力。

2.原理

（1）主库会把数据变更记录在二进制日志文件binlog中

（2）从库连接主库，读取binlog日志，并写入自身中继日志relaylog

（3）slave重做中继日志，将改变反映它自己的数据

3.搭建

（1）准备服务器

（2）配置主库

（3）配置从库

（4）测试主从复制
