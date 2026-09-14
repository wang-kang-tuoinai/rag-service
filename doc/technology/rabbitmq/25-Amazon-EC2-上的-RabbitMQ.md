---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/docs/ec2
---

# 在 Amazon EC2 上运行 RabbitMQ

## 概述

本指南假定您已熟悉通用的 集群指南 以及 集群节点发现 指南。

在 EC2 上使用 RabbitMQ 与在其他平台上运行非常相似。不过，EC2 存在一些需要注意的细微之处，主要与主机名及其解析有关。

本指南演示了手动（基于 CLI）的 RabbitMQ 集群配置。对于自动化部署，使用 AWS 节点发现插件（RabbitMQ 3.7.0 或更高版本）是一个更合适的选择。

## AMI

只要安装了 兼容的 Erlang/OTP 版本，RabbitMQ 就能在最新的 Ubuntu、Debian 和 CentOS AMI 上良好运行。

## 选择实例类型

RabbitMQ 可以在任何实例类型上运行，但有几点注意事项值得牢记：

  * 使用 64 位实例。
  * 根据工作负载和设置的不同，RabbitMQ 可能需要大量的内存。请确保您的主机具有 充足的内存 (RAM)，并始终启用至少几 GB 的交换空间 (swap space)。可以使用 PerfTest 来模拟工作负载。此外，还有一份关于 节点内存使用分析 的单独指南供参考。
  * 只要工作负载使用了 多个队列，RabbitMQ 通常会利用系统中的所有 CPU 核心。同时也应考虑其他因素（如磁盘和网络 I/O 吞吐量）。
  * 对 RabbitMQ 节点以及使用它的应用程序在真实或模拟工作负载下进行 监控，将有助于评估特定实例类型的适用性。



## 操作系统

尽管 RabbitMQ 已在大多数主流 Linux 发行版上进行了测试，但 Ubuntu 对 Amazon EC2 的支持似乎最为稳健，因此本指南将使用该发行版。

Ubuntu 云镜像 提供了专门为公有云设计的 Ubuntu 镜像（构建版本）。

## 安装

请查阅以下安装指南：

  * Debian 和 Ubuntu
  * RHEL、CentOS 和 Fedora



可以使用多种部署工具来自动完成 RabbitMQ 的部署。

  * 社区 Docker 镜像（在 GitHub 上）
  * Chef cookbook
  * Puppet 模块



以上是一些常用的选择。

## EBS 卷上的持久存储

在 Linux 上，RabbitMQ 将使用以下目录作为其节点数据目录：

  * `/var/lib/rabbitmq/` 用于存储持久化数据，如消息或队列
  * `/var/log/rabbitmq/` 用于存储日志



有关详细信息，请参阅 文件和目录位置。

这些目录可以是指向专用存储卷的符号链接。执行符号链接操作前，必须停止节点。
    
    
    sudo service rabbitmq-server stop  
    

建议尽可能在安装 RabbitMQ 之前执行符号链接和其他存储准备步骤。

请注意，EBS 卷具有 IOPS 限制，这可能会影响吞吐量和 RabbitMQ 操作。如果 EBS 卷达到限制，磁盘写入性能会下降。此外，RabbitMQ 消息存储压缩（磁盘上数据的垃圾回收）可能会滞后于磁盘写入，这意味着磁盘空间的耗尽速度可能快于消息消费和确认后回收空间的速度。这最终会导致 资源警报 和发布者限流。请确保限制阈值足够高，并设置 I/O 操作速率监控。

## 延伸阅读

其他几篇指南涵盖了在公有云中运行 RabbitMQ 集群高度相关的主题：

  * 集群基础知识
  * 节点发现
  * 配置
  * 监控
  * 部署指南
  * 文件和目录位置
