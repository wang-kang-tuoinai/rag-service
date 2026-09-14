---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/troubleshooting-ssl
---

# 排查启用了 TLS 的连接

## 概述

本指南涵盖了一些有助于诊断 TLS 连接问题和错误（TLS 警报）的方法和工具。它作为RabbitMQ 中的 TLS 主指南的补充。其策略是在排除过程中使用替代的 TLS 实现来测试所需的组件，从而识别出问题的终端（客户端或服务器）。

请注意，如果问题是由两个特定组件之间的交互引起的，此过程并不能保证能识别出问题。

本指南建议的步骤如下：

  * 验证 有效配置
  * 验证节点是否 正在监听 TLS 连接
  * 验证 文件权限
  * 验证证书和私钥文件使用的 文件格式
  * 验证 Erlang/OTP 中的 TLS 支持
  * 验证证书/密钥对，并 使用 OpenSSL 命令行工具 通过替代的 TLS 客户端或服务器进行测试
  * 验证可用和已配置的 密码套件 以及证书密钥用法选项
  * 验证客户端连接 使用 TLS 终止代理
  * 最后，再次针对真实的服务器连接测试真实的客户端连接



在测试 RabbitMQ 节点和/或真实的 RabbitMQ 客户端时，检查服务器和客户端的 日志 非常重要。

## 检查节点的有效配置

设置带有 TLS 的 RabbitMQ 节点涉及修改配置。在执行任何其他 TLS 排查步骤之前，验证配置文件位置和有效配置（即节点是否已成功加载配置）非常重要。详见 配置指南。

## 检查 TLS 监听器（端口）

此步骤检查代理是否正在 预期的端口 上进行监听，例如 AMQP 0-9-1 和 1.0 的 5671 端口，MQTT 的 8883 端口等。

要验证节点上是否已启用 TLS，请使用 `[rabbitmq-diagnostics](./man/rabbitmq-diagnostics.8) listeners` 或 `[rabbitmq-diagnostics](./man/rabbitmq-diagnostics.8) status` 中的 `listeners` 部分。

监听器部分看起来会像这样
    
    
    Interface: [::], port: 25672, protocol: clustering, purpose: inter-node and CLI tool communication  
    
    
    Interface: [::], port: 5672, protocol: amqp, purpose: AMQP 0-9-1 and AMQP 1.0  
    
    
    Interface: [::], port: 5671, protocol: amqp/ssl, purpose: AMQP 0-9-1 and AMQP 1.0 over TLS  
    
    
    Interface: [::], port: 15672, protocol: http, purpose: HTTP API  
    
    
    Interface: [::], port: 15671, protocol: https, purpose: HTTP API over TLS (HTTPS)  
    
    
    Interface: [::], port: 1883, protocol: mqtt, purpose: MQTT  
    

在上面的示例中，节点上有 6 个 TCP 监听器。其中两个接受 TLS 加密连接

  * 端口 `25672` 上的节点间通信和 CLI 工具通信
  * 端口 `5672` 上用于非 TLS 连接的 AMQP 0-9-1（及 1.0，如果已启用）监听器
  * 端口 `5671` 上用于 TLS 加密连接的 AMQP 0-9-1（及 1.0，如果已启用）监听器
  * 端口 15672 (HTTP) 和 15671 (HTTPS) 上的 HTTP API 监听器
  * 用于非 TLS 连接的 MQTT 监听器 1883



如果上述步骤不可行，检查节点的 日志文件 是一种可行的替代方案。它应该包含一条关于启用 TLS 监听器的条目，看起来如下所示
    
    
    2018-09-02 14:24:58.611 [info] <0.664.0> started TCP listener on [::]:5672  
    
    
    2018-09-02 14:24:58.614 [info] <0.680.0> started SSL listener on [::]:5671  
    

如果节点已配置为使用 TLS，但没有记录类似上述的消息，则可能是配置文件放置在了错误的位置且未被代理读取，或者在更改配置文件后未重启节点。有关配置文件验证的详细信息，请参阅 配置页面。

可以使用 `lsof` 和 `netstat` 等工具来验证节点正在监听哪些端口，详见 网络排查 指南。

## 检查证书、私钥和 CA 包的文件权限

RabbitMQ 必须能够读取其配置的 CA 证书包、服务器证书和私钥。这些文件必须存在并具有适当的权限。权限不正确（例如文件由 `root` 或其他安装它们的超级用户账户所有）是 TLS 设置中非常常见的问题。

在 Linux、BSD 和 MacOS 上，目录权限也会影响节点读取文件的能力。

当证书或私钥文件不可读或不存在时，节点将无法接受 TLS 加密连接，或者 TLS 连接会直接挂起（行为因 Erlang/OTP 版本而异）。

当使用 新式配置格式 配置证书和私钥路径时，节点会在启动时检查文件是否存在，如果不存在则拒绝启动。

## 检查证书、私钥和 CA 包的文件格式

RabbitMQ 节点要求所有证书、私钥和 CA 证书包文件必须采用 PEM 格式。其他格式将不被接受。

其他格式的文件可以使用 OpenSSL CLI 工具 转换为 PEM 文件。

## 检查 Erlang 中的 TLS 支持

建立通往代理的 TLS 连接的另一个关键要求是代理本身支持 TLS。通过运行以下命令确认 Erlang VM 是否支持 TLS：
    
    
    rabbitmq-diagnostics --silent tls_versions  
    

或者在 Windows 上：
    
    
    rabbitmq-diagnostics.bat --silent tls_versions  
    

输出将如下所示：
    
    
    tlsv1.2  
    
    
    tlsv1.1  
    
    
    tlsv1  
    
    
    sslv3  
    

对于不提供 `rabbitmq-diagnostics tls_versions` 的版本，请使用：
    
    
    rabbitmqctl eval 'ssl:versions().'  
    

或者在 Windows 上：
    
    
    rabbitmqctl.bat eval 'ssl:versions().'  
    

这种情况下的输出将如下所示：
    
    
    [{ssl_app,"9.1"},  
    
    
     {supported,['tlsv1.2','tlsv1.1',tlsv1]},  
    
    
     {supported_dtls,['dtlsv1.2',dtlsv1]},  
    
    
     {available,['tlsv1.2','tlsv1.1',tlsv1,sslv3]},  
    
    
     {available_dtls,['dtlsv1.2',dtlsv1]}]  
    

如果报告了错误，请确认 Erlang/OTP 安装 包含了 TLS 支持。

还可以列出节点上可用的密码套件：
    
    
    rabbitmq-diagnostics cipher_suites --format openssl --silent  
    

或者在 Windows 上：
    
    
    rabbitmq-diagnostics.bat cipher_suites --format openssl --silent  
    

还可以检查本地 Erlang 运行时支持哪些 TLS 版本。为此，在命令行上运行 `erl`（Windows 上为 `werl.exe`）打开 Erlang shell 并输入：
    
    
    %% the trailing dot is significant!  
    
    
    ssl:versions().  
    

请注意，这将报告本地节点上（针对 `PATH` 中找到的运行时）支持的版本，这可能与所检查的 RabbitMQ 节点所使用的版本不同。

## 使用 OpenSSL 工具测试 TLS 连接

OpenSSL s_client 和 s_server 是常用的命令行工具，可用于测试 TLS 连接和证书/密钥对。它们通过针对替代的 TLS 客户端和服务器实现进行测试，帮助缩小问题范围。例如，如果某个 TLS 客户端可以成功连接 `s_server` 但不能连接 RabbitMQ 节点，则根本原因很可能在服务器端。同样，如果 `s_client` 客户端可以成功连接到 RabbitMQ 节点但另一个客户端不能，则应首先仔细检查客户端的设置。

下面的示例旨在通过在两个独立的 shell（终端窗口）中连接 `s_client` 客户端和 `s_server` 服务器，来确认证书和密钥可用于建立 TLS 连接。

该示例假设您拥有以下 证书和密钥文件（这些文件名由 tls-gen 使用）：

项目| 位置  
---|---  
CA 证书（公钥）| `ca_certificate.pem`  
服务器证书（公钥）| `server_certificate.pem`  
服务器私钥| `server_key.pem`  
客户端证书（公钥）| `client_certificate.pem`  
客户端私钥| `client_key.pem`  
  
在一个终端窗口或选项卡中执行以下命令：
    
    
    openssl s_server -accept 8443 \  
    
    
      -cert server_certificate.pem -key server_key.pem -CAfile ca_certificate.pem  
    

它将启动一个使用提供的 CA 证书包、服务器证书和私钥的 OpenSSL `s_server`。它将用于通过针对此示例服务器的测试 TLS 连接来置信验证证书。

在另一个终端窗口中，运行以下命令，将 `CN_NAME` 替换为证书中的预期主机名或 `CN` 名称：
    
    
    openssl s_client -connect localhost:8443 \  
    
    
      -cert client_certificate.pem -key client_key.pem -CAfile ca_certificate.pem \  
    
    
      -verify 8 -verify_hostname CN_NAME  
    

它将打开一个通往上述示例 TLS 服务器的新 TLS 连接。您可以省略 `-verify_hostname` 参数，但 OpenSSL 将不再执行该验证。

如果证书和密钥创建正确，两个选项卡中都将出现 TLS 连接输出。现在示例客户端和示例服务器之间已建立连接，类似于 `telnet`。

如果能够建立 信任链，第二个终端将显示验证确认，代码为 `0`：
    
    
    Verify return code: 0 (ok)  
    

正如命令行工具一样，非零代码表示某种错误。

如果报告了错误，请确认证书和密钥生成正确，并使用了匹配的证书/私钥对。此外，证书在生成时可以 限制其使用场景。这意味着旨在供客户端自我认证的证书将被服务器（如 RabbitMQ 节点）拒绝。

对于自签名证书适用的环境，我们建议使用 tls-gen 进行生成。

## 验证可用的密码套件

RabbitMQ 节点和客户端在 TLS 握手期间允许使用的 密码套件 可能受到限制。确保双方拥有共同的密码套件非常重要，否则握手将失败。

证书的密钥用法属性也会限制可以使用的密码套件。

请参阅主 TLS 指南中的 配置密码套件 和 公钥用法扩展 以了解更多信息。
    
    
    openssl ciphers -v  
    

将显示本地 OpenSSL 构建版本支持的所有密码套件。

## 尝试与 RabbitMQ 节点建立 TLS 连接

一旦 RabbitMQ 节点配置为在 TLS 端口上进行监听，就可以使用 OpenSSL `s_client` 来测试 TLS 连接的建立，这次是针对该节点。此检查可以在无需配置 RabbitMQ 客户端的情况下确定代理是否配置正确。该工具还可用于比较不同客户端的行为。该示例假设节点运行在 `localhost` 上，端口为 AMQP 0-9-1 和 AMQP 1.0 的默认 TLS 端口（5671）。
    
    
    openssl s_client -connect localhost:5671 -cert client_certificate.pem -key client_key.pem -CAfile ca_certificate.pem  
    

输出应与使用 8443 端口的情况类似。节点日志文件应该在连接建立时 包含一个新条目。
    
    
    2018-09-27 15:46:20 [info] <0.1082.0> accepting AMQP connection <0.1082.0> (127.0.0.1:50915 -> 127.0.0.1:5671)  
    
    
    2018-09-27 15:46:20 [info] <0.1082.0> connection <0.1082.0> (127.0.0.1:50915 -> 127.0.0.1:5671): user 'user' authenticated and granted access to vhost 'virtual_host'  
    

节点将期望客户端执行协议握手（AMQP 0-9-1、AMQP 1.0 等）。如果这种情况不在短时间内（大多数协议默认为 10 秒）发生，节点将关闭连接。

## 使用 Stunnel 验证客户端连接

stunnel 是一种可用于验证已启用 TLS 的客户端的工具。在此配置中，客户端将与 stunnel 建立安全连接，stunnel 会将解密后的数据传递到代理的“常规”端口（例如 AMQP 0-9-1 和 1.0 的 5672）。这提供了客户端 TLS 配置是否与代理 TLS 配置无关且正确的信心。

`stunnel` 是一种专门的代理。在此示例中，它将以守护进程模式运行在与代理相同的主机上。在接下来的讨论中，假设 stunnel 仅被临时使用。虽然也可以使用 stunnel 执行 TLS 终止，但这超出了本指南的范围。

在此示例中，`stunnel` 将连接到代理的未加密端口 (5672)，并在 5679 端口接受来自支持 TLS 的客户端的 TLS 连接。

参数通过名为 `stunnel.conf` 的配置文件传递。它包含以下内容：
    
    
    foreground = yes  
    
    
      
    
    
    [rabbit-amqp]  
    
    
    connect = localhost:5672  
    
    
    accept = 5679  
    
    
    cert = client/key-cert.pem  
    
    
    debug = 7  
    

`stunnel` 的启动方式如下：
    
    
    cat client_key.pem client_certificate.pem > client/key-cert.pem  
    
    
    stunnel stunnel.conf  
    

`stunnel` 需要证书及其对应的私钥。证书和私钥文件必须如上所示使用 `cat` 命令连接起来。`stunnel` 要求密钥不能受密码保护。现在，支持 TLS 的客户端应该能够连接到 5679 端口，任何 TLS 错误都会出现在启动 `stunnel` 的控制台上。

## 验证 RabbitMQ 客户端与 RabbitMQ 节点的连接

假设之前的步骤都没有产生错误，那么您可以放心地将测试过的启用 TLS 的客户端连接到代理的启用 TLS 的端口，确保先停止任何正在运行的 OpenSSL `s_server` 或 `stunnel` 实例。

## 证书链和验证深度

当使用 由中间 CA 签名 的客户端证书时，可能需要配置 RabbitMQ 服务器以使用更高的 验证深度。

验证深度不足将导致 TLS 对等方验证失败。

## 了解 TLS 连接日志错误

在之前的许多步骤中都会生成新的代理日志文件条目。这些条目以及控制台上命令的诊断输出应有助于识别 TLS 相关错误的原因。以下是记录中最常见的错误条目：

**记录的错误**| **解释**  
---|---  
包含 `{undef, [{crypto,hash,...` 的条目| 所使用的 Erlang/OTP 安装中缺少 `crypto` 模块或者它已过期。在 Debian、Ubuntu 和其他基于 Debian 的发行版上，这通常意味着未安装 erlang-ssl 包。  
包含 `{ssl_upgrade_error, ekeyfile}` 或 `{ssl_upgrade_error, ecertfile}` 的条目| 这意味着代理密钥文件或证书文件无效。确认密钥文件与证书匹配，且两者均为 PEM 格式。PEM 格式是一种带有可识别分隔符的可打印编码。证书将分别以 `-----BEGIN CERTIFICATE-----` 和 `-----END CERTIFICATE-----` 开头和结尾。同样，密钥文件也将分别以 `-----BEGIN RSA PRIVATE KEY-----` 和 `-----END RSA PRIVATE KEY-----` 开头和结尾。  
包含 `{ssl_upgrade_failure, ... certify ...}` 的条目| 此错误与客户端验证有关。客户端提供了无效证书或未提供证书。如果 `ssl_options` 将 `verify` 选项设置为 `verify_peer`，则尝试临时使用值 `verify_none`。确保客户端证书已正确生成，并且客户端提供了正确的证书。  
包含 `{ssl_upgrade_error, ...}` 的条目| 这是一个通用错误，可能有多种原因。确保您使用的是推荐的 Erlang 版本。  
包含 `{tls_alert,"bad record mac"}` 的条目| 服务器已尝试验证其接收到的数据片段的完整性，但检查失败。这可能是由于有问题的网络设备、客户端中非故意的套接字共享（例如由于使用了 `fork(2)`）或客户端的 TLS 实现中存在错误所致。
