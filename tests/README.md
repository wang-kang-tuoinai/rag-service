# 测试

在 **rag-service 根目录**、已安装 `requirements.txt` 依赖的 Python 环境中运行：

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -t . -v
```

也可单独运行某一组：

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_ingest -v
.\.venv\Scripts\python.exe -m unittest tests.test_knowledge -v
.\.venv\Scripts\python.exe -m unittest tests.test_main -v
```

| 文件 | 覆盖范围 |
| --- | --- |
| `test_ingest.py` | 元数据校验、文档 ID、标题切分、重叠、代码与表格边界、混合类型入库和旧切片清理 |
| `test_knowledge.py` | 召回过滤、文档最大分数聚合、技术切片独立排序、父文档完整性、正文预算及 HTTP 契约 |
| `test_main.py` | lifespan 加载依赖、复用 collection、索引缺失时拒绝启动及路由范围 |

测试使用合成文档、模拟 tokenizer/embedding/reranker、临时父文档快照和 Chroma 临时或内存集合；不会重建正式 `my_chroma_data`，也不加载模型权重进行真实检索。测试仍需安装服务依赖，以便导入相关模块。

请使用上面的模块或 discover 命令，不直接执行 `python tests/test_*.py`。这些测试验证实现与接口，不衡量真实资料的召回率或诊断效果。
