---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/cli
---

# 命令行工具

本指南涵盖了与 RabbitMQ CLI 工具使用相关的多个主题

  * 概述
  * 运行 CLI 工具的安装和要求
  * CLI 工具如何向 RabbitMQ 节点进行身份验证以及如何排查身份验证失败问题
  * 命令行使用方法
  * CLI 工具与集群
  * 如何寻址特定节点
  * CLI 工具在容器化环境中使用的注意事项



## 概述

### 标准 RabbitMQ CLI 工具

RabbitMQ 附带多个命令行工具，每个工具都有一组相关的命令

  * `rabbitmqctl` 用于服务管理和常规操作任务
  * `rabbitmq-diagnostics` 用于诊断、监控和健康检查
  * `rabbitmq-plugins` 用于插件管理
  * `rabbitmq-queues` 用于队列（特别是仲裁队列）的维护任务
  * `rabbitmq-streams` 用于流 (streams) 的维护任务
  * `rabbitmq-upgrade` 用于与升级相关的维护任务



在 Windows 上，上述工具名称将以 `.bat` 结尾，例如 Windows 安装中的 `rabbitmqctl` 名称为 `rabbitmqctl.bat`。

### 附加工具

附加工具是可选的，可以从 GitHub 获取

  * `rabbitmqadmin` v2 用于通过 HTTP API 执行操作任务
  * `rabbitmq-collect-env` 用于收集相关的集群和环境信息以及服务器日志。此工具专用于 Linux 和类 UNIX 操作系统。



不同的工具涵盖不同的使用场景。例如，由于 `rabbitmqctl` 提供对节点的完全控制（包括虚拟主机、用户和权限管理、节点数据上的破坏性操作等），它通常仅对 RabbitMQ 管理员开放。

`rabbitmqadmin` 构建在 HTTP API 之上，使用不同的机制，仅要求 HTTP API 端口对外部连接开放。

尽管 CLI 工具随服务器一起发布，但大多数命令可用于操作远程节点。插件可以提供 CLI 命令，这些命令可被 CLI 工具发现（针对已显式启用的插件）。

## 系统和环境要求

RabbitMQ CLI 工具需要安装兼容的 Erlang/OTP 版本。

工具假定系统语言环境为 UTF-8（例如 `en_GB.UTF-8` 或 `en_US.UTF-8`）。如果不是这种情况，工具可能仍然可以正常工作，但无法保证。在非 UTF-8 环境中会发出警告。

## 安装

除了 `rabbitmqadmin` 之外，上述所有工具都随 RabbitMQ 一起提供，并且可以在安装根目录下的 `sbin` 目录中找到。对于大多数软件包类型，该目录在安装时会添加到 `PATH` 中。这意味着核心工具（如 `rabbitmq-diagnostics` 和 `rabbitmqctl`）在安装了 RabbitMQ 的每个节点上都可用。

通用 UNIX 软件包用户必须确保将安装根目录下的 `sbin` 目录添加到 `PATH` 中，以便更轻松地进行交互式使用。非交互式使用场景可以使用完整路径或相对路径，而无需修改 `PATH` 环境变量。

`rabbitmqadmin` 是一个独立工具，通过 GitHub 发布版本分发。

如果需要从远程节点进行交互，请下载并解压通用 UNIX 软件包或使用 Windows 安装程序。

除了身份验证之外，核心 CLI 工具的所有配置都是可选的。

需要特定参数的命令会在使用说明部分列出它们，并在执行时报告任何缺失的参数。

## 使用 Help 命令发现命令

要找出有哪些可用命令，请使用 `help` 命令

  * bash
  * PowerShell


    
    
    rabbitmqctl help  
    
    
      
    
    
    rabbitmq-diagnostics help  
    
    
    
    rabbitmqctl.bat help  
    
    
      
    
    
    rabbitmq-diagnostics.bat help  
    

该命令可以显示特定命令的使用信息

  * bash
  * PowerShell


    
    
    rabbitmq-diagnostics help status  
    
    
    
    rabbitmqctl.bat help add_vhost  
    
    
      
    
    
    rabbitmq-diagnostics.bat help status  
    

或者，可以使用 `--help` 选项

  * bash
  * PowerShell


    
    
    rabbitmqctl --help  
    
    
      
    
    
    rabbitmq-diagnostics --help  
    
    
    
    rabbitmqctl.bat --help  
    
    
      
    
    
    rabbitmq-diagnostics.bat --help  
    

包括针对单个命令

  * bash
  * PowerShell


    
    
    rabbitmq-diagnostics status --help  
    
    
    
    rabbitmq-diagnostics.bat status --help  
    

## rabbitmqctl

rabbitmqctl 是随 RabbitMQ 提供的原始 CLI 工具。它支持广泛的操作，主要是管理（操作）性质的。

这包括

  * 停止节点
  * 访问节点状态、有效配置、健康检查
  * 虚拟主机管理
  * 用户和权限管理
  * 策略管理
  * 列出队列、连接、通道、交换机、消费者
  * 集群成员管理



等等。

`rabbitmqctl` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## rabbitmq-queues

rabbitmq-queues 允许操作员管理复制队列的副本。它随 RabbitMQ 提供。

大多数命令仅支持在线模式（目标节点正在运行时）。

`rabbitmq-queues` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## rabbitmq-streams

rabbitmq-streams 允许操作员管理流的副本。它随 RabbitMQ 提供。

大多数命令仅支持在线模式（目标节点正在运行时）。

`rabbitmq-streams` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## rabbitmq-diagnostics

rabbitmq-diagnostics 是检查节点状态的主要工具。它拥有许多命令，允许操作员研究系统的各个方面。它随 RabbitMQ 提供。

它支持在线模式（目标节点正在运行时）和离线模式（更改在节点重启后生效）。

`rabbitmq-diagnostics` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## rabbitmq-plugins

rabbitmq-plugins 是一个管理插件的工具：列出、启用和禁用它们。它随 RabbitMQ 提供。

它支持在线模式（目标节点正在运行时）和离线模式（更改在节点重启后生效）。

`rabbitmq-plugins` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## rabbitmq-upgrade

rabbitmq-upgrade 是专门用于升级前、升级和升级后操作的工具。它随 RabbitMQ 提供。

大多数命令仅支持在线模式（目标节点正在运行时）。

`rabbitmq-upgrade` 使用与服务器节点之间的共享密钥身份验证机制（详见下文）。

## 离线模式

`--offline` 是 `rabbitmq-plugins` 命令支持的一个标志。提供该标志时，工具将避免连接目标节点，而是直接操作插件文件。

使用 `--offline` 标志时，命令将依赖环境变量来确定从哪里查找本地节点的插件目录。

例如，它将遵循并使用 `RABBITMQ_PLUGINS_DIR` 环境变量的值，就像 RabbitMQ 节点一样。当为服务器节点重写 `RABBITMQ_PLUGINS_DIR` 时，也必须为调用 CLI 工具的本地操作系统用户设置相同的值。

## 身份验证

除了 `rabbitmqadmin` 之外，RabbitMQ 工具使用共享密钥身份验证机制。这要求节点间通信端口和 CLI 通信端口（默认情况下）对目标节点上的外部连接开放。

## 针对远程服务器节点使用 CLI 工具

CLI 工具可用于与远程节点以及本地节点进行通信。节点由节点名称标识。如果没有指定节点名称，则假定目标为 `rabbit@{本地主机名}`。在连接远程节点时，适用相同的身份验证要求。

要连接远程节点，请使用 `rabbitmqctl`、`rabbitmq-diagnostics` 和其他核心 CLI 工具接受的 `--node` (`-n`) 选项。以下示例连接到节点 `rabbit@remote-host.local` 以查找其状态
    
    
    rabbitmq-diagnostics status -n rabbit@remote-host.local  
    

某些命令，例如
    
    
    rabbitmq-diagnostics status  
    

可用于任何节点。其他命令，例如
    
    
    rabbitmqctl shutdown  
    

或
    
    
    rabbitmqctl wait  
    

只能在与其目标节点相同的主机或容器中运行。这些命令通常依赖或修改本地环境中的某些内容，例如本地的已启用插件文件。

### 节点名称

RabbitMQ 节点由节点名称标识。节点名称由两部分组成：前缀（通常为 `rabbit`）和主机名。例如，`rabbit@node1.messaging.svc.local` 是一个节点名称，其前缀为 `rabbit`，主机名为 `node1.messaging.svc.local`。

集群中的节点名称必须唯一。如果给定主机上运行多个节点（在开发和 QA 环境中通常如此），它们必须使用不同的前缀，例如 `rabbit1@hostname` 和 `rabbit2@hostname`。

CLI 工具使用节点名称来识别和寻址服务器节点。大多数 CLI 命令都是针对一个称为目标节点的节点调用的。要指定目标节点，请使用 `--node` (`-n`) 选项。例如，要在节点 `rabbit@warp10.local` 上运行健康检查
    
    
    rabbitmq-diagnostics -n rabbit@warp10 check_alarms  
    

某些命令同时接受目标节点和其他节点名称。例如，`rabbitmqctl forget_cluster_node` 既接受目标节点（将执行该操作），也接受要移除的节点的名称。

在集群中，节点使用节点名称相互识别和联系。有关详情，请参阅集群指南。

当节点启动时，它会检查是否已分配节点名称。这是通过 `RABBITMQ_NODENAME` 环境变量完成的。如果没有显式配置值，节点会解析其主机名并在其前面加上 `rabbit` 来计算其节点名称。

如果系统对主机名使用完全限定域名 (FQDN)，则必须将 RabbitMQ 节点和 CLI 工具配置为使用所谓的长节点名称。对于服务器节点，这通过将 `RABBITMQ_USE_LONGNAME` 环境变量设置为 `true` 来完成。

对于 CLI 工具，必须设置 `RABBITMQ_USE_LONGNAME` 或指定 `--longnames` 选项
    
    
    # this example assumes that host1.messaging.eng.coolcorporation.banana is a hostname  
    
    
    # that successfully resolves  
    
    
    rabbitmq-diagnostics -n rabbit@host1.messaging.eng.coolcorporation.banana check_alarms --longnames  
    

### 容器化环境中的注意事项

当 RabbitMQ 在容器中运行时，运行 CLI 工具通常有两种方式

  1. 在容器内部运行，使用 `docker exec` 及类似工具
  2. 转发相关的节点间通信端口并从主机运行



这种方法可能会出现两个常见问题。

#### 主机和容器之间的共享密钥不匹配

当在主机上运行 CLI 工具时，本地共享密钥必须与容器中的匹配。如果不匹配，CLI 工具将无法进行身份验证，也无法对目标节点执行任何操作。

#### 共享密钥播种竞争条件

危险

如果容器使用的共享密钥没有预先播种，则必须在对节点运行 CLI 命令之前允许该节点启动

当 CLI 工具在未预播种共享密钥的主机上运行，且在本地启动的 RabbitMQ 节点有机会创建 cookie 文件之前运行时，会出现一种令人困惑的情况：播种的密钥可能会在节点启动期间被覆盖。

结果是，CLI 工具可能无法进行身份验证，RabbitMQ 节点可能无法访问创建的文件并因此报错停止，以及源于密钥不匹配的其他问题场景。

## 选项和位置参数

RabbitMQ CLI 工具主要遵循现有的、长期建立的命令行参数解析约定。本节提供了一些示例，并侧重于边缘情况和鲜为人知的功能。

不同的命令接受不同的参数。有些是命名选项，如 `--node`（别名为 `-n`），另一些是位置参数，如用户名和密码参数
    
    
    rabbitmqctl add_user <username> <password>  
    

一个具体示例
    
    
    rabbitmqctl add_user "a-user" "a-pa$$w0rd"  
    

选项可以在位置参数之前或之后提供，但有一个例外：双连字符 (`--`) 之后的所有内容都将被视为位置参数
    
    
    # all values after the double hyphen (--) will be treated as positional arguments,  
    
    
    # even if they begin with a hyphen or a double hyphen  
    
    
    rabbitmqctl add_user --node rabbit@host1.messaging.eng.coolcorporation.banana -- "a-user" "a-pa$$w0rd"  
    

当位置参数以连字符或双连字符（例如生成的密码）开头时，必须使用显式位置参数分隔符，以确保它们不会被解析为选项
    
    
    # Since "--!a-pa$$w0rd" is explicitly provided as a positional argument, it won't  
    
    
    # be mistakenly considered for an unsupported option, even though it starts with a double hyphen  
    
    
    rabbitmqctl add_user --node rabbit@host1.messaging.eng.coolcorporation.banana -- "a-user" "--!a-pa$$w0rd"  
    

选项值可以作为 `--option <value>` 或 `--option=<value>` 传递。当值以连字符 (`-`) 开头时，必须使用后一种变体，否则它将被视为一个选项
    
    
    # an alternative way of providing an option value  
    
    
    rabbitmqctl add_user --node=rabbit@host1.messaging.eng.coolcorporation.banana -- "a-user" "a-pa$$w0rd"  
    

`rabbitmqctl`、`rabbitmq-diagnostics`、`rabbitmq-plugins` 和 `rabbitmq-queues` 支持命令别名。

## CLI 工具如何向节点（以及节点相互之间）进行身份验证：Erlang Cookie

RabbitMQ 节点和 CLI 工具（`rabbitmqadmin` 除外）使用 cookie 来确定它们是否被允许相互通信。为了使 CLI 工具和节点能够通信，它们必须拥有相同的共享密钥，称为 Erlang cookie。cookie 只是一个长度不超过 255 个字符的字母数字字符串。它通常存储在本地文件中。该文件必须仅对所有者可见（例如具有 `600` 或类似的 UNIX 权限）。每个集群节点都必须拥有相同的 cookie。

如果文件不存在，当 RabbitMQ 服务器启动时，Erlang VM 会自动创建一个具有随机生成值的 cookie 文件。

Erlang cookie 的生成应在集群部署阶段完成，最好使用自动化和编排工具。

### Cookie 文件位置

#### Linux, MacOS, *BSD

在 UNIX 系统上，cookie 通常位于 `/var/lib/rabbitmq/.erlang.cookie`（供服务器使用）和 `$HOME/.erlang.cookie`（供 CLI 工具使用）。请注意，由于 `$HOME` 的值因用户而异，因此必须为使用 CLI 工具的每个用户放置一份 cookie 文件副本。这适用于非特权用户和 `root`。

RabbitMQ 节点将在启动时尽早记录其有效用户的主目录位置。

#### 社区 Docker 镜像和 Kubernetes

Docker 社区 RabbitMQ 镜像使用 `RABBITMQ_ERLANG_COOKIE` 环境变量的值来填充 cookie 文件。

使用此镜像的配置管理和容器编排工具必须确保集群中的每个 RabbitMQ 节点容器都使用相同的值。

在 Kubernetes 环境中，该值必须在部署文件中指定。例如，这可以在 RabbitMQ on Kubernetes 示例仓库中看到。

#### Windows

在 Windows 上，cookie 的位置取决于几个因素

  * 是否同时设置了 `HOMEDRIVE` 和 `HOMEPATH` 环境变量
  * Erlang 版本：早于 20.2（任何受维护的 RabbitMQ 发布系列都不再支持这些版本）或 20.2 及更高版本



##### Erlang 20.2 或更高版本

对于 20.2 及更高版本的 Erlang，cookie 文件的位置是

  * `%HOMEDRIVE%%HOMEPATH%\.erlang.cookie`（如果同时设置了 `HOMEDRIVE` 和 `HOMEPATH`，对于用户 `%USERNAME%` 通常为 `C:\Users\%USERNAME%\.erlang.cookie`）
  * `%USERPROFILE%\.erlang.cookie`（通常为 `C:\Users\%USERNAME%\.erlang.cookie`，如果未同时设置 `HOMEDRIVE` 和 `HOMEPATH`）
  * 对于 RabbitMQ Windows 服务 - `%USERPROFILE%\.erlang.cookie`（通常为 `C:\WINDOWS\system32\config\systemprofile`）



如果使用了 Windows 服务，则应将 cookie 从 `C:\Windows\system32\config\systemprofile\.erlang.cookie` 复制到运行如 `rabbitmqctl.bat` 等命令的用户所期望的位置。

### 使用 CLI 和运行时命令行参数覆盖

作为替代方案，可以将选项 "`-setcookie <value>`" 添加到 `RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS` 环境变量值中，以重写 RabbitMQ 节点使用的 cookie 值
    
    
    RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS="-setcookie cookie-value"  
    

CLI 工具可以使用命令行标志获取 cookie 值
    
    
    rabbitmq-diagnostics status --erlang-cookie "cookie-value"  
    

这两种方法都是**安全性最差的选项** ，通常**不建议使用** 。

### 故障排除

#### CLI 工具

从 版本 `3.8.6` 开始，`rabbitmq-diagnostics` 包含一个命令，该命令提供有关 CLI 工具所使用的 Erlang cookie 文件的相关信息
    
    
    rabbitmq-diagnostics erlang_cookie_sources  
    

该命令将报告有效用户、用户主目录以及 cookie 文件的预期位置
    
    
    Cookie File  
    
    
      
    
    
    Effective user: antares  
    
    
    Effective home directory: /home/cli-user  
    
    
    Cookie file path: /home/cli-user/.erlang.cookie  
    
    
    Cookie file exists? true  
    
    
    Cookie file type: regular  
    
    
    Cookie file access: read  
    
    
    Cookie file size: 20  
    
    
      
    
    
    Cookie CLI Switch  
    
    
      
    
    
    --erlang-cookie value set? false  
    
    
    --erlang-cookie value length: 0  
    
    
      
    
    
    Env variable  (Deprecated)  
    
    
      
    
    
    RABBITMQ_ERLANG_COOKIE value set? false  
    
    
    RABBITMQ_ERLANG_COOKIE value length: 0  
    

#### 服务器节点

当节点启动时，它将记录其有效用户的主目录位置
    
    
    node           : rabbit@cdbf4de5f22d  
    
    
    home dir       : /var/lib/rabbitmq  
    

除非重写了任何服务器目录，否则这就是查找 cookie 文件的目录，如果该文件尚不存在，节点将在首次启动时创建它。

在上面的示例中，cookie 文件的位置将是 `/var/lib/rabbitmq/.erlang.cookie`。

#### 主机名解析

从 RabbitMQ `3.8.6` 开始，CLI 工具提供了两个命令来帮助验证节点上的主机名解析是否按预期工作。这些命令并不旨在取代 `dig` 和其他专用 DNS 工具，而是提供了一种在考虑 Erlang 运行时主机名解析器功能的同时执行大多数基本检查的方法。

这些命令在网络指南中介绍。

## 身份验证失败

当 cookie 配置错误（例如不一致）时，RabbitMQ 节点将记录诸如 "Connection attempt from disallowed node", "", "Could not auto-cluster" 等错误。

例如，当 CLI 工具连接并尝试使用不匹配的密钥值进行身份验证时
    
    
    2020-06-15 13:03:33 [error] <0.1187.0> ** Connection attempt from node 'rabbitmqcli-99391-rabbit@warp10' rejected. Invalid challenge reply. **  
    

当 `rabbitmqctl` 等 CLI 工具无法向 RabbitMQ 进行身份验证时，消息通常显示为
    
    
    * epmd reports node 'rabbit' running on port 25672  
    
    
    * TCP connection succeeded but Erlang distribution failed  
    
    
    * suggestion: hostname mismatch?  
    
    
    * suggestion: is the cookie set correctly?  
    
    
    * suggestion: is the Erlang distribution using TLS?  
    

这意味着从 CLI 工具到 RabbitMQ 节点的 TCP 连接成功，但服务器拒绝了身份验证尝试。该消息还提到了最常见的几个原因，将在下面介绍。

#### 可能原因 1：Cookie 文件位置错误或缺失

cookie 文件位置不正确或 cookie 值不匹配是此类失败的最常见场景。

RabbitMQ 节点在启动时记录其 cookie 哈希值。CLI 工具在无法向目标节点进行身份验证时会打印其 cookie 哈希值。

当使用较新的 Erlang/OTP 版本时，身份验证失败包含更多信息，可以更好地识别 cookie 不匹配
    
    
    rabbit@warp10:  
    
    
      * connected to epmd (port 4369) on warp10  
    
    
      * epmd reports node 'rabbit' running on port 25672  
    
    
      * TCP connection succeeded but Erlang distribution failed  
    
    
      
    
    
      * Authentication failed (rejected by the remote node), please check the Erlang cookie  
    
    
      
    
    
    current node details:  
    
    
    - node name: 'rabbitmq-cli-63@warp10'  
    
    
    - home dir: /home/username  
    
    
    - cookie hash: Sg08R8+G85EYHZ3H/9NUfg==  
    

#### 可能原因 2：节点名称类型不匹配

如果 RabbitMQ 节点被配置为使用长节点名称（将 `RABBITMQ_USE_LONGNAME` 导出为 `true`），则 CLI 工具也应通过相同的环境变量或 3.7.0 中引入的 `--longnames` 命令行标志进行配置。

#### 可能原因 3：节点间连接需要 TLS

如果 RabbitMQ 被设置为使用 TLS 加密节点间和 CLI 连接，CLI 工具也必须使用 TLS，因此需要额外的选项。来自其他节点和 CLI 工具的非 TLS 连接将失败。

#### 可能原因 4：主机名不匹配

其他原因包括目标 RabbitMQ 节点使用的节点名称与提供给 CLI 工具的节点名称（例如通过 `-n` 标志）之间的主机名不匹配。例如，如果节点运行时的名称为 `rabbit@rmq1.eng.megacorp.local`，但调用 `rabbitmqctl` 时为
    
    
    rabbitmq-diagnostics status -n rabbit@rmq-dev.eng.megacorp.local  
    

那么即使 `rmq-dev.eng.megacorp.local` 和 `rmq1.eng.megacorp.local` 解析为同一个 IP 地址，服务器也会拒绝 `rabbitmqctl` 的身份验证尝试。这种情况相对罕见。

当使用较新的 Erlang/OTP 版本时，身份验证失败包含更多信息，可以更好地识别主机名不匹配
    
    
    rabbit@localhost:  
    
    
      * connected to epmd (port 4369) on localhost  
    
    
      * epmd reports node 'rabbit' running on port 25672  
    
    
      * TCP connection succeeded but Erlang distribution failed  
    
    
      
    
    
      * Hostname mismatch: node "rabbit@warp10" believes its host is different. Please ensure that hostnames resolve the same way locally and on "rabbit@warp10"  
    
    
      
    
    
      
    
    
    current node details:  
    
    
    - node name: 'rabbitmq-cli-30@warp10'  
    
    
    - home dir: /Users/antares  
    
    
    - cookie hash: Sg08R8+G85EYHZ3H/9NUfg==  
    

#### 其他可能原因

正如任何网络连接一样，CLI 到节点的连接可能会因以下原因失败

  * 主机名解析失败
  * 错误的 IP 路由
  * TCP 端口访问被阻止（防火墙等）



等等。

RabbitMQ 网络指南包含有关排除网络相关问题的一节。

## 管理节点

### 获取节点状态

要检索节点状态，请使用 `rabbitmq-diagnostics status` 或 `rabbitmq-diagnostics.bat status`，并带有可选的 `--node` 目标

  * bash
  * PowerShell


    
    
    rabbitmq-diagnostics  status  
    
    
      
    
    
    rabbitmq-diagnostics  status --node rabbit@target-hostname.local  
    
    
    
    rabbitmq-diagnostics .bat status  
    
    
      
    
    
    rabbitmq-diagnostics .bat status --node rabbit@target-hostname.local  
    

### 启动节点

RabbitMQ 节点的启动方式取决于所使用的软件包类型

  * 当在现代 Linux 发行版上使用 Debian 和 RPM 软件包时，节点使用 `systemd` 进行管理
  * 当使用 Windows 安装程序时，节点通常由 Windows 服务管理器进行管理
  * 当使用 Homebrew 公式时，节点使用 `brew services` 进行管理
  * 当使用通用 UNIX 构建或 Windows 二进制构建时，节点分别使用安装根目录下的 `sbin/rabbitmq-server` 和 `sbin/rabbitmq-server.bat` 启动



### 停止节点

要停止节点，请考虑使用启动节点时所使用的相同服务管理工具，这取决于安装 RabbitMQ 时使用的软件包类型。

要使用 RabbitMQ CLI 工具停止节点，请使用 `rabbitmqctl shutdown` 或 `rabbitmqctl.bat shutdown`，并带有可选的 `--node` 目标

  * bash
  * PowerShell


    
    
    rabbitmqctl shutdown  
    
    
    rabbitmqctl shutdown --node rabbit@target-hostname.local  
    
    
    
    rabbitmqctl.bat shutdown  
    
    
    rabbitmqctl.bat shutdown --node rabbit@target-hostname.local  
    

## rabbitmqadmin

rabbitmqadmin 是一个构建在 RabbitMQ HTTP API 之上的命令行工具。它不是 `rabbitmqctl` 的替代品，并提供对管理 UI 提供的大多数常用操作的子集的访问。

`rabbitmqadmin` 使用 HTTP API 身份验证机制（基本 HTTP 身份验证）。

它是一个原生二进制文件，必须从 RabbitMQ 分发版中单独下载。

## “节点本地”和“集群范围”命令

客户端连接、通道和队列将分布在集群节点上。操作员需要能够检查和监控集群中所有节点的此类资源。

CLI 工具（如 rabbitmqctl 和 `rabbitmq-diagnostics`）提供了检查资源和集群范围状态的命令。有些命令专注于单个节点的状态（例如 `rabbitmq-diagnostics environment` 和 `rabbitmq-diagnostics status`），另一些则检查集群范围的状态。后者的示例包括 `rabbitmqctl list_connections`、`rabbitmqctl list_mqtt_connections`、`rabbitmqctl list_stomp_connections`、`rabbitmqctl list_users`、`rabbitmqctl list_vhosts` 等等。

此类“集群范围”命令通常会先连接到一个节点，发现集群成员，然后联系所有节点以检索并汇总它们各自的状态。例如，`rabbitmqctl list_connections` 将联系所有节点，检索它们的 AMQP 0-9-1 和 AMQP 1.0 连接，并将它们全部显示给用户。用户无需手动联系所有节点。

假设集群处于不变状态（例如没有连接被关闭或打开），针对两个不同节点依次执行的两个 CLI 命令将产生相同或语义相同的结果。然而，“节点本地”命令可能不会产生相同的结果，因为很少有两个节点拥有完全相同的状态。

## 插件提供的命令

RabbitMQ 插件可以提供可由 `rabbitmq-diagnostics`、`rabbitmq-queues`、`rabbitmqctl` 等工具发现的 CLI 命令。要使插件命令可被发现，**必须显式启用** 该插件。

在执行命令发现时，CLI 工具将查阅已启用插件文件，以确定要扫描哪些插件来查找命令。如果插件未包含在该文件中（例如因为它作为依赖项被隐式启用），它将不会列在已启用插件文件中，因此其 CLI 命令**将不会被发现** ，并且不可用。

使用 `help` 命令查看有哪些可用命令，包括核心命令和插件提供的命令。

## 命令别名

`rabbitmqctl`、`rabbitmq-diagnostics` 和 `rabbitmq-plugins` 支持命令别名。别名提供了一种定义某些命令及其参数的缩写版本的方法。例如，与其键入 `rabbitmqctl environment`，定义一个别名 `rabbitmqctl env`（它会扩展为 `rabbitmqctl environment`）可能更方便。

别名从通过 `RABBITMQ_CLI_ALIASES_FILE` 环境变量指定的文件加载
    
    
    export RABBITMQ_CLI_ALIASES_FILE=/path/to/cli_aliases.conf  
    

别名文件使用极简的 ini 风格 `alias = command` 格式，例如
    
    
    env = environment  
    
    
    st  = status --quiet  
    
    
      
    
    
    lp  = list_parameters --quiet  
    
    
    lq  = list_queues --quiet  
    
    
    lu  = list_users --quiet  
    
    
      
    
    
    cs  = cipher_suites --openssl-format --quiet  
    

有了这个别名文件，就可以使用
    
    
    rabbitmqctl env  
    

它将扩展为
    
    
    rabbitmqctl environment  
    

或
    
    
    rabbitmqctl lq  
    

它将扩展为
    
    
    rabbitmqctl list_queues --quiet  
    

上面示例中的最后一个别名配置了一个 `rabbitmq-diagnostics` 命令
    
    
    rabbitmq-diagnostics cs  
    

将扩展为
    
    
    rabbitmq-diagnostics cipher_suites --openssl-format --quiet  
    

所有工具以相同的方式处理别名。只要扩展后的命令被识别，别名就可以与任何工具配合使用，甚至可以跨多个工具使用。例如，`rabbitmqctl` 和 `rabbitmq-diagnostics` 都提供 `environment` 命令，因此 `env` 别名对两者以完全相同的方式工作
    
    
    rabbitmq-diagnostics env  
    

将扩展为
    
    
    rabbitmq-diagnostics environment  
    

只有在工具本身不提供调用的命令时，才会查阅该文件。
