# 运维知识入库

ingest.py 默认读取与脚本同目录的 doc/，跳过 README.md，不再导入旧 docs/。旧 go_docs collection 不会被修改；现有问答服务仍使用原检索配置，运维检索接口尚待接入。

## 使用

在 rag-service 目录，使用项目 Python 环境：

```text
python ingest.py --dry-run
python ingest.py
```

--dry-run 只校验文档与切分，输出数量和首个章节，不加载模型、不写数据库。正常运行需要已安装 requirements.txt，并能加载 BAAI/bge-base-zh-v1.5。可用 --root 和 --db-path 覆盖路径。

## 存储契约

- Chroma 集合：ops_knowledge；余弦距离，归一化 embedding。
- documents：文档标题 + 章节标题 + 章节正文，不拼 YAML 元数据。
- 每条 metadata：文档头 id 转为 doc_id，其余标量字段保留，再加 source、title、section、chunk_index、snapshot_id。章节 ID 只通过 Chroma ids 存储，不在 metadata 中重复保存 id/chunk_id。父文档快照仍保留原始文档头 id。
- 文档 id 必须唯一；必需字段缺失、空正文、非标量 metadata 均提前报错。日期如要增加必须写为带引号字符串。
- H2 切分，H3、表格和代码块保留；一级标题前后的非 H2 正文归入“概述”。空章节不入库；没有 H2 时正文作为一个章节。
- embedding 前按模型 tokenizer 检查长度，超限时拒绝入库，需进一步拆分章节，不静默截断。reranker 的输入预算仍需在后续检索层检查。
- 父文档快照：my_chroma_data/ops_knowledge_parents/<snapshot_id>.json，以 doc_id 查找完整正文、标题及元数据。正文保留 Markdown，排除 front matter。

## 重建与失败恢复

先完成解析、长度检查和向量生成，再保存快照、upsert 当前章节，最后删除本集合中已消失的章节。旧快照保留，保证每条记录关联到对应入库正文；暂未做快照清理。

此流程是小规模全量同步，不是原子切换。中途写入失败可能出现新旧章节并存，重新运行完成同步即可；不应并发运行两个入库进程，构建期间避免查询该集合。不要把旧 go_docs 的检索结果当作新索引效果。

当前已完成解析测试和 dry-run：10 篇文档、55 个章节。尚未实际运行模型向量化或写入 Chroma。
