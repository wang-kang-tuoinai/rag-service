import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from knowledge import KnowledgeUnavailable, search_knowledge
from knowledge_api import router
from knowledge_models import KnowledgeSearchResponse


class Model:
    def encode(self, text, **kwargs):
        return SimpleNamespace(tolist=lambda: [1.0, 0.0])


class Ranker:
    def predict(self, pairs):
        return [float(text) for _, text in pairs]


class Collection:
    def __init__(self, rows):
        self.rows = rows
        self.kwargs = None

    def count(self):
        return len(self.rows)

    def query(self, **kwargs):
        self.kwargs = kwargs
        rows = self.rows
        if "where" in kwargs:
            rows = [row for row in rows if row[1]["doc_type"] == kwargs["where"]["doc_type"]]
        return {"documents": [[r[0] for r in rows]], "metadatas": [[r[1] for r in rows]],
                "ids": [[f"{r[1]['doc_id']}::{r[1].get('chunk_index', r[1]['section'])}" for r in rows]]}


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.directory = Path(self.tmp.name)
        parents = {name: {"body": f"# {name}\n完整正文，包含未命中章节", "title": name,
                          "source": f"{name}.md", "metadata": {"id": name, "doc_type": kind}}
                   for name, kind in [("a", "runbook"), ("b", "architecture")]}
        payload = json.dumps(parents, ensure_ascii=False).encode("utf-8")
        self.snapshot = hashlib.sha256(payload).hexdigest()
        (self.directory / f"{self.snapshot}.json").write_bytes(payload)
        self.collection = Collection([
            (score, {"doc_id": name, "snapshot_id": self.snapshot, "section": section, "doc_type": kind})
            for score, name, section, kind in [("0.9", "a", "原因", "runbook"),
                                              ("0.8", "a", "验证", "runbook"),
                                              ("0.85", "b", "流程", "architecture")]])

    def search(self, **kwargs):
        return search_knowledge(self.collection, Model(), Ranker(), self.directory, "Redis 故障", **kwargs)

    def technology_row(self, score, index=0):
        return (str(score), {"doc_id": "redis-tech", "doc_type": "technology", "title": "Redis 延迟",
                            "source": "technology/redis/latency.md", "source_url": "https://example.com/redis",
                            "component": "redis", "section": "测量延迟", "chunk_index": index})

    def test_mixed_candidates_ranked_after_document_aggregation(self):
        self.collection.rows[2] = ('0.82', self.collection.rows[2][1])
        self.collection.rows += [self.technology_row(0.88, 0), self.technology_row(0.85, 1)]
        result = self.search()
        self.assertEqual([item['score'] for item in result['items']], [0.90, 0.88, 0.85])
        self.assertEqual([item['content_mode'] for item in result['items']], ['full', 'chunk', 'chunk'])
        self.assertEqual(result['items'][0]['matched_sections'], ['原因', '验证'])
        self.assertEqual(result['items'][1]['chunk_id'], 'redis-tech::0')
        self.assertEqual(result['items'][1]['content'], '0.88')
        self.assertNotIn('snapshot_id', result['items'][1])
        self.assertNotIn('matched_sections', result['items'][1])
        self.assertNotIn('chunk_id', result['items'][0])
        KnowledgeSearchResponse.model_validate(result)

    def test_three_chunks_from_same_document_no_parent_access(self):
        self.collection.rows = [self.technology_row(0.9 - i / 10, i) for i in range(4)]
        with patch('knowledge.load_parent', side_effect=AssertionError('不应读取父文档')):
            result = search_knowledge(self.collection, Model(), Ranker(), None, 'Redis', doc_type='technology')
        self.assertEqual([item['chunk_index'] for item in result['items']], [0, 1, 2])
        self.assertEqual(self.collection.kwargs['where'], {'doc_type': 'technology'})

    def test_technology_fields_and_scores_validated(self):
        for field in ('source_url', 'component', 'title', 'source', 'chunk_index'):
            row = self.technology_row(0.9)
            del row[1][field]
            self.collection.rows = [row]
            with self.subTest(field=field), self.assertRaises(KnowledgeUnavailable):
                self.search()
        self.collection.rows = [self.technology_row('nan')]
        with self.assertRaisesRegex(KnowledgeUnavailable, '分数'):
            self.search()

    def test_chunk_dedup_ties_and_selected_results_budget(self):
        self.collection.rows = [self.technology_row(0.9, 2), self.technology_row(0.9, 1),
                                self.technology_row(0.9, 1), self.technology_row(0.8, 0)]
        self.assertEqual([item['chunk_index'] for item in self.search()['items']], [1, 2, 0])
        # 先确定 top_k，预算不足整条省略，不以低分结果补位，也不截断正文。
        self.collection.rows = [('0.900000', self.technology_row(0.9)[1]), self.technology_row(0.8, 1)]
        result = self.search(top_k=1, max_content_chars=4)
        self.assertEqual(result['items'], [])
        self.assertTrue(any('整条省略' in notice for notice in result['notices']))

    def test_max_score_dedup_and_full_snapshot(self):
        result = self.search()
        self.assertEqual([item["doc_id"] for item in result["items"]], ["a", "b"])
        self.assertEqual(result["items"][0]["score"], 0.9)
        self.assertEqual(result["items"][0]["matched_sections"], ["原因", "验证"])
        self.assertIn("未命中章节", result["items"][0]["content"])
        self.assertNotIn("where", self.collection.kwargs)

    def test_same_document_mixed_snapshots_rejected(self):
        self.collection.rows[1][1]['snapshot_id'] = '0' * 64
        with self.assertRaisesRegex(KnowledgeUnavailable, '多个快照'):
            self.search()

    def test_filter_and_document_limit(self):
        result = self.search(doc_type="architecture", top_k=1)
        self.assertEqual(result["items"][0]["doc_id"], "b")
        self.assertEqual(self.collection.kwargs["where"], {"doc_type": "architecture"})
        self.assertEqual(len(self.search(top_k=2)["items"]), 2)

    def test_empty_and_budget(self):
        self.assertEqual(self.search(max_content_chars=1)["items"], [])
        self.collection.rows = []
        self.assertEqual(self.search()["items"], [])

    def test_missing_corrupt_and_unsafe_snapshot(self):
        path = self.directory / f"{self.snapshot}.json"
        path.write_text("{}", encoding="utf-8")
        with self.assertRaises(KnowledgeUnavailable):
            self.search()
        path.unlink()
        with self.assertRaises(KnowledgeUnavailable):
            self.search()
        for _, meta in self.collection.rows:
            meta["snapshot_id"] = "../../elsewhere"
        with self.assertRaises(KnowledgeUnavailable):
            self.search()

    def test_http(self):
        app = FastAPI()
        app.include_router(router, prefix="/api/v1")
        app.state.model = Model()
        app.state.reranker = Ranker()
        app.state.collection = self.collection
        app.state.knowledge_snapshot_dir = self.directory
        with TestClient(app) as client:
            response = client.post("/api/v1/knowledge/search", json={"query": "Redis", "doc_type": "runbook"})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(len(response.json()["items"]), 1)
            self.collection.rows.append(self.technology_row(0.88))
            response = client.post('/api/v1/knowledge/search', json={'query': 'Redis'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual([item['content_mode'] for item in response.json()['items']], ['full', 'chunk', 'full'])
            schema = client.get('/openapi.json').json()['components']['schemas']
            item_schema = schema['KnowledgeSearchResponse']['properties']['items']['items']
            self.assertEqual(item_schema['discriminator']['propertyName'], 'content_mode')
            self.assertEqual(set(item_schema['discriminator']['mapping']), {'full', 'chunk'})
            del app.state.knowledge_snapshot_dir
            response = client.post('/api/v1/knowledge/search', json={'query': 'Redis', 'doc_type': 'technology'})
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn('snapshot_id', response.json()['items'][0])
            self.assertEqual(client.post('/api/v1/knowledge/search', json={'query': 'Redis', 'doc_type': 'runbook'}).status_code, 503)
            app.state.knowledge_snapshot_dir = self.directory
            for body in [{"query": "  "}, {"query": "x", "doc_type": "invalid"},
                         {"query": "x", "top_k": 0}, {"query": "x", "top_k": 6},
                         {"query": "x", "component": "redis"}]:
                self.assertEqual(client.post("/api/v1/knowledge/search", json=body).status_code, 422)
            del app.state.model
            self.assertEqual(client.post("/api/v1/knowledge/search", json={"query": "x"}).status_code, 503)

    def test_real_chroma_filter_and_empty_match(self):
        import chromadb
        client = chromadb.EphemeralClient()
        collection = client.create_collection("knowledge-test-filter")
        try:
            collection.add(ids=["one", "two", "three"],
                           documents=[row[0] for row in self.collection.rows],
                           metadatas=[row[1] for row in self.collection.rows],
                           embeddings=[[1.0, 0.0]] * 3)
            result = search_knowledge(collection, Model(), Ranker(), self.directory,
                                      "query", doc_type="architecture")
            self.assertEqual([item["doc_id"] for item in result["items"]], ["b"])
            technology = self.technology_row(0.95)
            collection.add(ids=['actual-chroma-id'], documents=[technology[0]], metadatas=[technology[1]],
                           embeddings=[[1.0, 0.0]])
            result = search_knowledge(collection, Model(), Ranker(), None, 'query', doc_type='technology')
            self.assertEqual(result['items'][0]['chunk_id'], 'actual-chroma-id')
            self.assertNotIn('snapshot_id', result['items'][0])
            collection.delete(ids=["three"])
            result = search_knowledge(collection, Model(), Ranker(), self.directory,
                                      "query", doc_type="architecture")
            self.assertEqual(result["items"], [])
        finally:
            client.delete_collection("knowledge-test-filter")


if __name__ == "__main__":
    unittest.main()
