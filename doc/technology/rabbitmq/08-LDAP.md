---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/ldap
---

# LDAP 支持

## 概述

RabbitMQ 可以通过委托外部 LDAP 服务器来执行身份验证和授权。此功能由一个内置插件提供，该插件必须先启用。

提示

LDAP 插件通常与另一个插件 `rabbitmq_auth_backend_cache` 结合使用，以改善延迟并显著降低 LDAP 服务器的负载。

身份验证和授权操作由 RabbitMQ 操作员配置的模板转换为 LDAP 查询。

LDAP 操作流程部分提供了该插件工作原理的更详细概述。

该插件主要针对 OpenLDAP 和 Microsoft Active Directory。其他 LDAP v3 实现也应能正常工作。

本指南简要概述了 LDAP 术语，但通常假设读者对 LDAP 有基本的了解。网上有许多面向初学者的 LDAP 入门教程，例如：一、二 以及 LDAP 术语表。

本指南涵盖了 RabbitMQ 使用的 LDAP 操作流程、LDAP 模型如何映射到 RabbitMQ 权限模型、如何使用 TLS 连接到 LDAP 服务器，以及可用于故障排除和代理 LDAP 请求的工具。

## 先决条件

RabbitMQ LDAP 插件依赖于名为 `eldap` 的 LDAP 客户端。该库包含在大多数操作系统的 Erlang/OTP 发行版中，包括 Windows 和带有 RabbitMQ 团队零依赖 Erlang 包的基于 RPM 的 Linux。

### Debian、Ubuntu 上缺少 LDAP 客户端包

在 Debian 和 Ubuntu 上，Erlang/OTP 被拆分为许多独立的包。`eldap` 库由必须单独安装的 `erlang-eldap` 包提供。
    
    
    sudo apt-get install -y erlang-eldap  
    

在不支持该库的 Erlang 安装上，**无法**使用 LDAP 支持。

请参阅 Erlang 兼容性指南以了解更多信息。

## 启用插件

LDAP 插件随 RabbitMQ 一起提供。要启用它，请使用 rabbitmq-plugins。
    
    
    rabbitmq-plugins enable rabbitmq_auth_backend_ldap  
    

## 启用 LDAP AuthN 和 AuthZ 后端

启用插件后，有必要配置节点以使用它。

这涉及：

  * 将 LDAP 列为 身份验证 (authN) 和/或授权 (authZ) 后端
  * 配置 LDAP 服务器端点
  * 指定将用于各种 authZ 权限检查的 LDAP 查询



以下示例将配置 RabbitMQ **仅**使用 LDAP 进行身份验证和授权，并忽略内部数据库。
    
    
    # use LDAP exclusively for authentication and authorisation  
    
    
    auth_backends.1 = ldap  
    

在 `advanced.config` 文件中，相同的设置如下所示：
    
    
    {rabbit, [  
    
    
      {auth_backends, [rabbit_auth_backend_ldap]}  
    
    
    ]}  
    

以下示例将指示节点先尝试 LDAP，如果用户无法通过 LDAP 进行身份验证，则回退到内部数据库。
    
    
    # try LDAP first  
    
    
    auth_backends.1 = ldap  
    
    
    # fall back to the internal database  
    
    
    auth_backends.2 = internal  
    

`advanced.config` 格式中的相同示例：
    
    
    {rabbit,[  
    
    
      {auth_backends, [rabbit_auth_backend_ldap, rabbit_auth_backend_internal]}  
    
    
    ]}  
    

在以下示例中，LDAP 将首先用于身份验证。如果用户在 LDAP 中被找到，则密码将针对 LDAP 进行核对，后续授权检查将针对内部数据库进行（因此 LDAP 中的用户也必须存在于内部数据库中，密码可选为空）。如果用户未在 LDAP 中找到，则仅使用内部数据库进行第二次尝试。
    
    
    # use LDAP for authentication first  
    
    
    auth_backends.1.authn = ldap  
    
    
    # use internal database for authorisation  
    
    
    auth_backends.1.authz = internal  
    
    
    # fall back to the internal database  
    
    
    auth_backends.2 = internal  
    

高级配置格式中：
    
    
    {rabbit,[{auth_backends, [{rabbit_auth_backend_ldap, rabbit_auth_backend_internal},  
    
    
                               rabbit_auth_backend_internal]}]}  
    

## 配置

一旦插件启用并且其后端连接好，就必须配置许多 LDAP 特定设置。它们包括 LDAP 服务器列表、身份验证和授权设置等。

默认配置允许所有用户访问所有 vhost 中的所有对象，但不会使他们成为管理员。通过配置 LDAP 查询可以限制访问。

### LDAP 服务器

为了使插件能够连接到 LDAP 服务器，必须使用 `auth_ldap.servers` 键配置至少一个服务器主机名或 IP 地址。如果提供了多个值，列表值可以是主机名或 IP 地址。此值必须进行配置。以下示例将插件配置为使用两个 LDAP 服务器。它们将按顺序尝试，直到与其中一个的连接成功为止。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    

使用经典配置格式的相同示例：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        {servers, ["ldap.eng.megacorp.local", "192.168.0.100"]}  
    
    
      ]}  
    
    
    ].  
    

LDAP 服务器通常使用端口 `389`，这也是 LDAP 插件默认使用的端口。可以使用 `auth_ldap.port` 来覆盖此设置。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    auth_ldap.port      = 6389  
    

使用经典配置格式的相同示例：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        {servers, ["ldap.eng.megacorp.local", "192.168.0.100"]},  
    
    
        {port,    6389}  
    
    
      ]}  
    
    
    ].  
    

可以使用 `auth_ldap.timeout` 配置键为 LDAP 服务器的 TCP 连接设置超时时间。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    # 15 seconds in milliseconds  
    
    
    auth_ldap.timeout   = 15000  
    

默认为 `infinity`，即无超时。

LDAP 服务器连接会被池化，以避免过多的连接流失和 LDAP 服务器负载。默认情况下，连接池最多有 64 个连接。这可以使用 `auth_ldap.connection_pool_size` 设置进行控制。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    auth_ldap.connection_pool_size = 256  
    

空闲的池化连接在一段时间后会关闭，该时间可通过 `auth_ldap.idle_timeout` 配置（以毫秒为单位或设为 `infinity`）。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    auth_ldap.connection_pool_size = 256  
    
    
    # 300 seconds in milliseconds  
    
    
    auth_ldap.idle_timeout = 300000  
    

建议设置为 120 到 300 秒之间的值。

## 将 TLS 用于 LDAP 连接

重要

从 Erlang 26 开始，TLS 实现默认启用TLS 客户端对等方验证。

如果未配置客户端 TLS 证书和密钥对，启用 TLS 的 LDAP 服务器连接将失败。如果不需要对等方验证，则可以禁用它，否则必须为 LDAP 连接配置证书和私钥对。

可以使用 TLS 连接到 LDAP 服务器。要指示插件执行此操作，请将 `auth_ldap.use_ssl` 设置为 `true`。如果 LDAP 服务器使用 StartTLS，请改为使用 `auth_ldap.use_starttls`。请注意，这些设置是互斥的（不能同时使用）。两个值默认为 `false`。

客户端 TLS 设置使用 `ssl_options` 进行配置，这与 RabbitMQ 中其他地方的 TLS 设置非常相似。

这是一个极简示例：
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    # enables TLS for connections to the LDAP server  
    
    
    auth_ldap.use_ssl   = true  
    
    
      
    
    
    # Disables peer certificate chain verification. See the section on Peer Verification  
    
    
    # below.  
    
    
    #  
    
    
    # Doing so loses one of the key benefits of TLS and make the setup less secure  
    
    
    # but also simplifies node configuration.  
    
    
    auth_ldap.ssl_options.verify = verify_none  
    

该插件还可以使用 StartTLS 进行连接。这种较旧且不太安全的选项**不被推荐**，但对于较旧的 LDAP 服务器可能是必要的。
    
    
    auth_ldap.servers.1 = ldap.eng.megacorp.local  
    
    
    auth_ldap.servers.2 = 192.168.0.100  
    
    
      
    
    
    # Enables StartTLS for connections to the LDAP server.  
    
    
    # Prefer auth_ldap.use_ssl with reasonably modern LDAP servers!  
    
    
    auth_ldap.use_starttls   = true  
    
    
      
    
    
    # Disables peer certificate chain verification. See the section on Peer Verification  
    
    
    # below.  
    
    
    #  
    
    
    # Doing so loses one of the key benefits of TLS and make the setup less secure  
    
    
    # but also simplifies node configuration.  
    
    
    auth_ldap.ssl_options.verify = verify_none  
    

### 可用于 LDAP 的客户端 TLS 选项

有多种 TLS 客户端选项可用：

#### CA 证书、客户端证书和私钥
    
    
    # local filesystem path to a CA certificate bundle file  
    
    
    auth_ldap.ssl_options.cacertfile = /path/to/ca_certificate.pem  
    
    
      
    
    
    # local filesystem path to a client certificate file  
    
    
    auth_ldap.ssl_options.certfile = /path/to/client_certfile.pem  
    
    
      
    
    
    # local filesystem path to a client private key file  
    
    
    auth_ldap.ssl_options.keyfile = /path/to/client_key.pem  
    

#### SNI (服务器名称指示)

服务器名称指示 (SNI) 可以配置为到 LDAP 服务器的出站 TLS 连接。如果不设置，默认值将是用于连接的主机名（请参阅上面的 `auth_ldap.servers.*`）。
    
    
    # Sets Server Name Indication for LDAP connections.  
    
    
    # If an LDAP server host is available via multiple domain names, set this value  
    
    
    # to the preferred domain name target LDAP server  
    
    
    auth_ldap.ssl_options.sni = ldap.identity.eng.megacorp.local  
    

#### 主机名验证

主机名验证不应与 对等证书链验证 混淆。这些设置是正交的，可以组合使用。
    
    
    # take wildcards into account when performing hostname verification  
    
    
    auth_ldap.ssl_options.hostname_verification = wildcard  
    
    
    
    # disables hostname verification  
    
    
    auth_ldap.ssl_options.hostname_verification = none  
    

#### 对等验证

从 Erlang 26 开始，LDAP TLS 客户端默认将执行 对等证书链验证。

对等证书链验证不应与主机名匹配验证混淆。这些设置是正交的，可以组合使用。
    
    
    # Enables peer certificate chain verification.  
    
    
    # This behavior is the default starting with Erlang 26 (and thus RabbitMQ 3.13+)  
    
    
    auth_ldap.ssl_options.verify = verify_peer  
    
    
    
    # Disables peer certificate chain verification.  
    
    
    #  
    
    
    # Doing so loses one of the key benefits of TLS and make the setup less secure  
    
    
    # but also significantly simplifies node configuration.  
    
    
    auth_ldap.ssl_options.verify = verify_none  
    

`advanced.conf` 格式中的相同示例：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        {servers, ["ldap1.eng.megacorp.local", "ldap2.eng.megacorp.local"]},  
    
    
      
    
    
        {use_ssl,     true},  
    
    
        {ssl_options, [  
    
    
          %% Enables peer certificate chain verification.  
    
    
          %% This behavior is the default starting with Erlang 26 (and thus RabbitMQ 3.13+)  
    
    
          {verify, verify_peer}  
    
    
        ]}  
    
    
      ]}  
    
    
    ].  
    
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        {servers, ["ldap1.eng.megacorp.local", "ldap2.eng.megacorp.local"]},  
    
    
      
    
    
        {use_ssl,     true},  
    
    
      
    
    
        {ssl_options, [  
    
    
          %% Disables peer certificate chain verification.  
    
    
          %%  
    
    
          %% Doing so loses one of the key benefits of TLS and make the setup less secure  
    
    
          %% but also significantly simplifies node configuration.  
    
    
          {verify, verify_none}  
    
    
        ]}  
    
    
      ]}  
    
    
    ].  
    

#### 对等链验证深度

对于使用多个中间证书的服务器，可以增加 证书链验证深度。
    
    
    auth_ldap.ssl_options.depth = 5  
    

#### 已启用的 TLS 版本
    
    
    # use TLSv1.2 only  
    
    
    ssl_options.versions.1 = tlsv1.2  
    

### `advanced.config` 中的 TLS 选项

以下示例使用 `advanced.config` 格式：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
         {servers, ["ldap1.eng.megacorp.local", "ldap2.eng.megacorp.local"]},  
    
    
      
    
    
         {use_ssl,     true},  
    
    
         {ssl_options, [{cacertfile, "/path/to/ca_certificate.pem"},  
    
    
                        {certfile,   "/path/to/server_certificate.pem"},  
    
    
                        {keyfile,    "/path/to/server_key.pem"},  
    
    
                        %% Disables peer certificate chain verification.  
    
    
                        %%  
    
    
                        %% Doing so loses one of the key benefits of TLS and make the setup less secure  
    
    
                        %% but also significantly simplifies node configuration.  
    
    
                        {verify, verify_none},  
    
    
                        {server_name_indication, "ldap.identity.eng.megacorp.local"},  
    
    
                        {ssl_hostname_verification, wildcard}  
    
    
       ]}  
    
    
    ].  
    

## 用于提高效率和降低负载的 LDAP 查询缓存

一个特殊的 缓存后端 可以与其它后端结合使用，以显著降低它们在 LDAP 服务器上生成的负载。

建议依赖 LDAP 进行身份验证和授权的生产集群将其与缓存后端结合使用。对于大多数系统，15 到 60 秒的缓存间隔在安全性和效率之间取得了良好的平衡。

## LDAP 基础知识和术语

本节涵盖了本文档中使用的一些基本 LDAP 术语。有关 LDAP 入门，请参阅 Digital Ocean 提供的此概述以及 ldap.com 的 LDAP 术语表。

术语| 描述  
---|---  
Bind (绑定)| LDAP 中指代“身份验证请求”。  
Distinguished Name (DN，可分辨名称)| DN 是 LDAP 目录（树）中的唯一键，用于标识对象（如用户或组）。插件会在身份验证阶段将客户端提供的用户名转换为 DN（见下文）。可以把 DN 想象成文件系统中的绝对路径。  
Common Name (CN，通用名称)| 树中对象的短标识符。此标识符在 LDAP 数据库的对象类（类型）之间会有所不同。例如，个人的通用名称将是全名。组的通用名称将是该组的名称。可以把 CN 想象成文件系统中的文件名。  
Attribute (属性)| 对象的属性（键值对）。可以将其视为面向对象编程语言中对象的字段。  
Object Class (对象类)| 一组预定义的属性。可以将其视为面向对象语言中的类型（类）。  
Entry (条目)| LDAP 数据库实体，例如个人或组。它具有关联的对象类和一个或多个属性（包括通用名称）。由于实体位于 LDAP 数据库树中的某处，它还必须具有唯一标识它的可分辨名称。LDAP 插件查询就是使用条目（查找、检查成员资格、比较属性等）。LDAP 数据库必须包含一些条目（通常是用户、组）才能对 RabbitMQ 的身份验证和授权发挥实际作用。  
  
### LDAP 操作流程

为了执行 LDAP 查询，插件将打开与列表中第一个可达 LDAP 服务器的连接。然后，根据凭据配置，它将执行匿名绑定或“简单绑定”（使用用户名/密码对对 LDAP 服务器进行用户身份验证）。用于执行绑定的凭据可以从客户端提供的用户名导出，详见下一节。

如果配置了 vhost 访问查询，它将接下来执行，否则将无条件授予 vhost 访问权限。

此时，可以认为连接已成功协商并建立。例如，应该可以在其上打开通道。该连接上执行的所有进一步操作都将执行授权查询之一。例如，声明队列将执行资源访问查询（下文介绍）。向主题交换机发布消息还将额外执行主题访问查询。请参阅访问控制指南以了解更多信息。

### 用户名和可分辨名称

在简单绑定阶段，`user_dn_pattern` 模式用于将提供的用户名转换为用于绑定的值。默认情况下，该模式按原样传递提供的值（即模式为 `${username}`）。如果指定了 `user_bind_pattern`，它将优先于 `user_dn_pattern`。如果在可分辨名称查找阶段需要使用不同的 `user_dn_pattern`，这会很方便。请注意，上述内容不适用于匿名绑定，也不适用于 `dn_lookup_bind` 未设置为 `as_user` 的情况。

客户端连接提供用户名，这些用户名被转换为 LDAP 中的可分辨名称 (DN)。有两种方法可以实现。最简单的方法是通过 `user_dn_pattern` 进行字符串替换。要使用此选项，请将 `user_dn_pattern` 设置为一个恰好包含一个 `${username}` 实例的字符串，该变量将被替换为客户端提供的用户名值。

例如，将 user_dn_pattern 设置为 `"cn=${username},ou=People,dc=example,dc=com"` 会导致用户名 `simon` 被转换为 DN `cn=simon,ou=People,dc=example,dc=com`。默认值为 `"${username}"`，换句话说，用户名被逐字使用。

将用户名转换为可分辨名称的另一种方法是通过 LDAP 查找。为此，请将 `auth_ldap.dn_lookup_attribute` 设置为表示用户名的属性名称，并将 `auth_ldap.dn_lookup_base` 设置为查询的基础 DN。查找可以在两个时间点之一完成：在尝试以相关用户身份绑定之前，或者之后。

要在绑定后执行查找，请将 `auth_ldap.dn_lookup_bind` 保留为其默认值 `as_user`。LDAP 插件随后将使用用户的纯（未修改）用户名进行绑定以进行登录，然后查找其 DN。为了使此操作起作用，LDAP 服务器需要配置为允许使用纯用户名进行绑定（Microsoft Active Directory 通常会这样做）。

要在绑定前执行查找，请按如下方式设置 `dn_lookup_bind`、`dn_lookup_base` 和 `dn_lookup_attribute`。LDAP 插件随后将首先使用这些凭据进行绑定以进行查找，然后使用用户的 DN 和密码进行绑定以进行登录。
    
    
    auth_ldap.dn_lookup_bind.user_dn = CN=myuser,OU=users,DC=gopivotal,DC=com  
    
    
    auth_ldap.dn_lookup_bind.password = test1234  
    
    
    auth_ldap.dn_lookup_attribute = userPrincipalName  
    
    
    auth_ldap.dn_lookup_base = DC=gopivotal,DC=com  
    

请考虑以下示例：
    
    
    auth_ldap.dn_lookup_attribute = userPrincipalName  
    
    
    auth_ldap.dn_lookup_base = DC=gopivotal,DC=com  
    

通过此配置，可以使用电子邮件地址进行身份验证（`userPrincipalName` 值通常是电子邮件地址），并让本地 Active Directory 服务器返回一个实际的 DN 来进行登录。

如果同时设置了 `auth_ldap.dn_lookup_attribute` 和 `auth_ldap.user_dn_pattern`，则这两种方法将结合使用：插件填写模板，然后搜索 DN。

`auth_ldap.dn_lookup_bind` 的默认值为 `as_user`。对于 `auth_ldap.dn_lookup_base` 和 `auth_ldap.dn_lookup_attribute`，其默认值为 `none`。

### LDAP 活动日志记录

该插件允许使用 `auth_ldap.log`（经典配置格式中为 `rabbitmq_auth_backend_ldap.log`）设置来控制 LDAP 活动日志记录的详细程度。这对于故障排除至关重要。

将值设置为 `true` 将启用 LDAP 插件用于做出决策的逻辑的详细日志记录。在此模式下，绑定请求结果中的凭据将被屏蔽。不建议在生产系统中使用此模式，但偶尔会有用。

`network` 值的工作方式与上述类似，但**额外** 导致 LDAP 网络流量以较低（LDAP 客户端）级别被记录，并屏蔽绑定请求凭据。此设置可能导致过多的日志记录，应非常小心地使用。

`network_unsafe` 值导致 LDAP 网络流量以较低（LDAP 客户端）级别被记录，并且绑定请求凭据（如密码）会被写入日志；此模式不得在生产环境中使用，否则将违反几乎所有广泛采用的安全策略。然而，它对于开发和 QA 环境中的故障排除非常有用。

最后，`false` 值（默认值）会停用 LDAP 流量日志记录。

以下示例将 LDAP 日志记录级别设置为 `network`：
    
    
    auth_ldap.log = network  
    

经典配置格式中的相同示例：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        %% ...  
    
    
        {log, network}  
    
    
      ]}  
    
    
    ]  
    

### 授权查询绑定

对于身份验证，此插件会以其尝试进行身份验证的用户身份绑定到 LDAP 服务器。`other_bind` 设置控制如何为授权查询绑定，以及如何检索未提供密码即登录的用户的详细信息（例如使用 EXTERNAL 身份验证机制）。

接受的值为 `as_user`（以经过身份验证的用户身份绑定）或 `anon`（匿名绑定），或者通过两个选项 `other_bind.user_dn` 和 `other_bind.password` 提供，以使用指定的用户名和密码进行绑定。例如：
    
    
    auth_ldap.other_bind.user_dn = a-username  
    
    
    auth_ldap.other_bind.password = a-password  
    

使用经典配置格式：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        {other_bind, {"a-username", "a-password"}}  
    
    
      ]}  
    
    
    ].  
    

请注意，当用户在未提供密码的情况下连接时，无法使用默认的 `as_user` 配置。在这种情况下，请使用 `auth_ldap.other_bind.user_dn` 和 `auth_ldap.other_bind.password` 或 `anon` 选项。

`auth_ldap.other_bind` 的默认值为 `as_user`。

### 组成员资格查找

该插件支持多种组成员资格查找查询。`group_lookup_base` 设置控制将使用哪个基础 DN 来搜索嵌套组。它仅由 `{in_group_nested, ...}` 查询使用。有关更多信息，请参阅查询部分。

在以下示例中，`ou=groups,dc=example,dc=com` 是包含所有组的目录。注意，它使用了经典配置格式：
    
    
    [  
    
    
      {rabbitmq_auth_backend_ldap, [  
    
    
        %% ...  
    
    
        {group_lookup_base, "ou=groups,dc=example,dc=com"}  
    
    
      ]}  
    
    
    ]  
    

默认值为 `'none'`。

## 配置授权

### RabbitMQ 权限模型如何映射到 LDAP

RabbitMQ 权限模型与 LDAP 的权限模型不同。此外，LDAP 模式的使用方式因公司而异。因此，需要一种定义 RabbitMQ 授权功能使用哪些 LDAP 请求的机制。授权由四个可配置查询控制：

  * `rabbitmq_auth_backend_ldap.vhost_access_query`
  * `rabbitmq_auth_backend_ldap.resource_access_query`
  * `rabbitmq_auth_backend_ldap.topic_access_query`
  * `rabbitmq_auth_backend_ldap.tag_queries`



每个查询都定义了一个查询，该查询将确定用户是否具有 vhost 访问权限、是否具有资源（例如交换机、队列、绑定）的访问权限以及拥有哪些 标签。

注意较长的 `rabbitmq_auth_backend_ldap` 前缀。查询使用以 Erlang 术语（数据结构）表达的领域特定语言编写，因此它们只能使用 高级配置格式进行定义。

### 查询及其类型

上面提到的每个查询都在不同的授权阶段使用，并且必须求值为 `true` 或 `false`。特定的查询类型（表达式，例如值比较或组成员资格检查）将在本指南后面介绍。

查询可以是多种类型之一。每种类型代表一个布尔表达式或函数：比较、字符串匹配、对象存在性检查、组成员资格检查等。查询可以使用布尔运算符进行嵌套和组合。

默认值（表达式）可在下表中找到：

查询| 目的| 默认表达式  
---|---|---  
`rabbitmq_auth_backend_ldap.vhost_access_query`| 验证用户是否被允许访问虚拟主机| `{constant, true}`  
`rabbitmq_auth_backend_ldap.resource_access_query`| 验证用户是否被允许访问资源（队列、交换机等）| `{constant, true}`  
`rabbitmq_auth_backend_ldap.topic_access_query`| 验证用户是否被允许发布到主题| `{constant, true}`  
`rabbitmq_auth_backend_ldap.tag_queries`| 检查众所周知的标签是否适用于用户| `[{administrator, {constant, false}}]`  
  
这意味着所有用户都被授予访问所有 vhost 中所有对象的权限，但他们不是系统管理员。

所有接受字符串作为参数的查询类型都支持字符串替换，其中可以替换与正在进行的查询相关的变量。每个查询支持不同的变量。

`vhost_access_query` 支持：

  * `${username}`: 身份验证时提供的用户名
  * `${user_dn}`: 用户可分辨名称
  * `${vhost}`: 我们正在查询访问权限的虚拟主机



`resource_access_query` 支持：

  * `${username}`: 身份验证时提供的用户名
  * `${user_dn}`: 用户可分辨名称
  * `${vhost}`: 资源所在的虚拟主机
  * `${resource}`: 资源类型的“exchange”或“queue”之一
  * `${name}`: 资源名称
  * `${permission}`: 正在请求的资源访问类型的“configure”、“write”或“read”之一



`tag_queries` 支持：

  * `${username}`: 身份验证时提供的用户名
  * `${user_dn}`: 用户可分辨名称
  * `${vhost}`: **虚拟主机信息并非在所有场景中都可用** 。它可用于附加上下文，例如对应用程序或用户进行分组



`topic_access_query` 支持：

  * `${username}`: 身份验证时提供的用户名
  * `${user_dn}`: 用户可分辨名称
  * `${vhost}`: 资源所在的虚拟主机
  * `${resource}`: 在此情况下始终为“topic”
  * `${name}`: 资源名称
  * `${permission}`: “write”（发布）或“read”（消费，用于主题交换机绑定队列和交换机到交换机绑定的读取）之一
  * `${routing_key}`: 已发布消息的路由键（“write”权限）或主题交换机到队列/交换机绑定的路由键（“read”权限）



最后，如果身份验证时提供的用户名格式为 `Domain\User`（在某些 Active Directory 环境中即是如此），则上述每个查询都将提供两个 _额外_ 变量：

  * `${ad_domain}` \- `Domain\User` 的域名部分
  * `${ad_user}` \- `Domain\User` 的用户部分



资源访问的 configure、write 和 read 术语与内置 RabbitMQ 权限系统中的含义相同，请参见 ./access-control。有关 `topic_access_query`，另请参阅 主题授权。

在初步熟悉查询 DSL 时，开启上面记录的 `log` 配置参数会有所帮助。这将导致 LDAP 插件将其实施的查询及其做出的决策的相当详细的描述写入 RabbitMQ 日志中。

### 虚拟主机访问

`rabbitmq_auth_backend_ldap.vhost_access_query` 是用于控制虚拟主机访问的查询。如果查询求值为 `true`，则授予访问权限。

请注意，在用户可以访问虚拟主机之前，必须先在 RabbitMQ 中创建该虚拟主机；与用户和权限不同，虚拟主机无法完全存在于 LDAP 中。

### 用户标签

`tag_queries` 由一个将标签名称映射到执行查询的键值映射组成，用于确定用户是否拥有该标签。必须列出用户应拥有的所有标签的查询。

## 授权查询参考

### 常量查询
    
    
    {constant, Bool}  
    

这将始终返回 true 或 false，无条件授予或拒绝访问。示例：
    
    
    {tag_queries, [{administrator, {constant, false}},  
    
    
     {management,    {constant, true}}]}  
    

这授予所有用户使用管理插件的能力，但使他们中没有任何人成为管理员。

### 存在性查询
    
    
    {exists, Pattern}  
    

这将把变量代入模式中，如果存在具有所得 DN 的对象，则返回 true。示例：
    
    
    {vhost_access_query, {exists, "ou=${vhost},ou=vhosts,dc=example,dc=com"}}  
    

这授予所有用户访问作为 `ou=vhosts,dc=example,dc=com` 内组织单位存在的所有虚拟主机的权限。

### 组内查询
    
    
    {in_group, Pattern}  
    
    
    
    {in_group, Pattern, AttributeName}  
    

与存在性查询一样，将参数代入模式以查找对象。但是，如果登录用户是成员，此查询返回 true；检查 `member` 属性或任何命名属性。示例：
    
    
    {vhost_access_query, {in_group, "cn=${vhost}-users,ou=vhosts,dc=example,dc=com"}}  
    

当用户被列为 `ou=vhosts,dc=example,dc=com` 内命名适当的对象（例如 `groupOfNames`）的 `member` 属性时，这授予对虚拟主机的访问权限。

### 嵌套组内查询
    
    
    {in_group_nested, Pattern}  
    
    
    
    {in_group_nested, Pattern, AttributeName}  
    
    
    
    {in_group_nested, Pattern, AttributeName, Scope}  
    

类似于 `in_group` 查询，但也遍历组层次结构，例如，如果登录用户是作为另一个组的成员的组的成员。成员资格根据 `member` 属性或任何命名属性进行检查。组在 `group_lookup_base` 配置键定义的 DN 中搜索，如果前者为 `none`，则使用 `dn_lookup_base` 变量。如果两个查找基础变量都设置为 `none`，查询将始终返回 `false`。搜索范围可以设置为 `subtree` 或 `single_level`。

  * `subtree` 搜索查找基础下包含的所有对象。
  * `single_level` 搜索直接包含在查找基础内的组。



范围的默认值为 `subtree`。查询正在执行从用户向上到目标组的深度搜索。搜索过程将检测并跳过循环路径。如果用户是许多组的成员，而这些组又是许多组的成员，此查询可能会消耗时间和内存。在可能的情况下，建议使用简单的 `{in_group, ...}` 查询：嵌套组可能很难推理。示例：
    
    
    [  
    
    
      {group_lookup_base, "ou=groups,dc=example,dc=com"},  
    
    
      {vhost_access_query, {in_group_nested, "cn=${vhost}-groups,ou=groups,dc=example,dc=com", "member", single_level}}  
    
    
    ]  
    

当用户是 `ou=groups,dc=example,dc=com` 目录中定义的由 `member` 属性值构成的组层次结构的成员时，这授予对虚拟主机的访问权限。

### For 查询
    
    
    {for, [{Name, Value, SubQuery}, ...]}  
    

这允许您拆分查询并使用不同的子查询处理不同的情况。

选项应为三元组列表，每个元组包含名称、值和子查询。名称是变量的名称（即进入 `${}` 替换的内容）。值是该变量的可能值。

请注意，这些值属于不同的 Erlang 类型；`resource` 和 `permission` 具有原子值（例如 `resource` 可以是 `exchange`），而其他键具有二进制值（例如 `name` 可能是 `<<"amq.fanout">>`）。

示例
    
    
    {resource_access_query,  
    
    
     {for, [{resource, exchange, {for, [{permission, configure,  
    
    
                                         {in_group, "cn=wheel,dc=example,dc=com"}  
    
    
                                        },  
    
    
                                        {permission, write, {constant, true}},  
    
    
                                        {permission, read,  {constant, true}}  
    
    
                                       ]}},  
    
    
                                       {resource, queue,    {constant, true}}]}}  
    

这允许 `wheel` 组成员声明和删除交换机，并允许所有用户执行其他所有操作。

### 布尔查询
    
    
    {'not', SubQuery}  
    
    
    
    {'and', [SubQuery1, SubQuery2, SubQuery3, ...]}  
    
    
    
    {'or', [SubQuery1, SubQuery2, SubQuery3, ...]}  
    

'and' 和 'or' 查询各自接受任意长度的子查询列表，如果所有或任何子查询分别求值为 true，则返回 true。

注意，'and'、'or' 和 'not' 是 Erlang 中的保留字，因此关键字需要在配置文件中用单引号引起来，如上所示。示例：
    
    
    {resource_access_query,  
    
    
     {'or',  
    
    
      [{'and',  
    
    
        [{equals, "${name}", "test1"},  
    
    
         {equals, "${username}", "user1"}]},  
    
    
       {'and',  
    
    
        [{equals, "${name}", "test2"},  
    
    
         {'not', {equals, "${username}", "user1"}}]}  
    
    
      ]}}  
    

此示例授予“user1”对名为“test1”的对象的完全访问权限，并授予除“user1”之外的所有人对“test2”的访问权限。

### 相等查询
    
    
    {equals, StringSubQuery1, StringSubQuery2}  
    

接受两个字符串，并检查一个是否与另一个匹配。请注意，两个字符串依次是子查询（属于下面的 `string` 和 `attribute` 类型）。

为了将字符串替换变量之一的值与常量、属性值等进行比较，这很有用。示例：
    
    
    {resource_access_query,  
    
    
     {for, [{permission, configure, {equals, {attribute, "${user_dn}", "description"},  
    
    
                                             {string, "can-declare-${resource}s"}  
    
    
                                    }  
    
    
            },  
    
    
            {permission, write, {constant, true}},  
    
    
            {permission, read,  {constant, true}}  
    
    
           ]  
    
    
    }  
    

这根据用户描述字段中是否存在字符串“can-declare-exchanges”和“can-declare-queues”来授予声明和删除交换机和队列的权限，并授予所有人写入和读取交换机的权限。

### 匹配查询
    
    
    {match, StringSubQuery, RESubQuery}  
    

接受一个字符串和一个正则表达式，并检查一个是否与另一个匹配。请注意，字符串和正则表达式依次是子查询（属于下面的 `string` 和 `attribute` 类型）。示例：
    
    
    {resource_access_query, {match, {string, "${name}"},  
    
    
                          {string, "^${username}-"}}  
    
    
    }  
    

这允许用户配置、读取和写入任何名称以其自己的用户名后跟连字符开头的对象。

### 字符串子查询
    
    
    {string, Pattern}  
    

只需将参数代入字符串。由于此操作返回字符串而不是布尔值，因此应在 `match` 或 `equals` 查询中使用它。请参阅上面的示例。作为简写，您可以使用普通字符串而不是 `{string, Pattern}`。

### 属性子查询
    
    
    {attribute, DNPattern, AttributeName}  
    

返回从 LDAP 检索的对象的属性值。由于此操作返回字符串而不是布尔值，因此应在 `match` 或 `equals` 查询中使用它。请参阅上面的示例。

## 示例配置

总结一下，这是一个示例配置。它同时使用了 标准配置 和 高级配置 文件。这使得所有用户都能访问管理插件，但没有一个成为管理员。对虚拟主机的访问权限由每个虚拟主机的组内成员资格控制。只有 `admin` 成员可以声明、删除或绑定交换机和队列，但所有用户都可以发布到交换机并从队列声明。发布到主题类型交换机仅限于路由键以“a”开头的消息，消费主题不受限制（主题授权）。

标准配置 (rabbitmq.conf) 用于配置身份验证后端和多个 LDAP 插件参数。
    
    
    auth_backends.1 = ldap  
    
    
      
    
    
    auth_ldap.servers.1  = my-ldap-server  
    
    
    auth_ldap.user_dn_pattern = cn=${username},ou=People,dc=example,dc=com  
    
    
    auth_ldap.use_ssl    = false  
    
    
    auth_ldap.port       = 389  
    
    
    auth_ldap.log        = false  
    

高级配置用于定义 LDAP 查询。
    
    
    [{rabbitmq_auth_backend_ldap,[  
    
    
        {vhost_access_query,    {in_group,  
    
    
                                  "ou=${vhost}-users,ou=vhosts,dc=example,dc=com"}},  
    
    
         {resource_access_query,  
    
    
          {for, [{permission, configure, {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                 {permission, write,  
    
    
                  {for, [{resource, queue,    {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                         {resource, exchange, {constant, true}}]}},  
    
    
                 {permission, read,  
    
    
                  {for, [{resource, exchange, {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                         {resource, queue,    {constant, true}}]}}  
    
    
                ]  
    
    
          }},  
    
    
         {topic_access_query,  
    
    
          {for, [{permission, write, {match, {string, "${routing_key}"}, {string, "^a"}}},  
    
    
                 {permission, read,  {constant, true}}  
    
    
                ]  
    
    
          }},  
    
    
         {tag_queries,           [{administrator, {constant, false}},  
    
    
                                  {management,    {constant, true}}]}  
    
    
    ]}].  
    

或者，您可以使用 经典配置格式 在单个文件中配置所有内容。
    
    
    [  
    
    
      {rabbit, [{auth_backends, [rabbit_auth_backend_ldap]}]},  
    
    
      {rabbitmq_auth_backend_ldap,  
    
    
       [ {servers,               ["my-ldap-server"]},  
    
    
         {user_dn_pattern,       "cn=${username},ou=People,dc=example,dc=com"},  
    
    
         {use_ssl,               false},  
    
    
         {port,                  389},  
    
    
         {log,                   false},  
    
    
         {vhost_access_query,    {in_group,  
    
    
                                  "ou=${vhost}-users,ou=vhosts,dc=example,dc=com"}},  
    
    
         {resource_access_query,  
    
    
          {for, [{permission, configure, {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                 {permission, write,  
    
    
                  {for, [{resource, queue,    {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                         {resource, exchange, {constant, true}}]}},  
    
    
                 {permission, read,  
    
    
                  {for, [{resource, exchange, {in_group, "cn=admin,dc=example,dc=com"}},  
    
    
                         {resource, queue,    {constant, true}}]}}  
    
    
                ]  
    
    
          }},  
    
    
         {topic_access_query,  
    
    
          {for, [{permission, write, {match, {string, "${routing_key}"}, {string, "^a"}}},  
    
    
                 {permission, read,  {constant, true}}  
    
    
                ]  
    
    
         }},  
    
    
         {tag_queries,           [{administrator, {constant, false}},  
    
    
                                  {management,    {constant, true}}]}  
    
    
       ]  
    
    
      }  
    
    
    ].  
    

## 故障排除

使用 LDAP 进行身份验证和/或授权会向系统中引入另一个活动部件。由于 LDAP 服务器是通过网络访问的，因此 网络故障排除 和 TLS 故障排除 指南中涵盖的某些主题适用于 LDAP。

为了对身份验证和授权阶段执行的 LDAP 操作进行故障排除，强烈建议 启用 LDAP 流量日志记录。

ldapsearch 是一个随 LDAP 提供的命令行工具，可以针对 OpenLDAP 安装执行任意 LDAP 查询。这在排除复杂的授权查询故障时很有用。ldp.exe 是 Active Directory 的对应工具。

## LDAP 代理

LDAP 代理可用于修改此插件执行的 LDAP 请求。ldaptor 是一个可用于在代理中构建自定义逻辑的库。

操作员应认识到，使用代理会使 LDAP 请求的 故障排除 变得更加困难。
