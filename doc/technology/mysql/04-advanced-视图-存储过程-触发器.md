---
id: technology-mysql-views-procedures-triggers
doc_type: technology
component: mysql
source_url: https://github.com/AlibabaP8Developer/knowledge/blob/master/docs/database/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87/MySQL%E8%BF%9B%E9%98%B6%E7%AF%87.md
---

# 视图/存储过程/触发器

## 视图

⚫ 介绍

视图（View）是一种虚拟存在的表。视图中的数据并不在数据库中实际存在，行和列数据来自定义视图的查询中使用的表，并且是在使用视图时动态生成的。

通俗的讲，视图只保存了查询的SQL逻辑，不保存查询结果。所以我们在创建视图的时候，主要的工作就落在创建这条SQL查询语句上。

⚫ 创建

```sql
create [or replace] view 视图名称[(列表名称)] as select语句 [with [cascaded | local] check option] 
```

⚫ 查询

```sql
查看创建视图语句：show create view 视图名称
查看视图数据：select * from 视图名称...;
```

⚫ 修改

```sql
方式一：create [or replace] view 视图名称[(列名列表)] as select 语句 [with [cascaded | local] check option] 
方式二：alter view 视图名称[(列名列表)] as select语句 [with [cascaded | local] check option] 
```

⚫ 删除

```sql
drop view [if exists] 视图名称[,视图名称]...
```

⚫ 视图的检查选项

当使用WITH CHECK OPTION子句创建视图时，MySQL会通过视图检查正在更改的每个行，例如 插入，更新，删除，以使其符合视图的定

义。 MySQL允许基于另一个视图创建视图，它还会检查依赖视图中的规则以保持一致性。为了确定检查的范围，mysql提供了两个选项：CASCADED 和 LOCAL ，默认值为 CASCADED 。

CASCADED :

LOCAL :

⚫ 视图的更新

要使视图可更新，视图中的行与基础表中的行之间必须存在一对一的关系。如果视图包含以下任何一项，则该视图不可更新：

1. 聚合函数或窗口函数（SUM()、 MIN()、 MAX()、 COUNT()等）

2. DISTINCT

3. GROUP BY

4. HAVING

5. UNION 或者 UNION ALL

⚫ 作用

➢ 简单

​	视图不仅可以简化用户对数据的理解，也可以简化他们的操作。那些被经常使用的查询可以被定义为视图，从而使得用户不必为以后的操

作每次指定全部的条件。

➢ 安全

​	数据库可以授权，但不能授权到数据库特定行和特定的列上。通过视图用户只能查询和修改他们所能见到的数据

➢ 数据独立

​	视图可帮助用户屏蔽真实表结构变化带来的影响。

**案例**

根据如下需求，定义视图

1. 为了保证数据库表的安全性，开发人员在操作tb_user表时，只能看到的用户的基本字段，屏蔽手机号和邮箱两个

字段。

2. 查询每个学生所选修的课程（三张表联查），这个功能在很多的业务中都有使用到，为了简化操作，定义一个视

图。

## 存储过程

⚫ 介绍

存储过程是事先经过编译并存储在数据库中的一段 SQL 语句的集合，调用存储过程可以简化应用开发人员的很多工作，减少数据在数据库和应用服务器之间的传输，对于提高数据处理的效率是有好处的。

存储过程思想上很简单，就是数据库 SQL 语言层面的代码封装与重用。

⚫ 特点

​	封装，复用

​	可以接收参数，也可以返回数据

​	减少网络交互，效率提升

⚫ 创建

```sql
create procedure 存储过程名称([参数列表])
begin 
    -- sql语句
end;
```

⚫ 调用

```sql
call 名称([参数]);
```

⚫ 查看

```sql
select * from information_schema.ROUTINES where ROUTINE_SCHEMA='xxx';-- 查询指定数据库的存储过程及状态信息
show create procedure 存储过程名称; -- 查询某个存储过程的定义
```

⚫ 删除

```sql
drop procedure [if exists] 存储过程名称;
```

注意: 在命令行中，执行创建存储过程的SQL时，需要通过关键字 delimiter 指定SQL语句的结束符。

⚫ 变量

系统变量 是MySQL服务器提供，不是用户定义的，属于服务器层面。分为全局变量（GLOBAL）、会话变量（SESSION）。

➢ 查看系统变量

```sql
show [session | global] variables;-- 查看所有系统变量
show [session | global] variables like '...';-- 可以通过like模糊匹配方式查找变量
select @@[session | global] 系统变量名;-- 查看指定变量的值
```

➢ 设置系统变量

```sql
set [session | global] 系统变量名=值;
set @@[session | global] 系统变量名=值;
```

注意: 

​	如果没有指定SESSION/GLOBAL，默认是SESSION，会话变量。

​	mysql服务重新启动之后，所设置的全局参数会失效，要想不失效，可以在 /etc/my.cnf 中配置。

⚫ 变量

用户定义变量 是用户根据需要自己定义的变量，用户变量不用提前声明，在用的时候直接用“@变量名”使用就可以。其作用域为当前连接。

➢ 赋值

```sql
set @var_name=expr[,@var_name=expr]...;
set @var_name:=expr[,@var_name:=expr]...;

select @var_name:=expr[,@var_name:=expr]...
select 字段名 into @var_name from 表名;
```

➢ 使用

```sql
select @var_name;
```

注意: 

用户定义的变量无需对其进行声明或初始化，只不过获取到的值为NULL。

⚫ 变量

局部变量 是根据需要定义的在局部生效的变量，访问之前，需要DECLARE声明。可用作存储过程内的局部变量和输入参数，局部变量的范围是在其内声明的BEGIN ... END块。

➢ 声明

```sql
declare 变量名 变量类型 [default ...];
```

变量类型就是数据库字段类型：INT、BIGINT、CHAR、VARCHAR、DATE、TIME等。

➢ 赋值

```sql
set 变量名=值;
set 变量名:=值;
select 字段名 into 变量名 from 表名 ...;
```

⚫ if

语法：

```sql
if 条件1 then
	...
elseif 条件2 then  -- 可选
    ...
else  -- 可选
	...
end if;
```

**练习**

定义存储过程，完成如下需求

根据定义的分数score变量，判定当前分数对应的分数等级。

1. score >= 85分，等级为优秀。

2. score >= 60分 且 score < 85分，等级为及格。

3. score < 60分，等级为不及格。

⚫ 参数

| 类型  | 含义                                         | 备注 |
| ----- | -------------------------------------------- | ---- |
| in    | 该类参数作为输入，也就是需要调用时传入值     | 默认 |
| out   | 该类参数作为输出，也就是该参数可以作为返回值 |      |
| inout | 既可以作为输入参数，也可以作为输出参数       |      |

用法：
```sql
create procedure 存储过程名称([in/out/inout 参数名 参数类型])
begin
    -- sql语句
end;
```
**练习**：
定义存储过程，完成如下需求
    1. 根据传入参数score，判定当前分数对应的分数等级，并返回。 
    ① score >= 85分，等级为优秀。
    ② score >= 60分 且 score < 85分，等级为及格。
    ③ score < 60分，等级为不及格。

2. 将传入的 200分制的分数,进行换算,换算成百分制 , 然后返回。

⚫ case
➢ 语法一
```sql
case case_value
    when when_value1 then statement_list1
    [when when_value2 then statement_list2]...
    [else statement_list]
end case;
```
➢ 语法二
```sql
case
    when search_condition1 then statement_list1
    [when search_condition2 then statement_list2]...
    [else statement_list]
end case;
```
**练习**
定义存储过程，完成如下需求
根据传入的月份，判定月份所属的季节（要求采用case结构）。
    1. 1-3月份，为第一季度
    2. 4-6月份，为第二季度
    3. 7-9月份，为第三季度
    4. 10-12月份，为第四季度

⚫ while
while 循环是有条件的循环控制语句。满足条件后，再执行循环体中的SQL语句。具体语法为：
```sql
#先判定条件，如果条件为true ，则执行逻辑，否则，不执行逻辑
when 条件 do
    -- SQL逻辑
end while;
```
**练习**
定义存储过程，完成如下需求
计算从1累加到n的值，n为传入的参数值。

⚫ repeat
repeat是有条件的循环控制语句, 当满足条件的时候退出循环 。具体语法为：
```sql
#先执行一次逻辑，然后判定逻辑是否满足，如果满足，则退出。如果不满足，则继续下一次循环
repeat
    -- sql逻辑
    -- until条件
end repeat;
```
**练习**
定义存储过程，完成如下需求
计算从1累加到n的值，n为传入的参数值。

⚫ loop
LOOP 实现简单的循环，如果不在SQL逻辑中增加退出循环的条件，可以用其来实现简单的死循环。LOOP可以配合一下两个语句使用：
• LEAVE ：配合循环使用，退出循环。
• ITERATE：必须用在循环中，作用是跳过当前循环剩下的语句，直接进入下一次循环。
```sql
[begin_label:] loop
    -- sql逻辑
end loop [end_label];

leave label;-- 退出指定标记的循环体
iterate label;-- 直接进入下一次循环
```
**练习**
定义存储过程，完成如下需求
1. 计算从1累加到n的值，n为传入的参数值。
2. 计算从1到n之间的偶数累加的值，n为传入的参数值。

⚫ 游标
游标（CURSOR）是用来存储查询结果集的数据类型 , 在存储过程和函数中可以使用游标对结果集进行循环的处理。游标的使用包括游标
的声明、OPEN、FETCH 和 CLOSE，其语法分别如下。
➢ 声明游标
```sql
declare 游标名称 cursor for 查询语句;
```
➢ 打开游标
```sql
open 游标名称;
```
➢ 获取游标记录
```sql
fetch 游标名称 into 变量[,变量];
```
➢ 关闭游标
```sql
close 游标名称;
```
**案例**
定义存储过程，完成如下需求
根据传入的参数uage，来查询用户表tb_user中，所有的用户年龄小于等于uage的用户姓名（name）和专业（
profession），并将用户的姓名和专业插入到所创建的一张新表(id,name,profession)中。
⚫ 条件处理程序
条件处理程序（Handler）可以用来定义在流程控制结构执行过程中遇到问题时相应的处理步骤。具体语法为：
```sql
DECLARE handler_action HANDLER FOR condition_value [,condition_value]... statement;

handler_action
    CONTINUE: 继续执行当前程序
    EXIT: 终止执行当前程序
condition_value
    SQLSTATE sqlstate_value: 状态码，如02000
    SQLWARNING: 所有以01开头的SQLSTATE代码的简写
    NOT FOUND: 所有以02开头的SQLSTATE代码的简写
    SQLEXCEPTION: 所有没有被SQLWARNING或NOT FOUND捕获的SQLSTATE代码的简写
```
https://dev.mysql.com/doc/mysql-errors/8.0/en/server-error-reference.html

**案例**
定义存储过程，完成如下需求
根据传入的参数uage，来查询用户表tb_user中，所有的用户年龄小于等于uage的用户姓名（name）和专业（
profession），并将用户的姓名和专业插入到所创建的一张新表(id,name,profession)中。

## 存储函数
存储函数是有返回值的存储过程，存储函数的参数只能是IN类型的。具体语法如下：
```sql
create function 存储函数名称 ([参数列表])
returns type [characteristic ...]
begin
    -- SQL语句
    return ...;
end;

characteristic说明：
    DETERMINISTIC: 相同的输入参数总是产生相同的结果
    NO SQL: 不包含SQL语句
    READS SQL DATA: 包含读取数据的语句，但不包含写入数据的语句
```
**练习**
定义存储函数，完成如下需求
计算从1累加到n的值，n为传入的参数值。

## 触发器
⚫ 介绍
触发器是与表有关的数据库对象，指在 insert/update/delete 之前或之后，触发并执行触发器中定义的SQL语句集合。触发器的这种特
性可以协助应用在数据库端确保数据的完整性 , 日志记录 , 数据校验等操作 。
使用别名 OLD 和 NEW 来引用触发器中发生变化的记录内容，这与其他的数据库是相似的。现在触发器还只支持行级触发，不支持语句
级触发。

⚫ 语法
➢ 创建
```sql
create trigger trigger_name
before/after insert/update/delete
on tbl_name for each row -- 行级触发器
begin
    trigger_stmt;
end;
```
➢ 查看
```sql
show triggers;
```
➢ 删除
```sql
drop trigger [schema_name.] trigger_name;--如果没有指定schema_name，默认为当前数据库 。
```
**练习**
定义触发器，完成如下需求
通过触发器记录 tb_user 表的数据变更日志，将变更日志插入到日志表user_logs中, 包含增加, 修改 , 删除 ;
```sql
create table user_logs (
    id int(10) not null auto_increment,
    operation varchar(20) not null comment '操作类型, insert/update/delete',
    operation_time datetime not null comment '操作时间',
    operation_id int(11) not null comment '操作id',
    operation_params varchar(500) not null comment '操作参数',
    primary key ('id')
)engine=innodb default charset=utf8;
```
