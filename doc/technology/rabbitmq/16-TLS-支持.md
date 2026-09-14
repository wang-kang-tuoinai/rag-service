---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/ssl
---

# TLS 支持

RabbitMQ 内置了对 TLS 的支持。这包括客户端连接以及适用的流行插件，例如 Federation 链接。也可以使用 TLS 来加密集群中的节点间连接。

本指南涵盖了与 RabbitMQ 中 TLS 相关的各种主题，重点是客户端连接。

  * 两种使用 TLS 的方式用于客户端连接：直接使用或通过 TLS 终止代理
  * TLS 支持的 Erlang/OTP 要求
  * 在 RabbitMQ 中启用 TLS
  * 如何为开发和 QA 环境生成自签名证书：使用 tls-gen 或手动生成
  * Java 和 .NET 客户端中的 TLS 配置
  * 客户端连接的对等方（证书链）验证或双向验证（"mTLS"）
  * 与 RabbitMQ 服务器和客户端相关的公共扩展密钥用法选项 (EKU)
  * 如何控制启用的 TLS 版本和密码套件
  * TLSv1.3 支持
  * 可用于评估 TLS 设置的工具
  * 证书和密钥轮换
  * 适用于仅需一组叶子证书进行对等验证（不实际遍历证书链）环境的 Trust Store 插件
  * 基于客户端证书的身份验证
  * 已知的 TLS 攻击及其缓解措施
  * 如何使用私钥密码



等等。

## 从哪里学习 TLS 基础知识

本指南试图解释 TLS 的基础知识，但它并不是 TLS、加密、公钥基础设施 (PKI) 及相关主题的入门教程，因此相关概念仅作简要介绍。

网络上可以找到许多面向初学者的 TLS 入门教程。

  * 一
  * 二
  * 三
  * 四



## TLS 与消息传递协议

TLS 可以为 RabbitMQ 支持的所有协议启用。但是，本指南主要关注 AMQP 1.0 和 AMQP 0-9-1 监听器。有关这些协议的 TLS 配置示例，请参阅 RabbitMQ 流协议、MQTT、STOMP、MQTT-over-WebSockets 和 STOMP-over-WebSockets 指南。

HTTP API、节点间流量和 CLI 工具流量也可以配置为使用 TLS (HTTPS)。

要在 Kubernetes 上使用 RabbitMQ 集群运算符配置 TLS，请参阅配置 TLS 指南。

有关常见 TLS 故障排除技术的概述，请参阅排查 TLS 相关问题和排查网络问题。

## RabbitMQ 客户端连接的常用 TLS 方法

对于客户端连接，有两种常见方法：

  * 配置 RabbitMQ 以处理 TLS 连接。
  * 使用代理或负载均衡器（例如 HAproxy）来执行客户端连接的 TLS 终止，并使用普通的 TCP 连接到 RabbitMQ 节点。



这两种方法都是有效的，各有优缺点。本指南将重点介绍第一种方案。本指南的某些部分对于选择第二种方案的环境仍然适用。

## TLS 支持的 Erlang/OTP 要求

为了支持 TLS 连接，RabbitMQ 需要 Erlang/OTP 安装中提供 TLS 和加密相关模块。建议与 TLS 一起使用的 Erlang/OTP 版本是最近的受支持 Erlang 版本。较早的版本即使受支持，也可能适用于大多数证书，但存在已知限制（见下文）。

必须安装并启用 Erlang 的 `asn1`、`crypto`、`public_key` 和 `ssl` 库（应用程序）。在 Debian 和 Ubuntu 上，这分别由 erlang-asn1、erlang-crypto、erlang-public-key 和 erlang-ssl 软件包提供。用于 RabbitMQ 的零依赖 Erlang RPM 包含上述模块。

如果 Erlang/OTP 是从源代码编译的，则必须确保 `configure` 能够找到 OpenSSL 并构建上述库。

在调查 TLS 连接问题时，请记住，绝大多数情况下这些问题是环境特定的（例如，证书丢失在受信任证书存储中），并不代表 Erlang/OTP 的 TLS 实现存在错误或限制。请先按照排查 TLS 指南中概述的步骤收集更多信息。

## 已知的不兼容和限制

如果预计使用椭圆曲线加密 (ECC) 密码套件，强烈建议使用最近的受支持 Erlang 版本。较早的版本在 ECC 支持方面存在已知限制。

如果您遇到上述限制或任何其他不兼容问题，请使用 TLS 终止选项（见上文）。

## TLS 基础知识：证书颁发机构、证书、密钥

TLS 是一个庞大且相当复杂的话题。在解释如何在 RabbitMQ 中启用 TLS 之前，有必要简要介绍本指南中使用的一些概念。本节刻意简短，并简化了一些内容。其目标是让读者开始为 RabbitMQ 和应用程序启用 TLS。

网络上可以找到许多面向初学者的 TLS 入门教程。

  * 一
  * 二
  * 三
  * 四



为了透彻理解 TLS 并充分利用它，我们建议使用其他资源，例如《Network Security with OpenSSL》。

### TLS 的两个主要目标

TLS 有两个主要目的：加密连接流量和提供一种验证（verify）对等方的方法，以防范中间人攻击。两者都是通过一组称为公钥基础设施 (PKI) 的角色、策略和程序来实现的。

PKI 基于可以进行加密（数学）验证的数字身份概念。这些身份被称为 _证书_ ，或者更准确地说是 _证书/密钥对_ 。每个支持 TLS 的服务器通常都有自己的证书/密钥对，用于计算将用于加密连接上发送的流量的连接特定密钥。

此外，如果被要求，它可以向连接对等方出示其证书（公钥）。客户端可能有也可能没有自己的证书。在消息传递和 RabbitMQ 等工具的上下文中，客户端也使用证书/密钥对以便服务器可以验证其身份是非常常见的。

### 证书、私钥和证书颁发机构

证书/密钥对由 OpenSSL 等工具生成，并由称为 _证书颁发机构 (CA)_ 的实体签名。CA 颁发用户（应用程序或其他 CA）使用的证书。当证书由 CA 签名时，它们形成一个 _信任链_ 。此类链可以包含多个 CA，但最终会签署应用程序使用的证书/密钥对（ _叶子_ 或 _最终用户_ 证书）。CA 证书链通常以单个文件的形式分发。这样的文件称为 _CA 捆绑包_ 。

这是一个包含一个根 CA 和一个叶子（服务器或客户端）证书的最基本链的示例：

带有中间证书的链可能如下所示：

有一些组织签署并颁发证书/密钥对。其中大多数是广受信任的 CA，并对其服务收取费用。

支持 TLS 的 RabbitMQ 节点必须拥有它认为受信任的一组证书颁发机构证书（位于一个文件中，即 CA 捆绑包）、一个证书（公钥）文件和一个私钥文件。这些文件将从本地文件系统读取。它们必须可由 RabbitMQ 节点进程的有效用户读取。

支持 TLS 的连接的两端均可选择验证连接的另一端。在这样做时，它们会尝试在对等方提供的证书列表中定位受信任的证书颁发机构。当双方执行此验证过程时，这称为 _双向 TLS 身份验证_ 或 _mTLS_ 。更多详细信息请参阅对等方验证部分。

本指南假设用户可以访问证书颁发机构以及两种证书/密钥对，并以多种格式供不同的客户端库使用。最好使用现有工具来完成此操作，但对于那些希望更熟悉该主题和 OpenSSL 命令行工具的人来说，有一个单独的部分。

在生产环境中，证书由商业证书颁发机构或由内部安全团队颁发的证书颁发机构生成。在这些情况下，证书颁发机构捆绑包文件很可能包含多个证书。只要满足相同的基本文件和路径要求，这不会改变配置 RabbitMQ 时使用捆绑包文件的方式。换句话说，无论证书是自签名的还是由受信任 CA 颁发的，它们的配置方式都是相同的。对等方验证部分对此进行了详细介绍。

## 生成 CA、证书和密钥的快捷方式

本指南假设用户可以访问 CA 证书捆绑包文件和两个证书/密钥对。证书/密钥对由 RabbitMQ 和连接到服务器 TLS 端口的客户端使用。生成证书颁发机构和两个密钥对的过程相当繁琐且容易出错。在 MacOS 或 Linux 上生成所有这些内容的一个更简单的方法是使用 tls-gen：它需要 `PATH` 中有 `Python 3.5+`、`make` 和 `openssl`。

请注意，`tls-gen` 及其生成的证书/密钥对是自签名的，仅适用于开发和测试环境。绝大多数生产环境应使用由广受信任的商业 CA 颁发的证书和密钥。

`tls-gen` 支持 RSA 和椭圆曲线加密 (ECC) 算法来进行密钥生成。

### 使用 tls-gen 的基本配置文件

下面是一个示例，它生成一个 CA 并使用它生成两个证书/密钥对，一个用于服务器，另一个用于客户端。这是本指南其余部分所期望的设置。
    
    
    git clone https://github.com/rabbitmq/tls-gen tls-gen  
    
    
    cd tls-gen/basic  
    
    
    # private key password  
    
    
    make PASSWORD=bunnies  
    
    
    make verify  
    
    
    make info  
    
    
    ls -l ./result  
    

此基本 tls-gen 配置文件生成的证书链如下所示：

## 在 RabbitMQ 中启用 TLS 支持

要启用 RabbitMQ 中的 TLS 支持，必须配置节点以知晓证书颁发机构捆绑包（包含一个或多个 CA 证书的文件）、服务器证书文件和服务器密钥的位置。还应启用 TLS 监听器，以明确在哪个端口上监听支持 TLS 的客户端连接。可以配置更多与 TLS 相关的内容。这些内容将在本指南的其余部分介绍。

以下是与 TLS 相关的基本配置设置：

配置键| 描述  
---|---  
`listeners.ssl`| 用于监听 TLS 连接的端口列表。RabbitMQ 可以监听单个接口或多个接口。  
`ssl_options.cacertfile`| 证书颁发机构 (CA) 捆绑包文件路径  
`ssl_options.certfile`| 服务器证书文件路径  
`ssl_options.keyfile`| 服务器私钥文件路径  
`ssl_options.password`| 私钥文件的密码  
`ssl_options.verify`| 是否应启用对等方验证？  
`ssl_options.fail_if_no_peer_cert`| 当设置为 `true` 时，如果客户端未能提供证书，TLS 连接将被拒绝  
  
这些选项在配置文件中提供。下面是一个配置文件示例，它将在该主机名上的所有接口上启动一个端口为 5671 的 TLS 监听器：
    
    
    listeners.ssl.default = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.verify     = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = true  
    
    
      
    
    
    # If the private key file is password protected, set this value:  
    
    
    # ssl_options.password = PASSWORD  
    

此配置还将执行对等方证书链验证，因此没有证书的客户端将被拒绝。

可以完全禁用常规（非 TLS）监听器。只有启用 TLS 的客户端才能连接到此类节点，并且仅当它们使用正确的端口时才能连接：
    
    
    # disables non-TLS listeners, only TLS-enabled clients will be able to connect  
    
    
    listeners.tcp = none  
    
    
      
    
    
    listeners.ssl.default = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.verify     = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = true  
    

TLS 设置也可以使用经典配置格式进行配置：
    
    
    [  
    
    
      {rabbit, [  
    
    
         {ssl_listeners, [5671]},  
    
    
         {ssl_options, [{cacertfile, "/path/to/ca_certificate.pem"},  
    
    
                        {certfile,   "/path/to/server_certificate.pem"},  
    
    
                        {keyfile,    "/path/to/server_key.pem"},  
    
    
                        {verify,     verify_peer},  
    
    
                        {fail_if_no_peer_cert, true}]}  
    
    
       ]}  
    
    
    ].  
    

### 证书和私钥文件路径

RabbitMQ 必须能够读取其配置的 CA 证书捆绑包、服务器证书和私钥。这些文件必须存在并具有适当的权限。如果不是这种情况，节点将无法启动或无法接受启用 TLS 的连接。

**Windows 用户注意** ：在 Windows 上，配置文件中的反斜杠 ("\") 被解释为转义序列。例如，要指定 Windows 上 CA 证书的路径 `c:\ca_certificate.pem`，需要使用 `"c:\\ca_certificate.pem"` 或 `"c:/ca_certificate.pem"`。

### 如何验证是否启用了 TLS

要验证节点上是否已启用 TLS，请重新启动它并检查其日志文件。它应该包含一条关于启用 TLS 监听器的条目，如下所示：
    
    
    2020-07-13 21:13:01.015 [info] <0.573.0> started TCP listener on [::]:5672  
    
    
    2020-07-13 21:13:01.055 [info] <0.589.0> started TLS (SSL) listener on [::]:5671  
    

另一种方法是使用 `rabbitmq-diagnostics listeners`，它应该包含已启用 TLS 的监听器的行：
    
    
    rabbitmq-diagnostics listeners  
    
    
    #  
    
    
    # ... (some output omitted for brevity)  
    
    
    # => Interface: [::], port: 5671, protocol: amqp/ssl, purpose: AMQP 0-9-1 and AMQP 1.0 over TLS  
    
    
    # ...  
    

### 提供私钥密码

私钥可以有选择地使用密码进行保护。要提供密码，请使用 `password` 选项：
    
    
    listeners.ssl.1 = 5671  
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.password   = t0p$3kRe7  
    

使用经典配置格式的相同示例：
    
    
    [  
    
    
     {rabbit, [  
    
    
               {ssl_listeners, [5671]},  
    
    
               {ssl_options, [{cacertfile,"/path/to/ca_certificate.pem"},  
    
    
                              {certfile,  "/path/to/server_certificate.pem"},  
    
    
                              {keyfile,   "/path/to/server_key.pem"},  
    
    
                              {password,  "t0p$3kRe7"}  
    
    
                             ]}  
    
    
              ]}  
    
    
    ].  
    

经典配置文件格式允许配置值加密，这对于密码是推荐的做法。

## TLS 对等方验证：你如何证明你是谁？

如证书和密钥部分所述，TLS 有两个主要目的：加密连接流量和提供一种验证对等方是否可信的方法（例如由受信任的证书颁发机构签名），以防范中间人攻击。中间人攻击是一类攻击者冒充合法的受信任对等方（通常是服务器）的攻击。本节将重点介绍后者。

### 对等方验证的工作原理

建立 TLS 连接时，客户端和服务器会执行几个步骤的连接协商。第一步是对等方 _选择性地_ 交换其证书。交换证书后，对等方可以 _选择性地_ 尝试在其 CA 证书和提供的证书之间建立信任链。这旨在验证对等方是否确实是其所声称的那个人（前提是私钥未被盗）。

此过程称为对等方验证，并遵循称为证书路径验证算法的算法。了解整个算法对于使用对等方验证不是必需的，因此本节对关键部分进行了过度简化的解释。

每个对等方提供一个 _证书链_ ，该链以“叶子”（客户端或服务器）证书开始，并至少包含一个证书颁发机构 (CA) 证书。该 CA 签发（签署）了该叶子 CA。如果有多个 CA 证书，它们通常形成一个签名链，这意味着每个 CA 证书都由下一个 CA 证书签名。例如，如果证书 B 由 A 签名，而 C 由 B 签名，则链为 `A, B, C`（此处使用逗号是为了清晰起见）。“最顶层”（第一个或唯一的）CA 通常被称为该链的 _根 CA_ 。根 CA 可以由知名的证书颁发机构（商业供应商）或任何其他方（自签名）颁发。

这是一个包含一个根 CA 和一个叶子（服务器或客户端）证书的最基本链的示例：

带有中间证书的链可能如下所示：

在对等方验证 TLS 连接期间，客户端（或服务器）会遍历对等方提供的证书链，如果找到受信任的证书，则认为对等方是受信任的。

### 双向对等方验证（双向 TLS 身份验证或 mTLS）

当双方执行此对等方验证过程时，这称为 _双向 TLS 身份验证_ 或 _mTLS_ 。

启用双向对等方验证涉及两件事：

  * 在 RabbitMQ 端启用客户端连接的对等方验证。
  * 在应用程序代码中启用服务器的对等方验证。



换句话说，双向对等方验证（“mTLS”）是 RabbitMQ 节点和客户端连接的共同责任。仅在一端启用对等方验证是不够的。

### 当对等方验证失败时

如果未找到受信任且有效的证书，则对等方验证失败，客户端的 TLS (TCP) 连接将因致命错误（OpenSSL 术语中的“警报”）而关闭，提示“Unknown CA”或类似信息。该警报将由服务器记录，并显示类似于以下的消息：
    
    
    2018-09-10 18:10:46.502 [info] <0.902.0< TLS server generated SERVER ALERT: Fatal - Unknown CA  
    

证书有效性也会在每一步进行检查。已过期或尚未生效的证书将被拒绝。在这种情况下，TLS 警报看起来像这样：
    
    
    2018-09-10 18:11:05.168 [info] <0.923.0< TLS server generated SERVER ALERT: Fatal - Certificate Expired  
    

上面的示例演示了 RabbitMQ 节点记录的 TLS 警报消息。执行对等方验证的客户端也会引发警报，但可能会使用不同的错误消息。RFC 8446 第 6.2 节概述了各种警报及其含义。

### 受信任证书

每个支持 TLS 的工具和 TLS 实现，包括 Erlang/OTP 和 RabbitMQ，都有标记一组证书为受信任的方法。

对此有三种常见方法：

  * 所有受信任的 CA 证书必须添加到一个称为 _CA 证书捆绑包_ 的单个文件中。
  * 目录中的所有 CA 证书都被视为受信任的。
  * 使用专用工具来管理受信任的 CA 证书。



不同的 TLS 实现和工具使用不同的选项。在 RabbitMQ 的上下文中，这意味着受信任证书的管理方法对于不同的客户端库、工具和 RabbitMQ 服务器本身可能不同。

例如，Linux 和其他类 UNIX 系统上的 OpenSSL 以及 OpenSSL 命令行工具（如 `s_client`）将使用由超级用户管理的目录。该目录中的 CA 证书将被视为受信任的，它们签发的证书（如客户端提供的证书）也是如此。受信任证书目录的位置在不同发行版、操作系统和版本之间会有所不同。

在 Windows 上，受信任证书使用 certmgr 等工具进行管理。

服务器 CA 证书捆绑包中的证书可能被视为受信任的。我们之所以说“可能”，是因为它并不适用于所有客户端库，因为这因 TLS 实现而异。例如，在 Python 中，除非显式添加到信任存储中，否则 CA 证书捆绑包中的证书将不会被视为受信任的。

RabbitMQ 依赖于 Erlang 的 TLS 实现。它假设**所有受信任的 CA 证书都已添加到服务器证书捆绑包中** 。

在执行对等方验证时，RabbitMQ 仅认为根证书（列表中的第一个证书）是受信任的。任何中间证书都将被忽略。如果希望中间证书也被视为受信任的，则必须将它们添加到受信任证书列表中：证书捆绑包。

虽然可以将最终（“叶子”）证书（例如服务器和客户端使用的证书）放入受信任证书目录，但更常见的做法是将 CA 证书添加到受信任证书列表中。

将多个证书附加到一起并用于单个证书颁发机构捆绑包文件的最常见方法是简单地将它们连接起来：
    
    
    cat rootca/ca_certificate.pem otherca/ca_certificate.pem > all_cacerts.pem  
    

### 启用对等方验证

在服务器端，对等方验证主要使用两个配置选项控制：`ssl_options.verify` 和 `ssl_options.fail_if_no_peer_cert`。

将 `ssl_options.fail_if_no_peer_cert` 选项设置为 `false` 会告知节点接受不提供证书（例如，未配置使用证书）的客户端。

当 `ssl_options.verify` 选项设置为 `verify_peer` 时，如果客户端确实向我们发送了证书，节点必须执行对等方验证。当设置为 `verify_none` 时，对等方验证将被禁用，并且不会执行证书交换。

例如，以下配置将执行对等方验证并拒绝不提供证书的客户端：
    
    
    listeners.ssl.default = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile = /path/to/server_key.pem  
    
    
    ssl_options.verify = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = true  
    

使用经典配置格式的相同示例：
    
    
    [  
    
    
    {rabbit, [  
    
    
       {ssl_listeners, [5671]},  
    
    
       {ssl_options, [{cacertfile,"/path/to/ca_certificate.pem"},  
    
    
                      {certfile,"/path/to/server_certificate.pem"},  
    
    
                      {keyfile,"/path/to/server_key.pem"},  
    
    
                      {verify, verify_peer},  
    
    
                      {fail_if_no_peer_cert, true}]}  
    
    
     ]}  
    
    
    ].  
    

在客户端库中精确配置对等方验证的方式因库而异。Java 和 .NET 客户端部分涵盖了这些客户端中的对等方验证。

强烈建议在生产环境中进行对等方验证。经过仔细考虑，在某些环境（例如开发环境）中禁用它可能是合理的。

因此，可以创建加密的 TLS 连接 _而无需_ 验证证书。客户端库通常支持这两种操作模式。

启用对等方验证后，客户端通常还会检查它们所连接服务器的主机名是否与服务器证书中的两个字段之一匹配：SAN (Subject Alternative Name) 或 CN (Common Name)。当使用通配符证书时，主机名将根据模式进行匹配。如果不匹配，客户端也会使对等方验证失败。主机名检查也是可选的，通常与客户端执行的证书链验证正交。

因此，了解生成证书时使用了什么 SAN (Subject Alternative Name) 或 CN (Common Name) 值非常重要。如果证书是在一台主机上生成并在另一台主机上使用的，则应将 `$(hostname)` 值替换为目标服务器的正确主机名。

tls-gen 将对这两个值使用本地机器的主机名。同样，在手动证书/密钥对生成部分中，本地机器的主机名被指定为 `...-subj /CN=$(hostname)/...` 用于某些 OpenSSL CLI 工具命令。

### 证书链和验证深度

当使用由中间 CA 签名的客户端证书时，可能需要将 RabbitMQ 服务器配置为使用更高的验证深度。

深度是有效认证路径中对等证书之后可能跟随的非自签发中间证书的最大数量。因此，如果深度为 0，则对等（例如客户端）证书必须由受信任的 CA 直接签名；如果深度为 1，则路径可以是“对等，CA，受信任 CA”；如果深度为 2，则是“对等，CA，CA，受信任 CA”，依此类推。默认深度为 1。

以下示例演示了如何配置 RabbitMQ 服务器的证书验证深度：
    
    
    listeners.ssl.default = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile = /path/to/server_key.pem  
    
    
    ssl_options.verify = verify_peer  
    
    
    ssl_options.depth  = 2  
    
    
    ssl_options.fail_if_no_peer_cert = false  
    

使用经典配置格式的相同示例：
    
    
    [  
    
    
      {rabbit, [  
    
    
         {ssl_listeners, [5671]},  
    
    
         {ssl_options, [{cacertfile,"/path/to/ca_certificate.pem"},  
    
    
                        {certfile,"/path/to/server_certificate.pem"},  
    
    
                        {keyfile,"/path/to/server_key.pem"},  
    
    
                        {depth, 2},  
    
    
                        {verify,verify_peer},  
    
    
                        {fail_if_no_peer_cert,false}]}  
    
    
       ]}  
    
    
    ].  
    

当将 RabbitMQ 插件（如 Federation 或 Shovel）与 TLS 一起使用时，可能需要为这些插件在底层使用的 Erlang 客户端配置验证深度，如下文所述。

## 在 Java 客户端中使用 TLS

在 RabbitMQ Java 客户端中启用 TLS 主要有两部分：设置密钥存储（包括一些 Java 安全框架细节）以及实现所需的对等方验证策略。

### 密钥管理器、信任管理器和存储

Java 安全框架中有三个主要组件：密钥管理器 (Key Manager)、信任管理器 (Trust Manager) 和 密钥存储 (Key Store)。

密钥管理器由对等方（在本例中为客户端连接）用来管理其证书。在 TLS 连接/会话协商期间，密钥管理器将控制要发送到远程对等方的证书。

信任管理器由对等方用来管理远程证书。在 TLS 连接/会话协商期间，信任管理器将控制远程对等方的哪些证书是受信任的。信任管理器可用于实现任何证书链验证逻辑。

密钥存储是 Java 对证书存储概念的封装。所有证书必须存储在 Java 特定的二进制格式 (JKS) 中或 PKCS#12 格式中。这些格式使用 `KeyStore` 类进行管理。在以下示例中，JKS 格式用于将受信任的（服务器）证书添加到存储中，而对于客户端密钥/证书对，将使用 tls-gen 生成的 PKCS#12 密钥文件。

Java 客户端中的所有 TLS 相关设置均通过 ConnectionFactory 进行配置。

### 使用 TLS 连接

这个非常基本的示例将展示一个简单的客户端如何通过 TLS 连接到 RabbitMQ 服务器，而不验证服务器证书，也不向服务器提供任何客户端证书。
    
    
    import java.io.*;  
    
    
    import java.security.*;  
    
    
      
    
    
    import com.rabbitmq.client.*;  
    
    
      
    
    
    public class Example1 {  
    
    
      
    
    
        public static void main(String[] args) throws Exception {  
    
    
            ConnectionFactory factory = new ConnectionFactory();  
    
    
            factory.setHost("localhost");  
    
    
            factory.setPort(5671);  
    
    
      
    
    
            factory.useSslProtocol();  
    
    
            // Tells the library to setup the default Key and Trust managers for you  
    
    
            // which do not do any form of remote server trust verification  
    
    
      
    
    
            Connection conn = factory.newConnection();  
    
    
            Channel channel = conn.createChannel();  
    
    
      
    
    
            // non-durable, exclusive, auto-delete queue  
    
    
            channel.queueDeclare("rabbitmq-java-test", false, true, true, null);  
    
    
            channel.basicPublish("", "rabbitmq-java-test", null, "Hello, World".getBytes());  
    
    
      
    
    
            GetResponse chResponse = channel.basicGet("rabbitmq-java-test", false);  
    
    
            if (chResponse == null) {  
    
    
                System.out.println("No message retrieved");  
    
    
            } else {  
    
    
                byte[] body = chResponse.getBody();  
    
    
                System.out.println("Received: " + new String(body));  
    
    
            }  
    
    
      
    
    
            channel.close();  
    
    
            conn.close();  
    
    
        }  
    
    
    }  
    

这个简单的示例是一个回显客户端和服务器。它创建一个通道并发布到默认的直连交换机，然后获取已发布的内容并将其回显出来。它使用一个独占的、非持久的、自动删除的队列，该队列将在连接关闭后不久被删除。

### 启用对等方验证后连接

为了让 Java 客户端信任服务器，服务器证书必须添加到将用于实例化 信任管理器 的信任存储中。JDK 附带了一个名为 `keytool` 的工具，用于管理证书存储。要将证书导入存储，请使用 `keytool -import`：
    
    
    keytool -import -alias server1 -file /path/to/server_certificate.pem -keystore /path/to/rabbitstore  
    

上述命令将使用 JKS 格式将 `server/certificate.pem` 导入到 `rabbitstore` 文件中。证书在信任存储中将被引用为 `server1`。所有证书和密钥在存储中必须具有唯一的名称。

`keytool` 将确认证书是受信任的，并要求输入密码。该密码保护信任存储免受任何篡改尝试。

然后使用 `PKCS#12` 文件中的客户端证书和密钥。请注意，Java 原生理解 `PKCS#12` 格式，无需转换。

以下示例演示了密钥存储和信任存储如何分别与密钥管理器和信任管理器一起使用。
    
    
    import java.io.*;  
    
    
    import java.security.*;  
    
    
    import javax.net.ssl.*;  
    
    
      
    
    
    import com.rabbitmq.client.*;  
    
    
      
    
    
    public class Example2 {  
    
    
      
    
    
        public static void main(String[] args) throws Exception {  
    
    
          char[] keyPassphrase = "MySecretPassword".toCharArray();  
    
    
          KeyStore ks = KeyStore.getInstance("PKCS12");  
    
    
          ks.load(new FileInputStream("/path/to/client_key.p12"), keyPassphrase);  
    
    
      
    
    
          KeyManagerFactory kmf = KeyManagerFactory.getInstance("SunX509");  
    
    
          kmf.init(ks, keyPassphrase);  
    
    
      
    
    
          char[] trustPassphrase = "rabbitstore".toCharArray();  
    
    
          KeyStore tks = KeyStore.getInstance("JKS");  
    
    
          tks.load(new FileInputStream("/path/to/trustStore"), trustPassphrase);  
    
    
      
    
    
          TrustManagerFactory tmf = TrustManagerFactory.getInstance("SunX509");  
    
    
          tmf.init(tks);  
    
    
      
    
    
          SSLContext c = SSLContext.getInstance("TLSv1.2");  
    
    
          c.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);  
    
    
      
    
    
          ConnectionFactory factory = new ConnectionFactory();  
    
    
          factory.setHost("localhost");  
    
    
          factory.setPort(5671);  
    
    
          factory.useSslProtocol(c);  
    
    
          factory.enableHostnameVerification();  
    
    
      
    
    
          Connection conn = factory.newConnection();  
    
    
          Channel channel = conn.createChannel();  
    
    
      
    
    
          channel.queueDeclare("rabbitmq-java-test", false, true, true, null);  
    
    
          channel.basicPublish("", "rabbitmq-java-test", null, "Hello, World".getBytes());  
    
    
      
    
    
          GetResponse chResponse = channel.basicGet("rabbitmq-java-test", false);  
    
    
          if (chResponse == null) {  
    
    
              System.out.println("No message retrieved");  
    
    
          } else {  
    
    
              byte[] body = chResponse.getBody();  
    
    
              System.out.println("Received: " + new String(body));  
    
    
          }  
    
    
      
    
    
          channel.close();  
    
    
          conn.close();  
    
    
      }  
    
    
    }  
    

为了确保上述代码在不受信任的证书下按预期工作，请使用未导入到密钥存储中的证书设置 RabbitMQ 节点，并观察连接失败。

#### 服务器主机名验证

必须使用 `ConnectionFactory#enableHostnameVerification()` 方法单独启用主机名验证。例如，在上面的示例中就是这样做的：
    
    
    import java.io.*;  
    
    
    import java.security.*;  
    
    
    import javax.net.ssl.*;  
    
    
      
    
    
    import com.rabbitmq.client.*;  
    
    
      
    
    
    public class Example2 {  
    
    
      
    
    
        public static void main(String[] args) throws Exception {  
    
    
          char[] keyPassphrase = "MySecretPassword".toCharArray();  
    
    
          KeyStore ks = KeyStore.getInstance("PKCS12");  
    
    
          ks.load(new FileInputStream("/path/to/client_key.p12"), keyPassphrase);  
    
    
      
    
    
          KeyManagerFactory kmf = KeyManagerFactory.getInstance("SunX509");  
    
    
          kmf.init(ks, keyPassphrase);  
    
    
      
    
    
          char[] trustPassphrase = "rabbitstore".toCharArray();  
    
    
          KeyStore tks = KeyStore.getInstance("JKS");  
    
    
          tks.load(new FileInputStream("/path/to/trustStore"), trustPassphrase);  
    
    
      
    
    
          TrustManagerFactory tmf = TrustManagerFactory.getInstance("SunX509");  
    
    
          tmf.init(tks);  
    
    
      
    
    
          SSLContext c = SSLContext.getInstance("TLSv1.2");  
    
    
          c.init(kmf.getKeyManagers(), tmf.getTrustManagers(), null);  
    
    
      
    
    
          ConnectionFactory factory = new ConnectionFactory();  
    
    
          factory.setHost("localhost");  
    
    
          factory.setPort(5671);  
    
    
          factory.useSslProtocol(c);  
    
    
          factory.enableHostnameVerification();  
    
    
      
    
    
          // this connection will both perform peer verification  
    
    
          // and server hostname verification  
    
    
          Connection conn = factory.newConnection();  
    
    
      
    
    
          // snip ...  
    
    
      }  
    
    
    }  
    

这将验证服务器证书是否是为客户端连接到的主机名颁发的。与证书链验证不同，此功能是特定于客户端的（通常不由服务器执行）。

### 在 Java 客户端中配置 TLS 版本

正如 RabbitMQ 服务器可以配置为仅支持特定的 TLS 版本一样，在 Java 客户端中配置首选 TLS 版本也是必要的。这是通过 `ConnectionFactory#useSslProtocol` 的重载来实现的，它接受协议版本名称或 `SSLContext`：
    
    
    ConnectionFactory factory = new ConnectionFactory();  
    
    
    factory.setHost("localhost");  
    
    
    factory.setPort(5671);  
    
    
      
    
    
    factory.useSslProtocol("TLSv1.2");  
    

该库的现代版本将尝试使用运行时支持的最新 TLS 版本。

## 在 .NET 客户端中使用 TLS

为了使客户端证书在 .NET 平台上被识别，它们可以采用多种格式，包括 DER 和 PKCS#12，但不包括 PEM。对于 DER 格式，.NET 期望它们存储在扩展名为 `.cer` 的文件中。tls-gen 同时生成 PEM 和 PKCS#12 文件。

### .NET 信任存储

在 .NET 平台上，受信任的证书是通过将它们放入多个存储中的任何一个来管理的。所有这些存储的管理都是通过“certmgr”工具完成的。

注意：在某些版本的 Windows 上，该命令有两个版本：一个随操作系统附带并仅提供图形界面，另一个随 Windows SDK 附带并提供图形和命令行界面。两者都可以完成工作，但以下示例基于后者。

对于我们的情况，因为我们在单独的 PKCS#12 文件中提供客户端证书/密钥对，所以我们只需要将根证书颁发机构的证书导入到 Root（Windows）或 Trust（Mono）存储中即可。任何由该存储中的任何证书签名的证书都会自动被信任。

与乐于在不执行对等方验证的情况下使用 TLS 连接的 Java 客户端相比，.NET 客户端默认要求此验证成功。要禁止验证，应用程序可以在 SslOption 中设置 `System.Net.Security.SslPolicyErrors.RemoteCertificateNotAvailable` 和 `System.Net.Security.SslPolicyErrors.RemoteCertificateChainErrors` 标志。

### 使用 Certmgr 进行证书管理

`certmgr` 是一个命令行工具，用于管理指定存储中的证书，例如添加和删除它们。这些存储可以是用户存储或系统级存储。只有管理用户才能对系统级存储拥有写访问权限。

以下示例将证书添加到用户 `Root`（在某些 .NET 实现中也称为 `Trust`）的存储中：
    
    
    # Windows  
    
    
    certmgr -add -all \path\to\cacert.cer -s Root  
    
    
    
    # Linux with Mono  
    
    
    certmgr -add -c Trust /path/to/cacert.cer  
    

要将证书添加到系统级（机器）证书存储中，请运行：
    
    
    # Windows  
    
    
    certmgr -add -all \path\to\cacert.cer -s -r localMachine Root  
    
    
    
    # Linux with Mono  
    
    
    certmgr -add -c -m Trust /path/to/cacert.cer  
    

添加到存储后，我们可以使用 `-all`（在 Mono 中为 `-list`）开关查看该存储的内容：
    
    
    certmgr -all -s Root  
    
    
      
    
    
    # … snip …  
    
    
      
    
    
    Self-signed X.509 v3 Certificate  
    
    
      Serial Number: AC3F2B74ECDD9EEA00  
    
    
      Issuer Name:   CN=MyTestCA  
    
    
      Subject Name:  CN=MyTestCA  
    
    
      valid From:    25/08/2018 14:03:01  
    
    
      valid Until:   24/09/2018 14:03:01  
    
    
      Unique Hash:   1F04D1D2C20B97BDD5DB70B9EB2013550697A05E  
    
    
    
    certmgr -list -c Trust  
    
    
      
    
    
    # … snip …  
    
    
      
    
    
    Self-signed X.509 v3 Certificate  
    
    
      Serial Number: AC3F2B74ECDD9EEA00  
    
    
      Issuer Name:   CN=MyTestCA  
    
    
      Subject Name:  CN=MyTestCA  
    
    
      valid From:    25/08/2018 14:03:01  
    
    
      valid Until:   24/09/2018 14:03:01  
    
    
      Unique Hash:   1F04D1D2C20B97BDD5DB70B9EB2013550697A05E  
    

根据上面的输出，信任存储中有一个自签名的 X.509 v3 证书。唯一哈希唯一标识了该存储中的此证书。要删除此证书，请使用唯一哈希：
    
    
    # Windows  
    
    
    certmgr -del -c -sha1 1F04D1D2C20B97BDD5DB70B9EB2013550697A05E -s Root  
    
    
      
    
    
    # … snip …  
    
    
      
    
    
    Certificate removed from store.  
    
    
    
    # Linux with Mono  
    
    
    certmgr -del -c Trust 1F04D1D2C20B97BDD5DB70B9EB2013550697A05E  
    
    
      
    
    
    # … snip …  
    
    
      
    
    
    Certificate removed from store.  
    

### 连接 TLS 设置

要创建启用 TLS 的 RabbitMQ 连接，我们需要在 ConnectionFactory 的 Parameters 字段中设置一些新字段。为了简化操作，有一个新的字段 Parameters.Ssl，它充当我们需要设置的所有其他字段的命名空间。这些字段是：

属性| 描述  
---|---  
`Ssl.CertPath`| 如果您的服务器期望客户端验证，这是 PKCS#12 格式的客户端证书路径。这是可选的。  
`Ssl.CertPassphrase`| 如果您使用的是 PKCS#12 格式的客户端证书，那么它很可能有一个密码，您可以在此字段中指定该密码。  
`Ssl.Enabled`| 这是一个布尔字段，用于开启或关闭 TLS 支持。默认情况下它是关闭的。  
`Ssl.ServerName`| .NET 期望此值与服务器发送的证书上的主题备用名称 (SAN) 或通用名称 (CN) 匹配。  
  
### TLS 版本

TLS 自 90 年代中期以来一直存在，并且有多个 TLS 版本可用，尽管随着更新、更安全版本的开发，旧版本已被行业淘汰。

正如 RabbitMQ 服务器可以配置为仅支持特定的 TLS 版本一样，在 .NET 客户端中配置首选 TLS 版本也是必要的。这是通过 `ConnectionFactory#Ssl` 访问的 TLS 选项完成的。

支持的 TLS 版本值是 System.Security.Authentication.SslProtocols 枚举 中的那些值。
    
    
    using System.Security.Authentication;  
    
    
      
    
    
    // ...  
    
    
      
    
    
    ConnectionFactory cf = new ConnectionFactory();  
    
    
      
    
    
    cf.Ssl.Enabled = true;  
    
    
    cf.Ssl.ServerName = System.Net.Dns.GetHostName();  
    
    
    cf.Ssl.CertPath = "/path/to/client_key.p12";  
    
    
    cf.Ssl.CertPassphrase = "MySecretPassword";  
    
    
      
    
    
    // Use TLSv1.2 for this connection  
    
    
    cf.Ssl.Version = SslProtocols.Tls12;  
    

RabbitMQ .NET 客户端 5.x 系列默认使用 TLSv1.0。

从 RabbitMQ .NET 客户端 6.0 开始，默认值更改为 `SslProtocols.None`，这意味着默认值由 .NET 框架或操作系统根据应用上下文切换来选择。

如果使用 `SslProtocols.None` 选择合适的 TLS 版本的连接失败，客户端将通过显式启用 TLSv1.2 进行重试。这减少了在禁用、不可用或无法依赖自动 TLS 版本选择的环境中，对应用程序开发人员进行显式配置的需求。

现代 .NET 框架版本默认使用 TLSv1.2。

### 代码示例

这是Java 客户端示例的一个或多或少的直接移植。它创建一个通道并发布到默认的直连交换机，然后读取已发布的内容并将其回显出来。请注意，我们使用了一个独占的、非持久的、自动删除的队列，这样我们就无需担心手动进行清理。
    
    
    using System;  
    
    
    using System.IO;  
    
    
    using System.Text;  
    
    
      
    
    
    using RabbitMQ.client;  
    
    
      
    
    
    namespace RabbitMQ.client.Examples  
    
    
    {  
    
    
      public class TestSSL  
    
    
      {  
    
    
        public static async Task<int> Main(string[] args)  
    
    
        {  
    
    
          ConnectionFactory cf = new ConnectionFactory();  
    
    
      
    
    
          cf.Ssl.Enabled = true;  
    
    
          cf.Ssl.ServerName = System.Net.Dns.GetHostName();  
    
    
          cf.Ssl.CertPath = "/path/to/client_key.p12";  
    
    
          cf.Ssl.CertPassphrase = "MySecretPassword";  
    
    
      
    
    
          using (IConnection conn = await cf.CreateConnectionAsync())  
    
    
          {  
    
    
            using (IChannel ch = await conn.CreateChannelAsync())  
    
    
            {  
    
    
              Console.WriteLine("Successfully connected and opened a channel");  
    
    
              await ch.QueueDeclareAsync("rabbitmq-dotnet-test", false, false, false, null);  
    
    
              Console.WriteLine("Successfully declared a queue");  
    
    
              await ch.QueueDeleteAsync("rabbitmq-dotnet-test");  
    
    
              Console.WriteLine("Successfully deleted the queue");  
    
    
            }  
    
    
          }  
    
    
          return 0;  
    
    
        }  
    
    
      }  
    
    
    }  
    

### 在 .NET 客户端中进行 TLS 对等方验证

TLS 提供对等方验证（验证），这是一种客户端和服务器根据对等方的证书信息验证彼此身份的方法。启用对等方验证后，通常您所连接服务器的 _主机名_ 需要与服务器证书上的 _CN (Common Name)_ 字段匹配，否则证书将被拒绝。但是，对等方验证通常不必仅限于 CN 和主机名匹配。

这就是本指南开头的命令指定 `...-subj /CN=$(hostname)/...` 的原因，该命令会动态查找您的主机名。如果您在一台机器上生成证书并在另一台机器上使用它们，请务必交换 `$(hostname)` 部分，并将其替换为您服务器的正确主机名。

在 .NET 平台上，RemoteCertificateValidationCallback 控制 TLS 验证行为。

在 RabbitMQ .NET 客户端中，`RabbitMQ.client.SslOption.CertificatevalidationCallback` 可用于提供一个 RemoteCertificateValidationCallback 委托。该委托将用于使用适合应用程序的任何逻辑来验证对等方（RabbitMQ 节点）的身份。

如果未指定此项，默认的回调将与 AcceptablePolicyErrors 属性结合使用，以确定远程服务器证书是否有效。

`RabbitMQ.client.SslOption.AcceptablePolicyErrors` 中的 `System.Net.Security.SslPolicyErrors.RemoteCertificateNameMismatch` 标志可用于禁用对等方验证（在生产环境中不建议这样做！）。

`RabbitMQ.client.SslOption.CertificateSelectionCallback` 可用于提供一个 LocalCertificateSelectionCallback，它将选择用于对等方验证的本地证书。

## 限制服务器使用的 TLS 版本

### 为什么要限制 TLS 版本

TLS（前身为 SSL）随着时间的推移而发展，并有多个版本在使用。每个版本都建立在以前版本的不足之处之上。大多数情况下，这些不足之处会导致已知的攻击，这些攻击会影响特定版本的 TLS（和 SSL）。禁用较旧的 TLS 版本是缓解这些攻击的一种方法（另一种技术是禁用受影响的密码套件）。

由于上述原因，最近的 Erlang 发行系列默认仅启用最新的受支持 TLS 版本，如下表所示：

**Erlang 系列**| **默认启用的 TLS 版本**  
---|---  
27.x| TLSv1.3 和 TLSv1.2  
26.x| TLSv1.3 和 TLSv1.2  
  
鼓励较旧的受支持 Erlang 版本的用户尽可能仅将支持的 TLS 版本限制为 1.2 及更高版本。请认为 TLSv1.0 和 TLSv1.1 **已被行业弃用** 。

### 为什么不限制 TLS 版本

将 TLS 版本限制为仅 TLSv1.3 甚至仅 TLSv1.2 意味着仅支持较旧 TLS 版本的客户端将无法连接。

如果对使用此类旧运行时的应用程序的支持很重要，则必须将服务器配置为支持较旧的 TLS 版本。在大多数情况下，支持 TLSv1.2 应该就足够了。

要限制启用的 TLS 协议版本，请使用 `ssl_options.versions` 设置。

下面的示例仅接受 TLSv1.3（最新且最安全的版本），并要求节点运行在针对非常新的 OpenSSL 编译的 Erlang 26 上。使用没有 TLSv1.3 支持的较旧运行时（例如 JDK、.NET、Python）的客户端**将无法在此设置下连接** 。
    
    
    listeners.ssl.1 = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
      
    
    
    ssl_options.versions.1 = tlsv1.3  
    
    
      
    
    
    # Limits enable cipher suites to only those used by TLSv1.3.  
    
    
    # There are no cipher suites supported by both TLSv1.3 and TLSv1.2.  
    
    
    ssl_options.ciphers.1  = TLS_AES_256_GCM_SHA384  
    
    
    ssl_options.ciphers.2  = TLS_AES_128_GCM_SHA256  
    
    
    ssl_options.ciphers.3  = TLS_CHACHA20_POLY1305_SHA256  
    
    
    ssl_options.ciphers.4  = TLS_AES_128_CCM_SHA256  
    
    
    ssl_options.ciphers.5  = TLS_AES_128_CCM_8_SHA256  
    

下面的示例禁用早于 TLSv1.2 的版本：
    
    
    listeners.ssl.1 = 5671  
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
      
    
    
    ssl_options.versions.1 = tlsv1.2  
    

### 验证启用的 TLS 版本

要验证所提供的 TLS 版本，请使用带有适当 TLS 版本标志的 `openssl s_client`：
    
    
    # connect using TLSv1.3  
    
    
    openssl s_client -connect 127.0.0.1:5671 -tls1_3  
    

并在输出中查找以下内容：
    
    
    New, TLSv1.3, Cipher is TLS_AES_256_GCM_SHA384  
    

在下面的示例中，使用了 TLSv1.2：
    
    
    # connect using TLSv1.2  
    
    
    openssl s_client -connect 127.0.0.1:5671 -tls1_2  
    

输出中的协议和协商的密码套件如下所示：
    
    
    SSL-Session:  
    
    
        Protocol  : TLSv1.2  
    
    
        Cipher    : ECDHE-RSA-AES256-GCM-SHA384  
    

### TLSv1.3

重要

TLS 1.3 是统称为“TLS”的标准套件的重大修订。它有意破坏了与所有早期版本的向后兼容性。

虽然大多数流行编程语言和运行时的现代版本都已经支持 TLS 1.3 好几年了，但采用此版本需要进行规划，并应被视为一项会影响使用 TLS 的应用程序的更改。

如果某些应用程序或其运行时无法轻易升级以使用此新版本，则在 RabbitMQ 端采用 TLS 1.3 可能会成为一个不可行的选择。

TLSv1.3 是对 TLS 协议的重大修订。它是最新且最安全的选项。

TLSv1.3 支持要求节点运行在 Erlang 27 或 26 上，并针对非常新的 OpenSSL 进行编译。

使用没有 TLSv1.3 支持的较旧运行时（例如 JDK、.NET、Python）的客户端**将无法连接** 到配置为仅接受 TLSv1.3 连接的 RabbitMQ 节点。

由于 TLSv1.3 与早期的 TLS 版本没有任何共享的密码套件，因此在启用 TLSv1.3 时，请列出一组 TLSv1.3 特定的密码套件：
    
    
    listeners.ssl.1 = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
      
    
    
    ssl_options.versions.1 = tlsv1.3  
    
    
      
    
    
    # Limits enable cipher suites to only those used by TLSv1.3.  
    
    
    # There are no cipher suites supported by both TLSv1.3 and TLSv1.2.  
    
    
    ssl_options.ciphers.1  = TLS_AES_256_GCM_SHA384  
    
    
    ssl_options.ciphers.2  = TLS_AES_128_GCM_SHA256  
    
    
    ssl_options.ciphers.3  = TLS_CHACHA20_POLY1305_SHA256  
    
    
    ssl_options.ciphers.4  = TLS_AES_128_CCM_SHA256  
    
    
    ssl_options.ciphers.5  = TLS_AES_128_CCM_8_SHA256  
    

在客户端侧也可能需要进行显式的密码套件配置。

要验证所提供的 TLS 版本，请如上所述使用 `openssl s_client`。

### JDK 和 .NET 的 TLS 版本支持表

禁用 TLSv1.0 会限制支持的客户端平台数量。下表说明了 JDK 和 .NET 版本支持哪些 TLS 版本。

TLS 版本| 最低 JDK 版本| 最低 .NET 版本  
---|---|---  
TLS 1.3| JDK 8 从 JDK8u261 开始，JDK 11+| .NET 4.7，在支持 TLSv1.3 的 Windows 版本上  
TLS 1.2| JDK 7（参见 协议，推荐 JDK 8）| .NET 4.5  
TLS 1.1| JDK 7（参见 协议，推荐 JDK 8）| .NET 4.5  
  
Oracle JDK 有一个关于加密及相关标准的公开路线图，其中概述了某些密码套件或 TLS 版本何时会被弃用或删除。

## 公共扩展密钥用法选项 (EKUs)

公钥（证书）有许多字段描述了密钥的预期使用场景。这些字段限制了各种工具允许使用密钥的方式。例如，公钥可用于验证证书签名（充当证书颁发机构密钥）。

这些字段还会影响 RabbitMQ 节点和客户端在连接协商（更具体地说是 TLS 握手）期间将使用的密码套件，因此解释它们的影响非常重要。

本指南将以一些刻意的过度简化来涵盖它们。从广义上讲，这些字段分为三类：

  * keyUsage
  * Basic Constraints
  * extendedKeyUsage



有些字段是布尔值，有些是其他类型，例如可以设置或取消设置的选项（位）集。

数据服务在很大程度上与所使用的约束和密钥用法选项无关。但是，有些对于本指南中描述的用例是必不可少的。

对于服务器，它们是：

  * `TLS Server Authentication` (又名 `id-kp-serverAuth`，向客户端提供 RabbitMQ 节点的身份)
  * `Digital Signature` (数字签名验证)
  * `Key Encipherment`



对于客户端，它们是：

  * `TLS Client Authentication` (又名 `id-kp-clientAuth`，向 RabbitMQ 节点、代理提供客户端的身份)
  * `Digital Signature` (数字签名验证)
  * `Key Encipherment`



具体来说，`TLS Server Authentication` 和 `TLS Client Authentication` 用于对等方验证。它们必须在生成公钥时分别为服务器和客户端证书设置。

提示

在大多数情况下，应仅设置其中一个 `Authentication` EKU：RabbitMQ 节点使用的证书应设置 `TLS Server Authentication`，客户端（应用程序）使用的证书应设置 `TLS Client Authentication`。

在单个证书上同时设置两者不再被认为是良好的（安全的）行业惯例。

  * 源一
  * 源二
  * 源三
  * 源四



tls-gen 将确保这些约束和扩展被正确设置。当手动生成证书时，这是生成密钥对的操作员或密钥对提供程序的责任。

### 扩展及其对接受的密码套件的影响（密码套件过滤）

两个关键扩展对于两类主要的密码套件至关重要：

  * `digitalSignature`，用于基于 ECC（椭圆曲线加密）的套件
  * `keyEncipherment`，用于基于 RSA 的套件



强烈建议为 RabbitMQ 节点和客户端库使用的证书设置上述两个选项（位）。如果未设置这些位，TLS 实现将排除掉一整类密码套件，这可能会导致在连接时出现令人困惑的“未找到合适的密码套件”警报（错误消息）。

### 检查证书扩展

要查看为公钥设置了哪些约束和扩展，请使用 `openssl x509` 命令：
    
    
    openssl x509 -in /path/to/certificate.pem -text -noout  
    

其输出将包含一个嵌套的扩展和约束列表，类似于这样（这是一个客户端证书示例）：
    
    
    X509v3 extensions:  
    
    
        X509v3 Basic Constraints:  
    
    
            CA:FALSE  
    
    
        X509v3 Key Usage:  
    
    
            Digital Signature, Key Encipherment  
    
    
        X509v3 Extended Key Usage:  
    
    
            TLS Web Client Authentication  
    

上述扩展集表明，这是一个可用于对客户端进行身份验证（向 RabbitMQ 节点提供客户端身份）的公钥，不能用作证书颁发机构证书，并可用于密钥加密和数字签名。

就本指南而言，这是一个适合用于客户端连接的证书（公钥）。

以下是一个适合用于服务器身份验证的证书（公钥）示例（向客户端提供 RabbitMQ 节点的身份）：
    
    
    X509v3 extensions:  
    
    
        X509v3 Basic Constraints:  
    
    
            CA:FALSE  
    
    
        X509v3 Key Usage:  
    
    
            Digital Signature, Key Encipherment  
    
    
        X509v3 Extended Key Usage:  
    
    
            TLS Web Server Authentication  
    

## 密码套件

可以配置 RabbitMQ 将使用的密码套件。请注意，并非所有套件在所有系统上都可用。例如，要使用椭圆曲线密码，必须使用最近的受支持 Erlang 版本。

RabbitMQ 节点和客户端使用的密码套件也可以通过公钥用法字段及其值进行有效限制。在继续进行密码套件配置之前，确保这些密钥用法选项是可以接受的非常重要。

### 列出 RabbitMQ 节点上可用的密码套件

要列出正在运行的节点的 Erlang 运行时支持的密码套件，请使用 `rabbitmq-diagnostics cipher_suites --format openssl`
    
    
    rabbitmq-diagnostics cipher_suites --format openssl -q  
    

这将生成 OpenSSL 格式的密码套件列表。

请注意，如果您使用 `--format erlang`
    
    
    rabbitmq-diagnostics cipher_suites --format erlang -q  
    

那么 `rabbitmq-diagnostics cipher_suites` 将以仅在经典配置格式中接受的格式列出密码套件。OpenSSL 格式被两种配置格式接受。请注意，密码套件在新式配置格式中不加引号，但在经典格式中需要双引号。

上述命令列出的密码套件的格式可用于入站和出站（例如 Shovel、Federation）客户端 TLS 连接。它们与配置值加密所使用的不同。

覆盖密码套件时，强烈建议强制执行服务器首选的密码套件顺序。

### 配置密码套件

密码套件使用 `ssl_options.ciphers` 配置选项（在经典配置格式中为 `rabbit.ssl_options.ciphers`）进行配置。

下面的示例演示了该选项的使用方式：
    
    
    listeners.ssl.1 = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.versions.1 = tlsv1.2  
    
    
      
    
    
    ssl_options.verify = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = false  
    
    
      
    
    
    ssl_options.ciphers.1  = ECDHE-ECDSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.2  = ECDHE-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.3  = ECDH-ECDSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.4  = ECDH-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.5  = DHE-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.6  = DHE-DSS-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.7  = ECDHE-ECDSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.8  = ECDHE-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.9  = ECDH-ECDSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.10 = ECDH-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.11 = DHE-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.12 = DHE-DSS-AES128-GCM-SHA256  
    
    
      
    
    
    # these MUST be disabled if TLSv1.3 is used  
    
    
    ssl_options.honor_cipher_order = true  
    
    
    ssl_options.honor_ecc_order    = true  
    

在经典配置格式中：
    
    
    %% list allowed ciphers  
    
    
    [  
    
    
     {ssl, [{versions, ['tlsv1.2', 'tlsv1.1']}]},  
    
    
     {rabbit, [  
    
    
               {ssl_listeners, [5671]},  
    
    
               {ssl_options, [{cacertfile,"/path/to/ca_certificate.pem"},  
    
    
                              {certfile,  "/path/to/server_certificate.pem"},  
    
    
                              {keyfile,   "/path/to/server_key.pem"},  
    
    
                              {versions, ['tlsv1.2', 'tlsv1.1']},  
    
    
                              %% This list is just an example!  
    
    
                              %% Not all cipher suites are available on all machines.  
    
    
                              %% Cipher suite order is important: preferred suites  
    
    
                              %% should be listed first.  
    
    
                              %% Different suites have different security and CPU load characteristics.  
    
    
                              {ciphers,  [  
    
    
                                "ECDHE-ECDSA-AES256-GCM-SHA384",  
    
    
                                "ECDHE-RSA-AES256-GCM-SHA384",  
    
    
                                "ECDH-ECDSA-AES256-GCM-SHA384",  
    
    
                                "ECDH-RSA-AES256-GCM-SHA384",  
    
    
                                "DHE-RSA-AES256-GCM-SHA384",  
    
    
                                "DHE-DSS-AES256-GCM-SHA384",  
    
    
                                "ECDHE-ECDSA-AES128-GCM-SHA256",  
    
    
                                "ECDHE-RSA-AES128-GCM-SHA256",  
    
    
                                "ECDH-ECDSA-AES128-GCM-SHA256",  
    
    
                                "ECDH-RSA-AES128-GCM-SHA256",  
    
    
                                "DHE-RSA-AES128-GCM-SHA256",  
    
    
                                "DHE-DSS-AES128-GCM-SHA256"  
    
    
                                ]}  
    
    
                             ]}  
    
    
              ]}  
    
    
    ].  
    

### 密码套件顺序

在 TLS 连接协商期间，服务器和客户端协商将使用哪种密码套件。可以强制服务器的 TLS 实现指定其首选（密码套件顺序），以避免恶意客户端有意协商弱密码套件，从而为运行攻击做准备。为此，请将 `honor_cipher_order` 和 `honor_ecc_order` 设置为 `true`：
    
    
    listeners.ssl.1        = 5671  
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.versions.1 = tlsv1.2  
    
    
      
    
    
    ssl_options.honor_cipher_order = true  
    
    
    ssl_options.honor_ecc_order    = true  
    

或者，在经典配置格式中：
    
    
    %% Enforce server-provided cipher suite order (preference)  
    
    
    [  
    
    
     {ssl, [{versions, ['tlsv1.2', 'tlsv1.1']}]},  
    
    
     {rabbit, [  
    
    
               {ssl_listeners, [5671]},  
    
    
               {ssl_options, [{cacertfile, "/path/to/ca_certificate.pem"},  
    
    
                              {certfile,   "/path/to/server_certificate.pem"},  
    
    
                              {keyfile,    "/path/to/server_key.pem"},  
    
    
                              {versions,   ['tlsv1.2', 'tlsv1.1']},  
    
    
      
    
    
                              %% ...  
    
    
      
    
    
      
    
    
                              {honor_cipher_order,   true},  
    
    
                              {honor_ecc_order,      true},  
    
    
                             ]}  
    
    
              ]}  
    
    
    ].  
    

### 推荐的密码套件 (TLS 1.3)

请参阅关于 TLS 1.3 和 评估 TLS 设置安全性 的部分。

### 推荐的密码套件 (TLS 1.2)

请参阅 Mozilla 的 服务器端 TLS 安全性 建议和 评估 TLS 设置安全性。

## 已知的 TLS 漏洞及其缓解措施

### ROBOT

ROBOT 攻击会影响依赖于 RSA 密码套件并在 19.3.6.4 和 20.1.7 之前的 Erlang/OTP 版本上运行的 RabbitMQ 安装。要缓解该问题，请升级 Erlang/OTP 到补丁版本，并考虑限制支持的密码套件列表。

### POODLE

POODLE 是一种已知的 SSL/TLS 攻击，最初破坏了 SSLv3。从 3.4.0 版本开始，RabbitMQ 服务器拒绝接受 SSLv3 连接。2014 年 12 月，宣布了一种影响 TLSv1.0 的修改版 POODLE 攻击。因此，建议要么运行 Erlang 18.0 或更高版本，这消除了 TLS 1.0 实现对 POODLE 的漏洞，要么禁用 TLSv1.0 支持。

### BEAST

BEAST 攻击是影响 TLSv1.0 的已知漏洞。要缓解它，请禁用 TLSv1.0 支持。

## 评估 TLS 设置安全性

由于 TLS 有许多可配置参数，且由于历史原因其中一些参数具有次优的默认值，因此评估 TLS 设置安全性是一种推荐的做法。存在多种工具可以在启用 TLS 的服务器端点上执行各种测试，例如测试它是否容易受到 POODLE、BEAST 等已知攻击的影响。

### testssl.sh

testssl.sh 是一种成熟且功能广泛的 TLS 端点测试工具。它可以与不提供 HTTPS 的协议端点一起使用。

该工具执行许多测试（例如，在某些机器上，仅密码套件测试就运行超过 350 次），并且并非每个环境都需要通过每一项测试。例如，许多生产部署不使用 CRL（证书撤销列表）；大多数开发环境使用自签名证书，无需担心启用最优化的密码套件集，依此类推。

要运行 `testssl.sh`，请提供要测试的端点，格式为 `{hostname}:5671`：
    
    
    ./testssl.sh localhost:5671  
    

### 评估 TLS 1.3 设置

以下接受 TLSv1.3 连接的配置示例在 Erlang 26 上通过了关键的 `testssl.sh` 测试：
    
    
    listeners.ssl.1 = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
      
    
    
    ssl_options.versions.1 = tlsv1.3  
    
    
      
    
    
    ssl_options.verify               = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = true  
    
    
      
    
    
    ssl_options.ciphers.1  = TLS_AES_256_GCM_SHA384  
    
    
    ssl_options.ciphers.2  = TLS_AES_128_GCM_SHA256  
    
    
    ssl_options.ciphers.3  = TLS_CHACHA20_POLY1305_SHA256  
    
    
    ssl_options.ciphers.4  = TLS_AES_128_CCM_SHA256  
    
    
    ssl_options.ciphers.5  = TLS_AES_128_CCM_8_SHA256  
    
    
      
    
    
    ssl_options.honor_cipher_order   = true  
    
    
    ssl_options.honor_ecc_order      = true  
    

这种 TLSv1.3 独占设置被报告为没有漏洞。
    
    
      Using "OpenSSL 3.3.1 4 Jun 2024 (Library: OpenSSL 3.3.1 4 Jun 2024)" [~94 ciphers]  
    
    
     on [redacted]:/opt/homebrew/bin/openssl  
    
    
     (built: "Jun  4 12:53:04 2024", platform: "darwin64-arm64-cc")  
    
    
      
    
    
      
    
    
     Start 2024-08-08 11:56:02                -->> 127.0.0.1:5671 (localhost) <<--  
    
    
      
    
    
     A record via:           /etc/hosts  
    
    
     rDNS (127.0.0.1):       localhost.  
    
    
     Service detected:       Couldn't determine what's running on port 5671, assuming no HTTP service => skipping all HTTP checks  
    
    
      
    
    
      
    
    
     Testing protocols via sockets except NPN+ALPN  
    
    
      
    
    
     SSLv2      not offered (OK)  
    
    
     SSLv3      not offered (OK)  
    
    
     TLS 1      not offered  
    
    
     TLS 1.1    not offered  
    
    
     TLS 1.2    not offered  
    
    
     TLS 1.3    offered (OK): final  
    
    
     NPN/SPDY   not offered  
    
    
     ALPN/HTTP2 not offered  
    
    
      
    
    
     Testing cipher categories  
    
    
      
    
    
     NULL ciphers (no encryption)                      not offered (OK)  
    
    
     Anonymous NULL Ciphers (no authentication)        not offered (OK)  
    
    
     Export ciphers (w/o ADH+NULL)                     not offered (OK)  
    
    
     LOW: 64 Bit + DES, RC[2,4], MD5 (w/o export)      not offered (OK)  
    
    
     Triple DES Ciphers / IDEA                         not offered  
    
    
     Obsoleted CBC ciphers (AES, ARIA etc.)            not offered  
    
    
     Strong encryption (AEAD ciphers) with no FS       not offered  
    
    
     Forward Secrecy strong encryption (AEAD ciphers)  offered (OK)  
    
    
      
    
    
      
    
    
     Testing server's cipher preferences  
    
    
      
    
    
    Hexcode  Cipher Suite Name (OpenSSL)       KeyExch.   Encryption  Bits     Cipher Suite Name (IANA/RFC)  
    
    
    -----------------------------------------------------------------------------------------------------------------------------  
    
    
    SSLv2  
    
    
     -  
    
    
    SSLv3  
    
    
     -  
    
    
    TLSv1  
    
    
     -  
    
    
    TLSv1.1  
    
    
     -  
    
    
    TLSv1.2  
    
    
     -  
    
    
    TLSv1.3 (listed by strength)  
    
    
     x1302   TLS_AES_256_GCM_SHA384            ECDH 253   AESGCM      256      TLS_AES_256_GCM_SHA384  
    
    
     x1303   TLS_CHACHA20_POLY1305_SHA256      ECDH 253   ChaCha20    256      TLS_CHACHA20_POLY1305_SHA256  
    
    
     x1301   TLS_AES_128_GCM_SHA256            ECDH 253   AESGCM      128      TLS_AES_128_GCM_SHA256  
    
    
     x1304   TLS_AES_128_CCM_SHA256            ECDH 253   AESCCM      128      TLS_AES_128_CCM_SHA256  
    
    
     x1305   TLS_AES_128_CCM_8_SHA256          ECDH 253   AESCCM8     128      TLS_AES_128_CCM_8_SHA256  
    
    
      
    
    
     Has server cipher order?     no (TLS 1.3 only)  
    
    
     (limited sense as client will pick)  
    
    
      
    
    
     Testing robust forward secrecy (FS) -- omitting Null Authentication/Encryption, 3DES, RC4  
    
    
      
    
    
     FS is offered (OK)           TLS_AES_256_GCM_SHA384 TLS_CHACHA20_POLY1305_SHA256 TLS_AES_128_GCM_SHA256 TLS_AES_128_CCM_SHA256 TLS_AES_128_CCM_8_SHA256  
    
    
     Elliptic curves offered:     prime256v1 secp384r1 X25519 X448  
    
    
     TLS 1.3 sig_algs offered:    RSA-PSS-RSAE+SHA256 RSA-PSS-RSAE+SHA384 RSA-PSS-RSAE+SHA512  
    
    
      
    
    
     Testing server defaults (Server Hello)  
    
    
      
    
    
     TLS extensions (standard)    "key share/#51" "supported versions/#43" "signature algorithms/#13" "certificate authorities/#47"  
    
    
     Session Ticket RFC 5077 hint no -- no lifetime advertised  
    
    
     SSL Session ID support       no  
    
    
     Session Resumption           Tickets no, ID: no  
    
    
     TLS clock skew               Random values, no fingerprinting possible  
    
    
     Certificate Compression      none  
    
    
     Client Authentication        optional  
    
    
     CA List for Client Auth      L=$$$$,CN=TLSGenSelfSignedtRootCA 2022-03-22T11:27:45.010198  
    
    
     Signature Algorithm          SHA256 with RSA  
    
    
     Server key size              RSA 2048 bits (exponent is 65537)  
    
    
     Server key usage             Digital Signature, Key Encipherment  
    
    
     Server extended key usage    TLS Web Server Authentication  
    
    
     Serial                       01 (OK: length 1)  
    
    
     Fingerprints                 SHA1 A4346FA6FDC61FCD4C0199EA14B8AE0F5D5121B1  
    
    
                                  SHA256 C81025DA6F9BB646239659420D58E73F62CEB7D2AD5AC13FF12A9DE057394953  
    
    
     Common Name (CN)             [redacted]  
    
    
     subjectAltName (SAN)         [redacted] localhost  
    
    
     Trust (hostname)             Ok via SAN (same w/o SNI)  
    
    
     Chain of trust               NOT ok (self signed CA in chain)  
    
    
     EV cert (experimental)       no  
    
    
     Certificate Validity (UTC)   2779 >= 60 days (2022-03-22 07:27 --> 2032-03-19 07:27)  
    
    
                                  >= 10 years is way too long  
    
    
     ETS/"eTLS", visibility info  not present  
    
    
     Certificate Revocation List  --  
    
    
     OCSP URI                     --  
    
    
                                  NOT ok -- neither CRL nor OCSP URI provided  
    
    
     OCSP stapling                not offered  
    
    
     OCSP must staple extension   --  
    
    
     DNS CAA RR (experimental)    not offered  
    
    
     Certificate Transparency     N/A  
    
    
     Certificates provided        2  
    
    
     Issuer                       TLSGenSelfSignedtRootCA 2022-03-22T11:27:45.010198  
    
    
     Intermediate cert validity   #1: ok > 40 days (2032-03-19 07:27). $$$$ <-- $$$$  
    
    
     Intermediate Bad OCSP (exp.) Ok  
    
    
      
    
    
      
    
    
     Testing vulnerabilities  
    
    
      
    
    
     Heartbleed (CVE-2014-0160)                not vulnerable (OK), no heartbeat extension  
    
    
     CCS (CVE-2014-0224)                       not vulnerable (OK)  
    
    
     Ticketbleed (CVE-2016-9244), experiment.  (applicable only for HTTPS)  
    
    
     ROBOT                                     Server does not support any cipher suites that use RSA key transport  
    
    
     Secure Renegotiation (RFC 5746)           not vulnerable (OK)  
    
    
     Secure Client-Initiated Renegotiation     not vulnerable (OK)  
    
    
     CRIME, TLS (CVE-2012-4929)                not vulnerable (OK)  
    
    
     POODLE, SSL (CVE-2014-3566)               not vulnerable (OK), no SSLv3 support  
    
    
     TLS_FALLBACK_SCSV (RFC 7507)              No fallback possible (OK), TLS 1.3 is the only protocol  
    
    
     SWEET32 (CVE-2016-2183, CVE-2016-6329)    not vulnerable (OK)  
    
    
     FREAK (CVE-2015-0204)                     not vulnerable (OK)  
    
    
     DROWN (CVE-2016-0800, CVE-2016-0703)      not vulnerable on this host and port (OK)  
    
    
                                               make sure you don't use this certificate elsewhere with SSLv2 enabled services, see  
    
    
                                               https://search.censys.io/search?resource=hosts&virtual_hosts=INCLUDE&q=C81025DA6F9BB646239659420D58E73F62CEB7D2AD5AC13FF12A9DE057394953  
    
    
     LOGJAM (CVE-2015-4000), experimental      not vulnerable (OK): no DH EXPORT ciphers, no DH key detected with <= TLS 1.2  
    
    
     BEAST (CVE-2011-3389)                     not vulnerable (OK), no SSL3 or TLS1  
    
    
     LUCKY13 (CVE-2013-0169), experimental     not vulnerable (OK)  
    
    
     Winshock (CVE-2014-6321), experimental    not vulnerable (OK)  
    
    
     RC4 (CVE-2013-2566, CVE-2015-2808)        not vulnerable (OK)  
    
    
      
    
    
    Could not determine the protocol, only simulating generic clients.  
    
    
      
    
    
     Running client simulations via sockets  
    
    
      
    
    
     Browser                      Protocol  Cipher Suite Name (OpenSSL)       Forward Secrecy  
    
    
    ------------------------------------------------------------------------------------------------  
    
    
     Android 8.1 (native)         No connection  
    
    
     Android 9.0 (native)         TLSv1.3   TLS_AES_128_GCM_SHA256            253 bit ECDH (X25519)  
    
    
     Android 10.0 (native)        TLSv1.3   TLS_AES_128_GCM_SHA256            253 bit ECDH (X25519)  
    
    
     Android 11 (native)          TLSv1.3   TLS_AES_128_GCM_SHA256            253 bit ECDH (X25519)  
    
    
     Android 12 (native)          TLSv1.3   TLS_AES_128_GCM_SHA256            253 bit ECDH (X25519)  
    
    
     Java 7u25                    No connection  
    
    
     Java 8u161                   No connection  
    
    
     Java 11.0.2 (OpenJDK)        TLSv1.3   TLS_AES_128_GCM_SHA256            256 bit ECDH (P-256)  
    
    
     Java 17.0.3 (OpenJDK)        TLSv1.3   TLS_AES_256_GCM_SHA384            253 bit ECDH (X25519)  
    
    
     go 1.17.8                    TLSv1.3   TLS_AES_128_GCM_SHA256            253 bit ECDH (X25519)  
    
    
     LibreSSL 2.8.3 (Apple)       No connection  
    
    
     OpenSSL 1.0.2e               No connection  
    
    
     OpenSSL 1.1.0l (Debian)      No connection  
    
    
     OpenSSL 1.1.1d (Debian)      TLSv1.3   TLS_AES_256_GCM_SHA384            253 bit ECDH (X25519)  
    
    
     OpenSSL 3.0.3 (git)          TLSv1.3   TLS_AES_256_GCM_SHA384            253 bit ECDH (X25519)  
    

### 使用受限密码套件评估 TLS 1.2 设置

以下接受 TLSv1.2 连接的配置示例在 Erlang 26.2 上通过了关键的 `testssl.sh` 测试：
    
    
    listeners.ssl.default  = 5671  
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.versions.1 = tlsv1.2  
    
    
      
    
    
    ssl_options.verify               = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = false  
    
    
      
    
    
    ssl_options.honor_cipher_order   = true  
    
    
    ssl_options.honor_ecc_order      = true  
    
    
      
    
    
    # These are highly recommended for TLSv1.2 but cannot be used  
    
    
    # with TLSv1.3. If TLSv1.3 is enabled, these lines MUST be removed.  
    
    
    ssl_options.client_renegotiation = false  
    
    
    ssl_options.secure_renegotiate   = true  
    
    
      
    
    
    ssl_options.ciphers.1  = ECDHE-ECDSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.2  = ECDHE-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.3  = ECDH-ECDSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.4  = ECDH-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.5  = DHE-RSA-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.6  = DHE-DSS-AES256-GCM-SHA384  
    
    
    ssl_options.ciphers.7  = ECDHE-ECDSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.8  = ECDHE-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.9  = ECDH-ECDSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.10 = ECDH-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.11 = DHE-RSA-AES128-GCM-SHA256  
    
    
    ssl_options.ciphers.12 = DHE-DSS-AES128-GCM-SHA256  
    

这种启用了 TLSv1.2 的设置被报告为对一组已知的高调漏洞没有漏洞。
    
    
     Using "OpenSSL 3.3.1 4 Jun 2024 (Library: OpenSSL 3.3.1 4 Jun 2024)" [~94 ciphers]  
    
    
     on [redacted]:/opt/homebrew/bin/openssl  
    
    
     (built: "Jun  4 12:53:04 2024", platform: "darwin64-arm64-cc")  
    
    
      
    
    
      
    
    
     Start 2024-08-08 13:42:36                -->> 127.0.0.1:5671 (localhost) <<--  
    
    
      
    
    
     A record via:           /etc/hosts  
    
    
     rDNS (127.0.0.1):       localhost.  
    
    
     Service detected:       certificate-based authentication without providing client certificate and private key => skipping all HTTP checks  
    
    
      
    
    
      
    
    
     Testing protocols via sockets except NPN+ALPN  
    
    
      
    
    
     SSLv2      not offered (OK)  
    
    
     SSLv3      not offered (OK)  
    
    
     TLS 1      not offered  
    
    
     TLS 1.1    not offered  
    
    
     TLS 1.2    offered (OK)  
    
    
     TLS 1.3    not offered and downgraded to a weaker protocol  
    
    
     NPN/SPDY   not offered  
    
    
     ALPN/HTTP2 not offered  
    
    
      
    
    
     Testing cipher categories  
    
    
      
    
    
     NULL ciphers (no encryption)                      not offered (OK)  
    
    
     Anonymous NULL Ciphers (no authentication)        not offered (OK)  
    
    
     Export ciphers (w/o ADH+NULL)                     not offered (OK)  
    
    
     LOW: 64 Bit + DES, RC[2,4], MD5 (w/o export)      not offered (OK)  
    
    
     Triple DES Ciphers / IDEA                         not offered  
    
    
     Obsoleted CBC ciphers (AES, ARIA etc.)            not offered  
    
    
     Strong encryption (AEAD ciphers) with no FS       not offered  
    
    
     Forward Secrecy strong encryption (AEAD ciphers)  offered (OK)  
    
    
      
    
    
      
    
    
     Testing server's cipher preferences  
    
    
      
    
    
    Hexcode  Cipher Suite Name (OpenSSL)       KeyExch.   Encryption  Bits     Cipher Suite Name (IANA/RFC)  
    
    
    -----------------------------------------------------------------------------------------------------------------------------  
    
    
    SSLv2  
    
    
     -  
    
    
    SSLv3  
    
    
     -  
    
    
    TLSv1  
    
    
     -  
    
    
    TLSv1.1  
    
    
     -  
    
    
    TLSv1.2 (server order)  
    
    
     xc030   ECDHE-RSA-AES256-GCM-SHA384       ECDH 253   AESGCM      256      TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384  
    
    
     x9f     DHE-RSA-AES256-GCM-SHA384         DH 2048    AESGCM      256      TLS_DHE_RSA_WITH_AES_256_GCM_SHA384  
    
    
     xc02f   ECDHE-RSA-AES128-GCM-SHA256       ECDH 253   AESGCM      128      TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256  
    
    
     x9e     DHE-RSA-AES128-GCM-SHA256         DH 2048    AESGCM      128      TLS_DHE_RSA_WITH_AES_128_GCM_SHA256  
    
    
    TLSv1.3  
    
    
     -  
    
    
      
    
    
     Has server cipher order?     yes (OK)  
    
    
      
    
    
      
    
    
     Testing robust forward secrecy (FS) -- omitting Null Authentication/Encryption, 3DES, RC4  
    
    
      
    
    
     FS is offered (OK)           ECDHE-RSA-AES256-GCM-SHA384 DHE-RSA-AES256-GCM-SHA384 ECDHE-RSA-AES128-GCM-SHA256 DHE-RSA-AES128-GCM-SHA256  
    
    
     Elliptic curves offered:     prime256v1 secp384r1 secp521r1 brainpoolP256r1 brainpoolP384r1 brainpoolP512r1 X25519 X448  
    
    
     DH group offered:            RFC3526/Oakley Group 14 (2048 bits)  
    
    
     TLS 1.2 sig_algs offered:    RSA+SHA256 RSA+SHA384 RSA+SHA512 RSA-PSS-RSAE+SHA256  
    
    
      
    
    
     Testing server defaults (Server Hello)  
    
    
      
    
    
     TLS extensions (standard)    "renegotiation info/#65281" "EC point formats/#11" "max fragment length/#1"  
    
    
     Session Ticket RFC 5077 hint no -- no lifetime advertised  
    
    
     SSL Session ID support       yes  
    
    
     Session Resumption           Tickets no, Client Auth: ID resumption test not supported  
    
    
     TLS clock skew               -1 sec from localtime  
    
    
     Client Authentication        required  
    
    
     CA List for Client Auth      L=$$$$,CN=TLSGenSelfSignedtRootCA 2022-03-22T11:27:45.010198  
    
    
     Signature Algorithm          SHA256 with RSA  
    
    
     Server key size              RSA 2048 bits (exponent is 65537)  
    
    
     Server key usage             Digital Signature, Key Encipherment  
    
    
     Server extended key usage    TLS Web Server Authentication  
    
    
     Serial                       01 (OK: length 1)  
    
    
     Fingerprints                 SHA1 A4346FA6FDC61FCD4C0199EA14B8AE0F5D5121B1  
    
    
                                  SHA256 C81025DA6F9BB646239659420D58E73F62CEB7D2AD5AC13FF12A9DE057394953  
    
    
     Common Name (CN)             [redacted]  
    
    
     subjectAltName (SAN)         [redacted] localhost  
    
    
     Trust (hostname)             Ok via SAN (same w/o SNI)  
    
    
     Chain of trust               NOT ok (self signed CA in chain)  
    
    
     EV cert (experimental)       no  
    
    
     Certificate Validity (UTC)   2779 >= 60 days (2022-03-22 07:27 --> 2032-03-19 07:27)  
    
    
                                  >= 10 years is way too long  
    
    
     ETS/"eTLS", visibility info  not present  
    
    
     Certificate Revocation List  --  
    
    
     OCSP URI                     --  
    
    
                                  NOT ok -- neither CRL nor OCSP URI provided  
    
    
     OCSP stapling                not offered  
    
    
     OCSP must staple extension   --  
    
    
     DNS CAA RR (experimental)    not offered  
    
    
     Certificate Transparency     --  
    
    
     Certificates provided        2  
    
    
     Issuer                       TLSGenSelfSignedtRootCA 2022-03-22T11:27:45.010198  
    
    
     Intermediate cert validity   #1: ok > 40 days (2032-03-19 07:27). $$$$ <-- $$$$  
    
    
     Intermediate Bad OCSP (exp.) Ok  
    
    
      
    
    
      
    
    
     Testing vulnerabilities  
    
    
      
    
    
     Heartbleed (CVE-2014-0160)                not vulnerable (OK), no heartbeat extension  
    
    
     CCS (CVE-2014-0224)                       not vulnerable (OK)  
    
    
     Ticketbleed (CVE-2016-9244), experiment.  not vulnerable (OK), no session ticket extension  
    
    
     ROBOT                                     Server does not support any cipher suites that use RSA key transport  
    
    
     Secure Renegotiation (RFC 5746)           supported (OK)  
    
    
     Secure Client-Initiated Renegotiation     not having provided client certificate and private key file, the client x509-based authentication prevents this from being tested  
    
    
     CRIME, TLS (CVE-2012-4929)                not vulnerable (OK)  
    
    
     BREACH (CVE-2013-3587)                    not having provided client certificate and private key file, the client x509-based authentication prevents this from being tested  
    
    
     POODLE, SSL (CVE-2014-3566)               not vulnerable (OK), no SSLv3 support  
    
    
     TLS_FALLBACK_SCSV (RFC 7507)              No fallback possible (OK), no protocol below TLS 1.2 offered  
    
    
     SWEET32 (CVE-2016-2183, CVE-2016-6329)    not vulnerable (OK)  
    
    
     FREAK (CVE-2015-0204)                     not vulnerable (OK)  
    
    
     DROWN (CVE-2016-0800, CVE-2016-0703)      not vulnerable on this host and port (OK)  
    
    
                                               make sure you don't use this certificate elsewhere with SSLv2 enabled services, see  
    
    
                                               https://search.censys.io/search?resource=hosts&virtual_hosts=INCLUDE&q=C81025DA6F9BB646239659420D58E73F62CEB7D2AD5AC13FF12A9DE057394953  
    
    
     LOGJAM (CVE-2015-4000), experimental      common prime with 2048 bits detected: RFC3526/Oakley Group 14 (2048 bits),  
    
    
                                               but no DH EXPORT ciphers  
    
    
     BEAST (CVE-2011-3389)                     not vulnerable (OK), no SSL3 or TLS1  
    
    
     LUCKY13 (CVE-2013-0169), experimental     not vulnerable (OK)  
    
    
     Winshock (CVE-2014-6321), experimental    not vulnerable (OK) - CAMELLIA or ECDHE_RSA GCM ciphers found  
    
    
     RC4 (CVE-2013-2566, CVE-2015-2808)        no RC4 ciphers detected (OK)  
    
    
      
    
    
    Could not determine the protocol, only simulating generic clients.  
    
    
      
    
    
     Running client simulations via sockets  
    
    
      
    
    
     Browser                      Protocol  Cipher Suite Name (OpenSSL)       Forward Secrecy  
    
    
    ------------------------------------------------------------------------------------------------  
    
    
     Android 8.1 (native)         TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     Android 9.0 (native)         TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     Android 10.0 (native)        TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     Android 11 (native)          TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     Android 12 (native)          TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     Java 7u25                    No connection  
    
    
     Java 8u161                   TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       521 bit ECDH (P-521)  
    
    
     Java 11.0.2 (OpenJDK)        TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       521 bit ECDH (P-521)  
    
    
     Java 17.0.3 (OpenJDK)        TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     go 1.17.8                    TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     LibreSSL 2.8.3 (Apple)       TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     OpenSSL 1.0.2e               TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       521 bit ECDH (P-521)  
    
    
     OpenSSL 1.1.0l (Debian)      TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     OpenSSL 1.1.1d (Debian)      TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    
    
     OpenSSL 3.0.3 (git)          TLSv1.2   ECDHE-RSA-AES256-GCM-SHA384       253 bit ECDH (X25519)  
    

## TLS 证书和私钥轮换

服务器 TLS 证书（公钥）和私钥有过期日期，需要不时更换（轮换）。

更换过程涉及以下步骤：

  1. 在磁盘上替换文件。
  2. 清除节点上的证书和私钥存储缓存。



如果没有第二个步骤，新证书/密钥对将在一段时间后由节点使用，因为运行时中的 TLS 实现会清除其证书存储缓存。

### 在磁盘上更换证书和私钥文件

只需用新版本替换服务器证书、服务器私钥和（如果需要）证书颁发机构捆绑包文件。

### 清除证书和私钥存储缓存

  * bash
  * PowerShell
  * cmd


    
    
    rabbitmqctl eval -n [target-node@hostname] 'ssl:clear_pem_cache().'  
    
    
    
    rabbitmqctl.bat eval -n [target-node@hostname] 'ssl:clear_pem_cache().'  
    
    
    
    rabbitmqctl.bat eval -n [target-node@hostname] "ssl:clear_pem_cache()."  
    

## Trust Store 插件

在某些环境中，有一组叶子（客户端）受信任证书必须被信任，仅此而已，不需要遍历链，也不使用传统的信任根（CA）。

这种方法通常用于客户端证书也用作身份、必须是唯一的且经常变动（更改：添加一些，移除另一些）的环境中。

`rabbitmq_trust_store` 是一个插件，它重写对等方验证算法来执行此操作：验证连接客户端的证书是否属于某个集合（白名单）。

白名单来自本地文件系统目录或遵循一小组约定的 HTTP API 端点。该列表以可配置的时间间隔刷新，允许添加或删除证书，而无需重启节点或影响现有连接。

### 证书提供程序

信任存储支持两种受信任叶子客户端证书的来源（提供程序）：

  * **文件系统提供程序** （默认）：从本地目录加载证书。
  * **HTTPS 提供程序** ：从远程 HTTPS 端点检索证书。



#### 文件系统提供程序

要使用文件系统提供程序，请配置一个包含 PEM 格式受信任客户端证书的目录：
    
    
    # will monitor `/path/to/trust-store/whitelist` for files additions and deletion  
    
    
    trust_store.directory = /path/to/trust-store/whitelist  
    
    
    # scan the above directory every 30 seconds  
    
    
    trust_store.refresh_interval = 30  
    

将 `refresh_interval` 设置为 `0` 将禁用自动重新加载。

#### HTTP 提供程序

要从遵循特定约定的远程 HTTPS 端点检索证书：
    
    
    trust_store.providers.1 = http  
    
    
    trust_store.url = https://certs.example.com/trusted  
    
    
    trust_store.refresh_interval = 30  
    

#### 提供程序 HTTP API

远程服务器必须公开一个列出证书并允许获取单个证书的 HTTP API。

`GET <url>` 必须以 `200 OK` 和以下正文响应：
    
    
    {  
    
    
      "certificates": [  
    
    
        {"id": "certificate-1", "path": "/certificates/1.pem"},  
    
    
        {"id": "certificate-2", "path": "/certificates/2.pem"}  
    
    
        // , ...  
    
    
      ]  
    
    
    }  
    

证书 ID 必须是有效的文件名并且是唯一的。

`GET <url>/<relative-url>`（例如上面示例中的 `"/certificates/1.pem"`）必须以 `200 OK` 响应，并在其正文中返回 PEM 编码的证书。

提供程序使用 `If-Modified-Since` 标头来避免不必要的重新下载。

如果 HTTPS 端点本身使用 x.509 证书对客户端进行身份验证，请配置其 CA 证书捆绑包、公钥和私钥：
    
    
    trust_store.ssl_options.certfile   = /path/to/client/client_certificate.pem  
    
    
    trust_store.ssl_options.keyfile    = /path/to/client/client_key.pem  
    
    
    trust_store.ssl_options.cacertfile = /path/to/ca/trusted_ca_bundle.pem  
    

最后，可以使用 `trust_store.https_request_timeout` 设置请求超时。

### 将信任存储用于客户端 (x509) 证书身份验证

上述 Trust Store 插件和 `rabbitmq_auth_mechanism_ssl` 插件承担了两个互补的角色：

  * `rabbitmq_trust_store` 处理**证书验证** ：验证客户端证书是否在受信任的白名单上。
  * `rabbitmq_auth_mechanism_ssl` 处理**客户端身份验证** ：从证书中提取身份并将其映射到 RabbitMQ 用户。



结合 EXTERNAL 身份验证机制，它们允许客户端仅通过 x.509 证书进行身份验证。

此设置需要启用两个插件
    
    
    rabbitmq-plugins enable rabbitmq_trust_store  
    
    
    rabbitmq-plugins enable rabbitmq_auth_mechanism_ssl  
    

然后在 `rabbitmq.conf` 中配置 TLS、信任库（trust store）和身份验证机制
    
    
    # TLS listener  
    
    
    listeners.ssl.default = 5671  
    
    
      
    
    
    ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
    ssl_options.certfile   = /path/to/server_certificate.pem  
    
    
    ssl_options.keyfile    = /path/to/server_key.pem  
    
    
    ssl_options.verify     = verify_peer  
    
    
    ssl_options.fail_if_no_peer_cert = true  
    
    
      
    
    
    # Trust store: directory containing whitelisted client certificates  
    
    
    trust_store.directory = /path/to/trust-store/whitelist  
    
    
    trust_store.refresh_interval = 30  
    
    
      
    
    
    # Enable the EXTERNAL mechanism so clients can authenticate with a certificate  
    
    
    auth_mechanisms.1 = EXTERNAL  
    
    
    auth_mechanisms.2 = PLAIN  
    
    
      
    
    
    # Extract the username from the certificate's Common Name (CN) field.  
    
    
    # Other supported options: distinguished_name (default), subject_alternative_name  
    
    
    ssl_cert_login_from = common_name  
    

`ssl_cert_login_from` 设置控制客户端证书的哪个字段被用作 RabbitMQ 用户名

  * `distinguished_name`（默认值）：使用 RFC 4514 格式的完整主题 DN（例如，`CN=guest,O=client,L=Paris,ST=France,C=FR`）
  * `common_name`：仅使用 CN 字段（例如，`guest`）
  * `subject_alternative_name`：使用 SAN 条目，通过 `ssl_cert_login_san_type`（例如 `dns`, `email`）和 `ssl_cert_login_san_index`（用于从列表中选择特定条目）进行配置



在配置的 身份验证和授权后端 中，必须存在与提取出的名称匹配的 RabbitMQ 用户。

当使用 `EXTERNAL` 机制时，客户端提供的密码将被忽略。

### 检查并刷新白名单

列出当前已加载的证书
    
    
    rabbitmq-diagnostics list_trust_store_certificates  
    

手动触发白名单刷新
    
    
    rabbitmqctl refresh_trust_store  
    

### TLS 会话缓存

TLS 会话缓存会绕过信任库证书验证。当客户端恢复缓存的 TLS 会话时，不会查询信任库。为了确保删除的证书能立即被拒绝，请禁用 TLS 会话缓存
    
    
    ssl_options.reuse_sessions = false  
    

请参阅 插件 README 以获取更多详细信息和高级配置选项。

## 在 Erlang 客户端中使用 TLS

在 RabbitMQ Erlang 客户端中启用 TLS 与配置其他网络相关设置类似。`#amqp_params_network` 记录提供了一个字段 `ssl_options`，用于包含所有 标准 Erlang TLS 选项。

### Erlang TLS 选项

必须提供的三个重要选项是

  * `cacertfile` 选项指定我们要隐式信任的根证书颁发机构（Certificate Authorities）的证书。
  * `certfile` 是 PEM 格式的客户端证书
  * `keyfile` 是 PEM 格式的客户端私钥文件



`server_name_indication` \- 将此选项设置为将要建立 TLS 连接的服务器主机名，以启用对服务器提供的证书进行“服务器名称指示”验证。这确保了服务器证书的 `CN=` 值在 TLS 连接建立期间得到验证。你可以通过将 `server_name_indication` 设置为不同的主机名或特殊值 `disable` 来禁用此验证，从而覆盖此行为。请注意，默认情况下，SNI 是**不**启用的。此默认设置将在未来的 RabbitMQ Erlang 客户端版本中更改。

`verify` \- 将此选项设置为 `verify_peer` 以启用 X509 证书链验证。`depth` 选项配置证书验证深度。请注意，默认情况下，`verify` 设置为 `verify_none`，这会禁用证书链验证。此默认设置将在未来的 RabbitMQ Erlang 客户端版本中更改。

### 代码示例
    
    
    SslOpts = [{cacertfile, "/path/to/ca_certificate.pem"},  
    
    
               {certfile, "/path/to/client/certificate.pem"},  
    
    
               {keyfile, "/path/to/client/private_key.pem"},  
    
    
      
    
    
               %% only necessary with intermediate CAs  
    
    
               %% {depth, 2},  
    
    
      
    
    
               %% Note: it is recommended to set 'verify' to  
    
    
               %% to 'verify_peer' to ensure that X509  
    
    
               %% certificate chain validation is enabled  
    
    
               %%  
    
    
               %% Do not set 'verify' or set it to verify_none  
    
    
               %% if x509 certificate chain validation is  
    
    
               %% not desired  
    
    
               {verify, verify_peer},  
    
    
      
    
    
               %% If Server Name Indication validation is desired,  
    
    
               %% set the following option to the host name to which  
    
    
               %% the connection is made. If necessary, this option  
    
    
               %% may be set to another host name to match the server  
    
    
               %% certificate's CN= value.  
    
    
               %% Do not set this option or set it to the atom 'disable'  
    
    
               %% to disable SNI validation  
    
    
               {server_name_indication, "my.rmq-server.net"}],  
    
    
      
    
    
    Params = #amqp_params_network{host = "my.rmq-server.net",  
    
    
                                  port = 5671,  
    
    
                                  ssl_options = SslOpts}  
    
    
      
    
    
    {ok, Conn} = amqp_connection:start(Params),  
    

你现在可以像使用普通连接一样使用 Conn 了。

## 手动生成 CA、证书和私钥

本指南的这一部分介绍了如何生成证书颁发机构（CA），并使用它来生成和签名两个证书/密钥对，一个用于服务器，另一个用于客户端库。请注意，此过程可以 使用现有工具自动化，我们建议这样做。本节旨在帮助那些希望加深对该过程、OpenSSL 命令行工具以及 OpenSSL 配置某些重要方面了解的人。

本指南假定使用类 UNIX 操作系统（Linux、MacOS、BSD 变体等），并且 `PATH` 中有可用的最新版本 OpenSSL。

首先，让我们为我们的测试证书颁发机构创建一个目录
    
    
    mkdir testca  
    
    
    cd testca  
    
    
    mkdir certs private  
    
    
    chmod 700 private  
    
    
    echo 01 > serial  
    
    
    touch index.txt  
    

现在，在新建的 `testca` 目录中添加以下 OpenSSL 配置文件 `openssl.cnf`
    
    
    [ ca ]  
    
    
    default_ca = testca  
    
    
      
    
    
    [ testca ]  
    
    
    dir = .  
    
    
    certificate = $dir/ca_certificate.pem  
    
    
    database = $dir/index.txt  
    
    
    new_certs_dir = $dir/certs  
    
    
    private_key = $dir/private/ca_private_key.pem  
    
    
    serial = $dir/serial  
    
    
      
    
    
    default_crl_days = 7  
    
    
    default_days = 365  
    
    
    default_md = sha256  
    
    
      
    
    
    policy = testca_policy  
    
    
    x509_extensions = certificate_extensions  
    
    
      
    
    
    [ testca_policy ]  
    
    
    commonName = supplied  
    
    
    stateOrProvinceName = optional  
    
    
    countryName = optional  
    
    
    emailAddress = optional  
    
    
    organizationName = optional  
    
    
    organizationalUnitName = optional  
    
    
    domainComponent = optional  
    
    
      
    
    
    [ certificate_extensions ]  
    
    
    basicConstraints = CA:false  
    
    
      
    
    
    [ req ]  
    
    
    default_bits = 2048  
    
    
    default_keyfile = ./private/ca_private_key.pem  
    
    
    default_md = sha256  
    
    
    prompt = yes  
    
    
    distinguished_name = root_ca_distinguished_name  
    
    
    x509_extensions = root_ca_extensions  
    
    
      
    
    
    [ root_ca_distinguished_name ]  
    
    
    commonName = hostname  
    
    
      
    
    
    [ root_ca_extensions ]  
    
    
    basicConstraints = CA:true  
    
    
    keyUsage = keyCertSign, cRLSign  
    
    
      
    
    
    [ client_ca_extensions ]  
    
    
    basicConstraints = CA:false  
    
    
    keyUsage = digitalSignature,keyEncipherment  
    
    
    extendedKeyUsage = 1.3.6.1.5.5.7.3.2  
    
    
      
    
    
    [ server_ca_extensions ]  
    
    
    basicConstraints = CA:false  
    
    
    keyUsage = digitalSignature,keyEncipherment  
    
    
    extendedKeyUsage = 1.3.6.1.5.5.7.3.1  
    

接下来，我们需要生成测试证书颁发机构将使用的密钥和证书。仍在 `testca` 目录中
    
    
    openssl req -x509 -config openssl.cnf -newkey rsa:2048 -days 365 \  
    
    
        -out ca_certificate.pem -outform PEM -subj /CN=MyTestCA/ -nodes  
    
    
    openssl x509 -in ca_certificate.pem -out ca_certificate.cer -outform DER  
    

这就是生成测试证书颁发机构所需的全部步骤。根证书位于 `ca_certificate.pem` 中，也位于 `testca/ca_certificate.cer` 中。这两个文件包含相同的信息，但格式不同（PEM 和 DER）。大多数软件使用前者，但某些工具需要后者。

设置好证书颁发机构后，我们现在需要为客户端和服务器生成私钥和证书。RabbitMQ 代理使用 PEM 格式的证书和私钥。有些客户端库使用 PEM 格式，另一些则需要转换为其他格式（例如 PKCS#12）。

Java 和 .NET 客户端使用一种称为 PKCS#12 的证书格式和自定义证书存储。证书存储包含客户端的证书和密钥。PKCS 存储通常受密码保护，因此必须提供密码。

创建服务器和客户端证书的过程非常相似。首先是服务器
    
    
    cd ..  
    
    
    ls  
    
    
    # => testca  
    
    
    mkdir server  
    
    
    cd server  
    
    
    openssl genrsa -out private_key.pem 2048  
    
    
    openssl req -new -key private_key.pem -out req.pem -outform PEM \  
    
    
        -subj /CN=$(hostname)/O=server/ -nodes  
    
    
    cd ../testca  
    
    
    openssl ca -config openssl.cnf -in ../server/req.pem -out \  
    
    
        ../server/server_certificate.pem -notext -batch -extensions server_ca_extensions  
    
    
    cd ../server  
    
    
    openssl pkcs12 -export -out server_certificate.p12 -in server_certificate.pem -inkey private_key.pem \  
    
    
        -passout pass:MySecretPassword  
    

现在是客户端
    
    
    cd ..  
    
    
    ls  
    
    
    # => server testca  
    
    
    mkdir client  
    
    
    cd client  
    
    
    openssl genrsa -out private_key.pem 2048  
    
    
    openssl req -new -key private_key.pem -out req.pem -outform PEM \  
    
    
        -subj /CN=$(hostname)/O=client/ -nodes  
    
    
    cd ../testca  
    
    
    openssl ca -config openssl.cnf -in ../client/req.pem -out \  
    
    
        ../client/client_certificate.pem -notext -batch -extensions client_ca_extensions  
    
    
    cd ../client  
    
    
    openssl pkcs12 -export -out client_certificate.p12 -in client_certificate.pem -inkey private_key.pem \  
    
    
        -passout pass:MySecretPassword  
    

上述两个示例生成的私钥大小为 2048 位。通过为 `openssl genrsa` 提供不同的值，可以使用更长（更安全但生成速度较慢）的密钥，例如：
    
    
    openssl genrsa -out private_key.pem 4096  
    

另一个选择是使用 椭圆曲线密码学 (Elliptic Curve Cryptography) 生成密钥。不要使用 `openssl genrsa`，而是使用 `openssl ecparam`，如下所示：
    
    
    openssl ecparam -out private_key.pem -genkey -name prime256v1  
    

上例中的 `prime256v1` 是椭圆曲线名称。不同版本的 OpenSSL 具有不同的可用曲线，可以使用 `openssl ecparam -list_curves` 列出它们。
