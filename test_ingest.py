import tempfile
import unittest
from pathlib import Path

from ingest import prepare, split_sections

HEADER = '''---
id: test-doc
doc_type: runbook
project: ops-agent
service: ops-agent-backend
component: redis
deployment: docker-compose
---
'''


class IngestTests(unittest.TestCase):
    def test_sections_and_fenced_heading(self):
        title, sections = split_sections('# 标题\n前言\n## 验证\n```text\n## 假标题\n```\n### 子标题\n内容\n## 空章节\n')
        self.assertEqual(title, '标题')
        self.assertEqual(len(sections), 2)
        self.assertIn('## 假标题', sections[1][1])
        self.assertIn('### 子标题', sections[1][1])
        self.assertEqual(split_sections('# 标题\n正文')[1], [('概述', '正文')])

    def test_metadata_parent_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'one.md'
            path.write_text(HEADER + '# 文档\n## 原因\n缓存失败\n## 验证\n检查日志', encoding='utf-8')
            parents, chunks = prepare(root)
            self.assertEqual(len(chunks), 2)
            self.assertEqual(chunks[0]['metadata']['component'], 'redis')
            self.assertEqual(chunks[0]['text'], '文档标题：文档\n章节标题：原因\n\n缓存失败')
            self.assertIn('## 验证', parents['test-doc']['body'])
            self.assertNotIn('deployment:', parents['test-doc']['body'])
            (root / 'two.md').write_text(path.read_text(encoding='utf-8'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '重复'):
                prepare(root)

    def test_invalid_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'one.md').write_text(HEADER.replace('component: redis', 'component: [redis]') + '# 标题\n正文', encoding='utf-8')
            with self.assertRaises(ValueError):
                prepare(root)


if __name__ == '__main__':
    unittest.main()
