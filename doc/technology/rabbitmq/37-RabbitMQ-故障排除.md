---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/troubleshooting
---

# 故障排查指南

## 概述

本指南概述了与 RabbitMQ 安装和消息系统故障排查相关的若干主题。

  * 监控与健康检查
  * 日志记录
  * 节点配置
  * 客户端连接
  * 客户端认证与授权
  * CLI 工具连接与认证
  * 运行时崩溃转储
  * 集群形成
  * 节点内存使用
  * 连接与连接泄漏
  * 通道与通道泄漏
  * TLS
  * LDAP
  * OAuth 2.0
  * 流量捕获



节点内存使用、指标与监控、TLS 等。

## 监控、指标、健康检查

生产系统故障排查的一个重要方面是监控和健康检查。它们收集可供检查和分析的数据，有助于识别和检测异常。

## 日志记录

日志是故障排查的另一个重要信息来源。单独的日志记录指南解释了在哪里查找日志文件、如何调整日志级别、存在哪些日志类别、如何利用日志文件检测连接生命周期事件等。

## 节点配置

配置指南包含一个关于定位配置文件的章节。

可以使用 `rabbitmqctl environment` 以及多个 rabbitmq-diagnostics 命令来检查有效的节点配置。

## CLI 工具连接与认证

CLI 工具指南解释了 CLI 工具如何向节点进行认证、什么是 Erlang cookie 文件，以及 CLI 工具在服务器节点上执行操作失败的最常见原因。

## 集群形成

集群形成指南包含一个故障排查章节。

## 内存使用分析

内存使用推理是专门针对该主题的指南。

## 网络与连接

网络故障排查是专门针对网络和连接主题的指南。

## 认证与授权

访问控制指南包含关于排查客户端认证和排查授权的章节。

## 运行时崩溃转储文件

当 Erlang 运行时系统异常退出时，会在 RabbitMQ 启动目录下写入一个名为 `erl_crash.dump` 的文件。该文件包含运行时在异常退出时的状态。终止原因可以在文件的前几行中找到，以 `Slogan` 开头，例如：
    
    
    head -n 3 ./erl_crash.dump  
    
    
    # => =erl_crash_dump:0.5  
    
    
    # => Sun Aug 25 00:57:34 2019  
    
    
    # => Slogan: Kernel pid terminated (application_controller) ({application_start_failure,rabbit,{{timeout_waiting_for_tables,[rabbit_user,rabbit_user_permission,rabbit_topic_permission,rabbit_vhost,rabbit_durable_r  
    

在这个特定示例中，口号（未捕获的异常消息）说明启动的节点在从对等节点同步架构元数据时超时，这很可能是因为它们没有在配置的时间窗口内上线。

为了更好地理解来自崩溃转储文件的 Erlang 运行时状态，将其可视化会很有帮助。崩溃转储查看器工具 `cdv` 是 Erlang 安装的一部分。`cdv` 二进制文件的路径取决于 Erlang 版本及其安装位置。

这是调用它的示例：
    
    
    /usr/local/lib/erlang/lib/observer-2.9.1/priv/bin/cdv ./erl_crash.dump  
    

上述命令成功执行后，将打开一个类似于此的新应用程序窗口：

要使上述功能正常工作，系统必须具有图形用户界面，并且 Erlang 必须在编译时同时支持 observer 和 Wx。

## 连接

连接指南解释了如何识别应用程序连接泄漏以及其他相关主题。

## 通道

通道指南解释了通道级异常的含义、如何识别应用程序通道泄漏以及其他相关主题。

## TLS

TLS 故障排查是专门针对 TLS 主题的指南。

## LDAP

LDAP 指南解释了如何启用 LDAP 决策和查询日志记录。

## OAuth 2.0

OAuth 2.0 是专门针对 OAuth 2.0 主题的指南。

## 流量捕获

在排查网络连接、应用程序行为、连接泄漏、通道泄漏等问题时，流量捕获可以提供大量有用的信息。tcpdump 和 Wireshark 是捕获和分析网络流量的行业标准开源工具。
