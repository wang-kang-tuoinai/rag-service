# 运维知识入库

ingest.py 默认读取与脚本同目录的 doc/，跳过 README.md，不再导入旧 docs/。旧 go_docs collection 不会被修改。

知识查询接口已支持两种结果：architecture/runbook 读取父文档快照，technology 直接返回切片，不要求 snapshot_id。请求和响应见 knowledge-search-api.md。

## 使用

在 rag-service 目录，使用项目 Python 环境：

```text
python ingest.py --dry-run
python ingest.py
```

--dry-run 加载 tokenizer 和模型长度配置，校验文档与切分，输出文档数、父文档数、切片数和首个切片，不加载模型权重、不写数据库。首次运行可能需要下载 tokenizer 与配置；缓存齐全时可设置 HF_HUB_OFFLINE=1 离线执行。正常入库需要加载 BAAI/bge-base-zh-v1.5 模型权重。可用 --root 和 --db-path 覆盖路径。

--root 表示整个 ops_knowledge 集合的期望内容，不是增量追加目录。仅指定某个子目录正式入库，会清理本集合中其他目录的记录。

## 存储契约

- Chroma 集合：ops_knowledge；余弦距离，归一化 embedding。
- documents：文档标题 + 章节标题 + 章节正文，不拼 YAML 元数据。
- architecture/runbook 必填 id、doc_type、project、service、component、deployment。文档头 id 转为 doc_id，其余标量字段保留，再加 source、title、section、chunk_index、snapshot_id。父文档快照仍保留原始文档头 id。
- technology 只必填 doc_type、component、source_url；来源必须为完整 HTTP(S) URL。可选 id 为非空字符串：填写时直接用作 doc_id；未填写时，脚本去掉 URL 锚点、统一域名大小写后计算 SHA-256，沿用原来的 technology-<hash> ID。
- source_url 表示来源，不要求一篇来源只对应一个本地文件。同一来源按主题拆成多个文件时，各文件指定唯一且固定的 id，例如 technology-mysql-indexes、technology-mysql-locks。文件名、标题和正文更新后保留该 id，避免身份变化；自动拆分脚本可在首次输出文件时生成并写入 id。相同 id 仍会报错，不能通过取消去重校验解决来源重复。
- id 只在文件头维护，写入 Chroma 时转为 doc_id，不重复保存两个字段。无显式 id 时不同来源 URL 视为不同文章，不做正文相似去重。更改已有文档的 id 后，完整运行 ingest.py 会写入新切片并清理旧 ID 的切片。
- technology 每条 metadata 自动添加 doc_id、source、title、section、chunk_index；额外标量字段如 version 可以保留。不要求 project/service/deployment，也不保存 snapshot_id 或父文档。
- 切片 ID 为 doc_id::section::<chunk_index>，仅通过 Chroma ids 存储，不在 metadata 中重复保存 id/chunk_id。
- 所有类型统一检查 doc_id 唯一；必需字段缺失、空正文、非标量 metadata 均提前报错。日期如要增加必须写为带引号字符串。
- 公共解析与切分位于 markdown_splitter.py，入库类型分流位于 ingest.py 的 prepare()。项目文档按 H2 切分，H3 及以下、表格和代码块保留；超长仍报错，需要人工调整。非 H2 正文归入“概述”，空章节不入库。
- 技术文档先按 H2 切分；章节未超限就整体保留，超限时优先沿 H3 至 H6 细分，section 保存标题路径；仍超限时按段落、列表项、句子切分，无标点长句最终按字符边界细分。
- 同一技术章节继续切分时，重叠预算为扣除标题后正文 token 预算的 12%，优先复用末尾完整段落或句子。为保留结构或容纳下一块，实际重叠可以更少甚至为零；不跨章节重叠。
- 围栏代码和缩进代码不作为标题解析，也不直接截断。单个代码块超限会报出标题与章节，要求人工拆分。长表格按行拆分并重复表头，表头加单行仍超限则报错。
- token 预算包含文档标题、章节路径、正文和特殊 token。切分前读取 tokenizer 和 SentenceTransformer 长度配置，embedding 前用真实模型配置二次校验，不静默截断。reranker 的输入预算仍需在后续检索层检查。
- 父文档快照：my_chroma_data/ops_knowledge_parents/<snapshot_id>.json，只包含 architecture/runbook，以 doc_id 查找完整正文、标题及元数据。正文保留 Markdown，排除 front matter。只有技术文档时不创建快照。

## 重建与失败恢复

先汇总所有类型文档，完成解析、长度检查和向量生成，再保存项目文档快照、统一 upsert 所有切片，最后删除本集合中已消失的切片。不能分别对两类文档执行全量清理。旧快照保留，暂未做快照清理。

此流程是小规模全量同步，不是原子切换。中途写入失败可能出现新旧章节并存，重新运行完成同步即可；不应并发运行两个入库进程，构建期间避免查询该集合。不要把旧 go_docs 的检索结果当作新索引效果。

本次使用本地真实 tokenizer 完成 dry-run：23 篇文档、10 篇父文档、226 个切片，均满足 512 token 上限。回归测试覆盖类型校验、ID 稳定性、标题路径、重叠、代码/表格边界，并在临时 Chroma 集合验证混合类型同步与旧记录清理。本次没有执行模型向量化或重建正式索引。
