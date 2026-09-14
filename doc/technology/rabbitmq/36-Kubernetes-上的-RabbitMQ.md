---
doc_type: technology
component: rabbitmq
source_url: https://rabbitmq.cn/kubernetes/operator/operator-overview
---

# RabbitMQ Kubernetes Operators: Cluster Operator 和 Messaging Topology Operator

RabbitMQ 团队开发并维护了两个 Kubernetes Operator：RabbitMQ Cluster Kubernetes Operator 和 RabbitMQ Messaging Topology Operator。

  * RabbitMQ Cluster Kubernetes Operator 实现了 RabbitMQ 集群在 Kubernetes 上配置、管理和运维的自动化。

  * RabbitMQ Messaging Topology Operator 用于管理通过 RabbitMQ Cluster Kubernetes Operator 部署的 RabbitMQ 集群中的消息拓扑结构。




Kubernetes Operator 是 Kubernetes 的软件扩展，它提供自定义资源，用于管理应用程序、服务及其组件。

在本文档及其他与 Operator 相关的信息中，“Operator”（首字母大写）用于指代 Kubernetes Operator 模式的实现，而“operator”（首字母小写）用于指代技术运维工程师（管理员）。

## RabbitMQ Cluster Kubernetes Operator

RabbitMQ Cluster Kubernetes Operator 提供了一种一致且简便的方法来在 Kubernetes 上部署和运行 RabbitMQ 集群，包括“第二天”（持续）的运维工作。使用该 Operator 部署的 RabbitMQ 集群既可供 Kubernetes 内部运行的应用程序使用，也可供外部应用程序使用。

Cluster Operator 的文档涵盖多个指南：

  * 限制
  * 快速入门指南：RabbitMQ Cluster Kubernetes Operator
  * 安装 RabbitMQ Cluster Kubernetes Operator
  * 配置默认值：RabbitMQ Cluster Operator
  * RabbitMQ kubectl 插件
  * 使用 RabbitMQ Cluster Kubernetes Operator
  * 监控 Kubernetes 上的 RabbitMQ 集群
  * 法定人数状态监控：Kubernetes 上的 RabbitMQ 集群
  * 排查 Kubernetes 上的 RabbitMQ 集群故障
  * 升级 RabbitMQ Kubernetes Operator
  * 在 Openshift 上使用 RabbitMQ Kubernetes Operator



此外，还有一个独立的 Operator 用于管理统称为消息拓扑的集群对象：虚拟主机 (vhost)、用户、队列等。相关内容包含在以下指南中：

  * 安装 RabbitMQ Messaging Topology Operator
  * 使用 RabbitMQ Messaging Topology Operator
  * 在 Messaging Topology Kubernetes Operator 中使用 TLS
  * 排查 Messaging Topology Kubernetes Operator 故障



该 Operator 提供以下主要功能：

  * 单节点和多节点 RabbitMQ 集群的自动化配置
  * 当部署集群的实际状态与预期状态不符时，进行自动协调（Reconciliation）
  * 使用 Prometheus 和 Grafana 监控 RabbitMQ 集群
  * RabbitMQ 集群的扩容和自动化滚动升级



### RabbitMQ Cluster Kubernetes Operator 设计原则

RabbitMQ Cluster Kubernetes Operator 的设计基于以下理念和概念：

  * 应提供灵活的 RabbitMQ 节点配置
  * 在可能的情况下应提供合理的安全默认值
  * 应简化 RabbitMQ 的运维工作



遵循这些理念，Operator 不会修改现有的 `RabbitmqCluster` 规范 (spec)。这意味着，当 Operator 升级时，即使有新的默认值或 RabbitMQ 更新版本，它也不会自动更新现有的 `RabbitmqCluster` 实例。

唯一的例外是，当用户手动从规范中删除某个字段时，Operator 将会设置默认值。

### 限制

#### RabbitMQ Cluster Operator 协调机制

删除的 `Secret` 对象将由 Kubernetes Operator 重新创建，但新生成的密钥值不会部署到 RabbitMQ 集群中。例如，如果删除了包含管理员凭据的 `Secret`，系统会创建一个带有新用户名和密码的新 `Secret`，但这些更改不会反映在 RabbitMQ 集群中。对于任何 `Secret` 值，如共享节点间认证密钥（即 Erlang cookie）的值，处理方式相同。

#### RabbitMQ Cluster Operator 功能标志

Cluster Operator 不支持禁用任何 RabbitMQ 功能标志。Operator 会列出所有可用的功能标志，并在集群启动时启用所有标志。

## RabbitMQ Messaging Topology Operator

RabbitMQ Messaging Topology Operator 支持通过 Kubernetes 声明式 API 管理 RabbitMQ 消息拓扑对象。

Messaging Topology Operator 的文档结构如下：

  * 限制
  * 安装 RabbitMQ Messaging Topology Operator
  * 使用 RabbitMQ Messaging Topology Operator
  * Messaging Topology Operator 的 TLS 配置
  * 排查 Messaging Topology Operator 故障



### 限制

#### 自定义默认凭据导致 401 未授权错误

Topology Operator 依赖于由 Cluster Operator 创建的默认凭据 `Secret`。如果在 `RabbitmqCluster` 的 `spec` 中通过 `additionalConfig` 使用 `default_user` 和 `default_pass` 键定义了默认用户，将导致生成的默认凭据 `Secret` 不正确。由于凭据错误，Topology Operator 的所有操作都会报错，并在日志中打印以下消息：
    
    
    Error: API responded with a 401 Unauthorized  
    

有关详细信息和解决方案，请参阅排查 Messaging Topology Operator 故障部分。

## 这些 Kubernetes Operator 的源代码

这两个 Operator 均为开源项目。您可以在 GitHub 上为其开发做出贡献：

  * RabbitMQ Cluster Kubernetes Operator
  * RabbitMQ Messaging Topology Operator



## 这些 Kubernetes Operator 的许可证

这两个 Operator 均根据 Mozilla Public License 2.0 发布。

## 支持的 Kubernetes 版本

RabbitMQ Operator 旨在与任何符合 Kubernetes 标准的平台配合使用。如果您在特定的 Kubernetes 发行版中遇到问题，请查看 GitHub 仓库中的已知问题。

有关 Operator 支持哪些 Kubernetes 和 RabbitMQ 服务器版本的更多信息，请查阅 README。
