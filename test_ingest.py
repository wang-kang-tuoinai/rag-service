import tempfile
import unittest
import json
from pathlib import Path

from ingest import prepare, split_sections, sync_collection
from markdown_splitter import format_chunk, split_long_section


class CharacterTokenizer:
    """确定性测试预算，中文每字符一个 token，包含两个特殊 token。"""
    def encode(self, text, **kwargs):
        return [0] * (len(text) + 2)


TECH_HEADER = '''---
doc_type: technology
component: redis
source_url: https://example.com/redis.html
---
'''

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
    def test_explicit_technology_ids_share_source_and_remain_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ('indexes', 'locks'):
                header = TECH_HEADER.replace('doc_type:', f'id: technology-mysql-{name}\ndoc_type:')
                (root / f'{name}.md').write_text(header + f'# {name}\n正文', encoding='utf-8')
            parents, chunks = prepare(root, CharacterTokenizer(), 100)
            self.assertEqual(parents, {})
            self.assertEqual({c['metadata']['doc_id'] for c in chunks},
                             {'technology-mysql-indexes', 'technology-mysql-locks'})
            self.assertEqual(len({c['metadata']['source_url'] for c in chunks}), 1)
            self.assertTrue(all('id' not in c['metadata'] for c in chunks))
            old = root / 'indexes.md'
            renamed = root / 'renamed.md'
            old.rename(renamed)
            renamed.write_text(renamed.read_text(encoding='utf-8').replace('# indexes', '# 新标题'), encoding='utf-8')
            self.assertIn('technology-mysql-indexes::section::0',
                          {c['id'] for c in prepare(root, CharacterTokenizer(), 100)[1]})
            (root / 'duplicate.md').write_text(renamed.read_text(encoding='utf-8'), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '重复文档 id'):
                prepare(root, CharacterTokenizer(), 100)

    def test_invalid_optional_technology_id_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for value in ('null', '123', '"   "', '[]'):
                header = TECH_HEADER.replace('doc_type:', f'id: {value}\ndoc_type:')
                (root / 'one.md').write_text(header + '# 标题\n正文', encoding='utf-8')
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, 'id 必须'):
                    prepare(root, CharacterTokenizer(), 100)

    def test_technology_minimal_metadata_stable_id_and_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'one.md'
            path.write_text(TECH_HEADER + '# Redis\n## 原因\n连接超时。', encoding='utf-8')
            parents, chunks = prepare(root, CharacterTokenizer(), 100)
            self.assertEqual(parents, {})
            self.assertEqual(set(chunks[0]['metadata']), {
                'doc_type', 'component', 'source_url', 'doc_id', 'source', 'title', 'section', 'chunk_index',
            })
            original_id = chunks[0]['metadata']['doc_id']
            renamed = root / 'renamed.md'
            path.rename(renamed)
            renamed.write_text(TECH_HEADER + '# 改名\n## 原因\n更新正文。', encoding='utf-8')
            self.assertEqual(prepare(root, CharacterTokenizer(), 100)[1][0]['metadata']['doc_id'], original_id)
            path.write_text(TECH_HEADER.replace('redis.html', 'redis.html#latency') + '# Redis\n正文', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '重复'):
                prepare(root, CharacterTokenizer(), 100)

    def test_technology_url_and_project_required_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / 'one.md'
            for header in (TECH_HEADER.replace('https://example.com/redis.html', '/redis.html'),
                           HEADER.replace('service: ops-agent-backend\n', '')):
                path.write_text(header + '# 标题\n正文', encoding='utf-8')
                with self.assertRaises(ValueError):
                    prepare(root, CharacterTokenizer(), 100)

    def test_project_oversized_section_still_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'one.md').write_text(HEADER + '# 标题\n## 验证\n' + '长' * 200, encoding='utf-8')
            with self.assertRaisesRegex(ValueError, '超过模型'):
                prepare(root, CharacterTokenizer(), 100)

    def test_short_section_keeps_subheadings_long_section_uses_paths(self):
        tokenizer = CharacterTokenizer()
        body = '章节前提。\n### 原因\n连接失败。\n### 验证\n检查日志。'
        self.assertEqual(split_long_section('Redis', '超时', body, tokenizer, 200), [('超时', body)])
        pieces = split_long_section('Redis', '超时', body, tokenizer, 45)
        self.assertEqual([section for section, _ in pieces], ['超时', '超时 / 原因', '超时 / 验证'])
        self.assertEqual(pieces[0][1], '章节前提。')

    def test_overlap_budget_and_long_unpunctuated_text(self):
        tokenizer = CharacterTokenizer()
        paragraphs = [f'记录{i:02d}。' for i in range(25)]
        pieces = split_long_section('标题', '章节', '\n\n'.join(paragraphs), tokenizer, 100)
        self.assertGreater(len(pieces), 1)
        self.assertEqual(pieces[0][1].split('\n\n')[-1], pieces[1][1].split('\n\n')[0])
        for section, content in pieces:
            self.assertLessEqual(len(tokenizer.encode(format_chunk('标题', section, content))), 100)
        self.assertTrue(all(paragraph in '\n'.join(content for _, content in pieces) for paragraph in paragraphs))
        long_text = '甲乙丙丁戊己庚辛壬癸' * 40
        pieces = split_long_section('标题', '章节', long_text, tokenizer, 100, overlap_ratio=0)
        self.assertEqual(''.join(content.replace('\n\n', '') for _, content in pieces), long_text)

    def test_code_preserved_and_oversized_code_reported(self):
        tokenizer = CharacterTokenizer()
        code = '```shell\n## fake heading\nredis-cli ping\n```'
        body = '前提。\n\n' + code + '\n\n' + '后续说明。' * 30
        pieces = split_long_section('标题', '章节', body, tokenizer, 100)
        self.assertTrue(any(code in content for _, content in pieces))
        self.assertTrue(all(section == '章节' for section, _ in pieces))
        _, sections = split_sections('# 标题\n## 章节\n    # 缩进代码\n    redis-cli ping')
        self.assertTrue(sections[0][1].startswith('    #'))
        with self.assertRaisesRegex(ValueError, '代码块超过'):
            split_long_section('标题', '章节', '```\n' + 'x' * 200 + '\n```', tokenizer, 100)
        with self.assertRaisesRegex(ValueError, '代码块超过'):
            split_long_section('标题', '章节', '    # fake\n    ' + 'x' * 200, tokenizer, 100)

    def test_table_split_repeats_header_and_preserves_rows(self):
        tokenizer = CharacterTokenizer()
        header = '| 参数 | 解释 |\n|---|---|'
        rows = [f'| 参数{i} | 内容{i} |' for i in range(12)]
        pieces = split_long_section('标题', '章节', header + '\n' + '\n'.join(rows), tokenizer, 110)
        self.assertGreater(len(pieces), 1)
        for section, content in pieces:
            self.assertTrue(content.startswith(header))
            self.assertLessEqual(len(tokenizer.encode(format_chunk('标题', section, content))), 110)
        for row in rows:
            self.assertEqual(sum(content.count(row) for _, content in pieces), 1)

    def test_mixed_sync_and_stale_cleanup_with_chroma(self):
        import chromadb
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'project.md').write_text(HEADER + '# 项目\n## 原因\n缓存失败', encoding='utf-8')
            tech_path = root / 'tech.md'
            tech_path.write_text(TECH_HEADER + '# Redis\n## 原因\n连接失败\n## 验证\n检查连接', encoding='utf-8')
            parents, chunks = prepare(root, CharacterTokenizer(), 100)
            client = chromadb.EphemeralClient()
            collection = client.create_collection('ingest-mixed-test')
            try:
                collection.upsert(ids=['old-section'], documents=['old'], metadatas=[{'doc_id': 'old'}], embeddings=[[1., 0.]])
                count, snapshot = sync_collection(collection, parents, chunks, [[1., 0.]] * len(chunks), root, 1)
                self.assertEqual(count, 3)
                self.assertEqual(set(json.loads(snapshot.read_text(encoding='utf-8'))), {'test-doc'})
                for meta in collection.get(include=['metadatas'])['metadatas']:
                    self.assertEqual('snapshot_id' in meta, meta['doc_type'] != 'technology')
                old_ids = set(collection.get()['ids'])
                tech_path.write_text(TECH_HEADER + '# Redis\n## 原因\n已更新', encoding='utf-8')
                parents, chunks = prepare(root, CharacterTokenizer(), 100)
                sync_collection(collection, parents, chunks, [[1., 0.]] * len(chunks), root, 1)
                self.assertEqual(collection.count(), 2)
                self.assertIn('test-doc::section::0', collection.get()['ids'])
                self.assertEqual(len(old_ids - set(collection.get()['ids'])), 1)
            finally:
                client.delete_collection(collection.name)

    def test_technology_only_no_snapshot_and_failed_upsert_no_cleanup(self):
        from unittest.mock import Mock
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'tech.md').write_text(TECH_HEADER + '# Redis\n正文', encoding='utf-8')
            parents, chunks = prepare(root, CharacterTokenizer(), 100)
            collection = Mock()
            collection.get.return_value = {'ids': [chunks[0]['id']]}
            collection.count.return_value = 1
            _, snapshot = sync_collection(collection, parents, chunks, [[1., 0.]], root, 1)
            self.assertIsNone(snapshot)
            self.assertFalse((root / 'ops_knowledge_parents').exists())
            collection.reset_mock()
            collection.upsert.side_effect = RuntimeError('write failed')
            with self.assertRaisesRegex(RuntimeError, 'write failed'):
                sync_collection(collection, parents, chunks, [[1., 0.]], root, 1)
            collection.get.assert_not_called()
            collection.delete.assert_not_called()

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
            self.assertEqual(chunks[0]['metadata']['doc_id'], 'test-doc')
            self.assertNotIn('id', chunks[0]['metadata'])
            self.assertNotIn('chunk_id', chunks[0]['metadata'])
            self.assertEqual(chunks[0]['id'], 'test-doc::section::0')
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
