---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/clustering-ssl
---

# 使用 TLS 保护集群（节点间）和 CLI 工具通信

## 概述

RabbitMQ 节点接受来自 客户端 的连接，同时也接受来自 对等集群节点 和 CLI 工具 的连接。

主要的 TLS 指南和 TLS 排错 指南介绍了如何使用 TLS 保护客户端连接。您可能希望为另外两种连接添加一层加密和额外的身份验证层。本指南将介绍如何实现这一点。

切换节点间和 CLI 工具通信需要配置几个 运行时 标志。它们为节点提供 CA 证书包和证书/密钥对。CLI 工具也必须配置为使用证书/密钥对，因为启用 TLS 的节点不会接受来自 CLI 工具和对等节点的未加密连接。

本指南假设读者熟悉 TLS 基础知识 以及主 TLS 指南中介绍的 对等验证（身份验证）。

它还假设您已经为每个集群节点和使用 CLI 工具的每台主机生成了 CA 证书包和证书/密钥对。在生产环境中，这些证书通常由运维人员或部署工具生成。对于开发和实验，可以使用 OpenSSL 和 Python 进行 快速生成。

本指南将引用三个文件

  * `ca_certificate.pem`：证书颁发机构 (CA) 证书包
  * `server_certificate.pem`：将由配置的节点（和/或 CLI 工具）使用的证书（公钥）
  * `server_key.pem`：将由配置的节点（和/或 CLI 工具）使用的私钥



在开始之前，请确保已准备好这些文件。

## 基础知识

将节点配置为通过启用 TLS 的连接进行通信涉及几个步骤。对于 受支持的 Erlang 版本，有两种实现方法。

所有受支持操作系统上的步骤都非常相似。以下示例使用选项卡来显示 bash（Linux、macOS）和 PowerShell/batch（Windows）变体。

策略一 包括以下步骤

  * 使用运行时标志 `-proto_dist inet_tls` 告知节点使用加密的节点间连接
  * 将节点使用的公钥和私钥合并为一个文件
  * 使用另一个运行时标志 `-ssl_dist_opt server_certfile` 告知节点其证书和私钥的位置
  * 使用其他 `-ssl_dist_opt` 选项告知节点所需的任何其他 TLS 设置，例如：`-ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true` 以启用 安全重协商



策略二 非常相似，但不是指定一组运行时标志，而是可以在类似于 RabbitMQ 的 advanced.config 文件 的文件中指定这些选项，并让运行时指向该文件。因此，步骤如下

  * 使用运行时标志 `-proto_dist inet_tls` 告知节点使用加密的节点间连接
  * 部署一个节点间 TLS 设置文件，其中包含有关证书/密钥对位置、CA 包位置、所用 TLS 设置等信息
  * 使用另一个运行时标志 `-ssl_dist_optfile` 告知节点其节点间 TLS 设置文件的位置



我们鼓励运维人员选择最适合其首选部署工具的策略。

对于这两个选项，环境变量都用于将这些选项传递给运行时。如 配置指南 中所述，最好使用 `rabbitmq-env.conf` 来完成此操作。

一旦节点配置了 TLS 节点间连接，`rabbitmqctl` 和 `rabbitmq-diagnostics` 等 CLI 工具也必须使用 TLS 与节点通信。普通的 TCP 连接将会失败。

### 部署节点间 TLS

一旦证书/密钥对文件和配置就绪，就可以启动新节点。请注意，可能需要先停止节点，然后部署文件和配置，最后再启动节点。这是因为配置为使用 TLS 的 CLI 工具将无法连接到不期望 TLS 启用 CLI 工具连接的节点。

为了使节点和 CLI 工具能够成功执行 TLS 握手和对等验证，必须遵循相同的 对等验证 示例，即其他节点和 CLI 工具使用的证书/密钥对必须由与初始节点相同的证书颁发机构签名，或者是所有集群节点都信任的不同 CA。

这与 客户端和插件 TLS 连接的对等验证工作方式 没有区别。

可以为所有节点和 CLI 工具重用单个证书/密钥对。该证书还可以使用通配符使用者可选名称 (SAN) 或公用名 (CN)，例如 `*.rabbitmq.example.local`，以匹配集群中的每个主机名。

## 策略一（使用单个标志）

### 合并证书和私钥

本指南中涵盖的第一种策略要求将节点的公钥和私钥合并为一个文件。我们称之为合并密钥文件。要合并它们，只需将私钥文件（在下例中为 `server_key.pem`）从新行开始连接到公钥文件（`server_certificate.pem`）的末尾即可

  * bash
  * PowerShell


    
    
    cat server_certificate.pem server_key.pem > combined_keys.pem  
    
    
    
    Get-Content server_certificate.pem, server_key.pem | Set-Content combined_keys.pem  
    

这可以使用文本编辑器完成，而不仅仅是命令行工具。

### 配置节点间 TLS 的各个运行时标志

假设上面部分中的合并密钥文件已准备就绪，接下来我们推断 Erlang TLS 库路径并在环境配置文件中导出 `ERL_SSL_PATH` 以指向它

  * bash
  * PowerShell


    
    
    # These commands ensure that `ERL_SSL_PATH` is the first line in  
    
    
    # /etc/rabbitmq/rabbitmq-env.conf and will preserve the existing  
    
    
    # contents of that file if it already exists  
    
    
      
    
    
    erl -noinput -eval 'io:format("ERL_SSL_PATH=~s~n", [filename:dirname(code:which(inet_tls_dist))])' -s init stop > /tmp/ssl-path.txt  
    
    
    cat /tmp/ssl-path.txt /etc/rabbitmq/rabbitmq-env.conf > /tmp/new-rabbitmq-env.conf  
    
    
    mv -f /tmp/new-rabbitmq-env.conf /etc/rabbitmq/rabbitmq-env.conf  
    
    
    
    erl -noinput -eval 'io:format("ERL_SSL_PATH=~s~n", [filename:dirname(code:which(inet_tls_dist))])' -s init stop > ssl-path.txt  
    

在带有 `cmd.exe` 的 Windows 上，请改用带转义内引号的双引号
    
    
    erl -noinput -eval "io:format(""ERL_SSL_PATH=~s~n"", [filename:dirname(code:which(inet_tls_dist))])" -s init stop > ssl-path.txt  
    

这使得节点能够从该路径加载模块 `inet_tls_dist`，该模块用于加密的节点间通信。

第二步是使用 `-proto_dist inet_tls` 运行时标志告知运行时使用该模块。与其他运行时标志一样，`SERVER_ADDITIONAL_ERL_ARGS` 是传递它们最方便且兼容的方式。

  * bash
  * PowerShell



请注意，这里**必须** 使用双引号，因为环境变量的值是多行的
    
    
    # -pa $ERL_SSL_PATH prepends the directory ERL_SSL_PATH points at to the code path  
    
    
    # -proto_dist inet_tls tells the runtime to encrypt inter-node communication  
    
    
    # -ssl_dist_opt server_certfile /path/to/combined_keys.pem tells the runtime  
    
    
    #                               where to find the combined certificate/key file  
    
    
    # -ssl_dist_opt server_password password   required if the private key is encrypted  
    
    
    #  
    
    
    SERVER_ADDITIONAL_ERL_ARGS="-pa $ERL_SSL_PATH \  
    
    
      -proto_dist inet_tls \  
    
    
      -ssl_dist_opt server_certfile /path/to/combined_keys.pem \  
    
    
      -ssl_dist_opt server_password password  
    
    
    
    set SERVER_ADDITIONAL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_opt server_certfile C:/Path/To/combined_keys.pem ^  
    
    
        -ssl_dist_opt server_password password  
    

下一步是在前一个示例的基础上，为节点间 TLS 连接启用安全重协商。虽然这是可选的，但强烈建议这样做。同样的 `-ssl_dist_opt` 可用于启用更多 TLS 相关设置。本示例不再赘述

  * bash
  * PowerShell


    
    
    # -pa $ERL_SSL_PATH prepends the directory ERL_SSL_PATH points at to the code path  
    
    
    # -proto_dist inet_tls tells the runtime to encrypt inter-node communication  
    
    
    # -ssl_dist_opt server_certfile /path/to/combined_keys.pem tells the runtime  
    
    
    #                               where to find the combined certificate/key file  
    
    
    # -ssl_dist_opt server_password password   required if the private key is encrypted  
    
    
    # -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true enables an additional TLS setting: secure renegotiation  
    
    
    SERVER_ADDITIONAL_ERL_ARGS="-pa $ERL_SSL_PATH \  
    
    
      -proto_dist inet_tls \  
    
    
      -ssl_dist_opt server_certfile /path/to/combined_keys.pem \  
    
    
      -ssl_dist_opt server_password password \  
    
    
      -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true"  
    
    
    
    set SERVER_ADDITIONAL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_opt server_certfile C:/Path/To/combined_keys.pem ^  
    
    
        -ssl_dist_opt server_password password ^  
    
    
        -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true  
    

一旦节点配置了 TLS 节点间连接，`rabbitmqctl` 和 `rabbitmq-diagnostics` 等 CLI 工具也必须使用 TLS 与节点通信。普通的 TCP 连接将会失败。

这与上面的示例使用 `SERVER_ADDITIONAL_ERL_ARGS` 的做法非常相似，但这次环境变量是 `RABBITMQ_CTL_ERL_ARGS`。它控制 CLI 工具使用的运行时标志。

以下是完整的环境配置文件

  * bash
  * PowerShell



文件为 `/etc/rabbitmq/rabbitmq-env.conf`
    
    
    # IMPORTANT:  
    
    
    # the following path is system dependent (will  
    
    
    # change depending on the Erlang version, distribution,  
    
    
    # and installation method used). Please double check it before proceeding!  
    
    
    ERL_SSL_PATH="/usr/lib64/erlang/lib/ssl-9.4/ebin"  
    
    
      
    
    
    # -pa $ERL_SSL_PATH prepends the directory ERL_SSL_PATH points at to the code path  
    
    
    # -proto_dist inet_tls tells the runtime to encrypt inter-node communication  
    
    
    # -ssl_dist_opt server_certfile /path/to/combined_keys.pem tells the runtime  
    
    
    #                               where to find the combined certificate/key file  
    
    
    # -ssl_dist_opt server_password password   required if the private key is encrypted  
    
    
    # -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true enables an additional TLS setting: secure renegotiation  
    
    
    SERVER_ADDITIONAL_ERL_ARGS="-pa $ERL_SSL_PATH \  
    
    
      -proto_dist inet_tls \  
    
    
      -ssl_dist_opt server_certfile /path/to/combined_keys.pem \  
    
    
      -ssl_dist_opt server_password password \  
    
    
      -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true"  
    
    
      
    
    
    # Same settings as above but for CLI tools  
    
    
    RABBITMQ_CTL_ERL_ARGS="-pa $ERL_SSL_PATH \  
    
    
      -proto_dist inet_tls \  
    
    
      -ssl_dist_opt server_certfile /path/to/combined_keys.pem \  
    
    
      -ssl_dist_opt server_password password \  
    
    
      -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true"  
    

文件为 `rabbitmq-env-conf.bat`，保存在 `%AppData%\RabbitMQ` 中
    
    
    @echo off  
    
    
    rem IMPORTANT:  
    
    
    rem the following path is system dependent and will vary between Erlang versions  
    
    
    rem and installation paths  
    
    
    set SSL_PATH="C:/Program Files/erl10.0.1/lib/ssl-9.0/ebin"  
    
    
      
    
    
    set SERVER_ADDITIONAL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_opt server_certfile C:/Path/To/combined_keys.pem ^  
    
    
        -ssl_dist_opt server_password password ^  
    
    
        -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true  
    
    
      
    
    
    rem Same as above but for CLI tools.  
    
    
    rem In environment config files, the RABBITMQ_ prefix is dropped  
    
    
    set CTL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_opt server_certfile C:/Path/To/combined_keys.pem ^  
    
    
        -ssl_dist_opt server_password password ^  
    
    
        -ssl_dist_opt server_secure_renegotiate true client_secure_renegotiate true  
    

## 策略二（使用单个 TLS 选项文件）

### 为节点间 TLS 使用单独的设置文件

现代 Erlang 版本支持运行时标志 `-ssl_dist_optfile`，可用于使用单个文件配置节点间通信的 TLS。这简化了在命令行上传递的参数。

以下是使用此设置的完整环境配置文件。请注意，`-ssl_dist_optfile` 文件的名称并不重要，但它必须存储在有效 `rabbitmq` 用户可读取的位置

  * bash
  * PowerShell



文件为 `/etc/rabbitmq/rabbitmq-env.conf`
    
    
    # NOTE: the following path is system dependent and will change between Erlang  
    
    
    #       versions  
    
    
    ERL_SSL_PATH="/usr/lib64/erlang/lib/ssl-9.4/ebin"  
    
    
      
    
    
    # -pa $ERL_SSL_PATH prepends the directory ERL_SSL_PATH points at to the code path  
    
    
    # -proto_dist inet_tls tells the runtime to encrypt inter-node communication  
    
    
    # -ssl_dist_optfile tells the runtime where to find its inter-node TLS configuration file  
    
    
    SERVER_ADDITIONAL_ERL_ARGS="-pa $ERL_SSL_PATH  
    
    
      -proto_dist inet_tls  
    
    
      -ssl_dist_optfile /etc/rabbitmq/inter_node_tls.config"  
    
    
      
    
    
    RABBITMQ_CTL_ERL_ARGS="-pa $ERL_SSL_PATH  
    
    
      -proto_dist inet_tls  
    
    
      -ssl_dist_optfile /etc/rabbitmq/inter_node_tls.config"  
    

文件为 `rabbitmq-env-conf.bat`，保存在 `%AppData%\RabbitMQ` 中
    
    
    @echo off  
    
    
    rem NOTE: the following path is system dependent and will vary between Erlang versions  
    
    
    set SSL_PATH="C:/Program Files/erl10.0.1/lib/ssl-9.0/ebin"  
    
    
      
    
    
    set SERVER_ADDITIONAL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_optfile C:/Users/rmq_user/AppData/Roaming/RabbitMQ/inter_node_tls.config  
    
    
      
    
    
    rem In environment config files, the RABBITMQ_ prefix is dropped  
    
    
    set CTL_ERL_ARGS=-pa %SSL_PATH% ^  
    
    
        -proto_dist inet_tls ^  
    
    
        -ssl_dist_optfile C:/Users/rmq_user/AppData/Roaming/RabbitMQ/inter_node_tls.config  
    

这是一个使用单独的服务器证书和私钥文件、启用 对等验证 并要求对等方出示证书的 `inter_node_tls.config` 文件示例。在 Windows 上，请使用正斜杠 (`/`) 作为目录分隔符
    
    
    %% coding: utf-8  
    
    
    %% This directive tells the Erlang preprocessor to interpret this file  
    
    
    %% as UTF-8, which is required if any values contain non-ASCII characters  
    
    
    %% (for example, in the password field).  
    
    
    [  
    
    
      {server, [  
    
    
        {cacertfile, "/full/path/to/ca_certificate.pem"},  
    
    
        {certfile,   "/full/path/to/server_certificate.pem"},  
    
    
        {keyfile,    "/full/path/to/server_key.pem"},  
    
    
        {password,   "password-if-keyfile-is-encrypted"},  
    
    
        {secure_renegotiate, true},  
    
    
        {verify, verify_peer},  
    
    
        {fail_if_no_peer_cert, true}  
    
    
      ]},  
    
    
      {client, [  
    
    
        {cacertfile, "/full/path/to/ca_certificate.pem"},  
    
    
        {certfile,   "/full/path/to/client_certificate.pem"},  
    
    
        {keyfile,    "/full/path/to/client_key.pem"},  
    
    
        {password,   "password-if-keyfile-is-encrypted"},  
    
    
        {secure_renegotiate, true},  
    
    
        {verify, verify_peer}  
    
    
      ]}  
    
    
    ].  
    

这些选项在 Erlang/OTP 文档 中有进一步记录。
