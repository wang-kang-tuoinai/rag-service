"""验证服务启动只加载运维索引，查询复用已加载的 collection。"""
import unittest
from unittest.mock import Mock, patch

from chromadb.errors import NotFoundError
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main
from knowledge import COLLECTION
from knowledge_api import router


class LifespanTests(unittest.TestCase):
    def setUp(self):
        self.model = Mock()
        self.reranker = Mock()
        self.collection = Mock()
        self.collection.count.return_value = 0
        self.client = Mock()
        self.client.get_collection.return_value = self.collection
        self.provider = Mock()
        for target, value in [('SentenceTransformer', self.model), ('CrossEncoder', self.reranker),
                              ('chromadb.PersistentClient', self.client)]:
            patcher = patch(f'main.{target}', return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = patch('main.tracer_provider', self.provider)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = FastAPI(lifespan=main.lifespan)
        self.app.include_router(router, prefix='/api/v1')

    def test_collection_loaded_once_and_bot_routes_removed(self):
        with TestClient(self.app) as http:
            self.assertIs(self.app.state.collection, self.collection)
            self.assertIs(self.app.state.model, self.model)
            self.assertIs(self.app.state.reranker, self.reranker)
            for _ in range(2):
                response = http.post('/api/v1/knowledge/search', json={'query': 'Redis'})
                self.assertEqual(response.status_code, 200, response.text)
            self.client.get_collection.assert_called_once_with(COLLECTION)
        self.provider.shutdown.assert_called_once()
        self.assertEqual(set(main.app.openapi()['paths']), {'/health', '/api/v1/knowledge/search'})

    def test_missing_index_fails_startup(self):
        self.client.get_collection.side_effect = NotFoundError('missing')
        with self.assertRaisesRegex(RuntimeError, 'ops_knowledge.*ingest.py'):
            with TestClient(self.app):
                self.fail('索引缺失时不能启动服务')
        self.assertFalse(hasattr(self.app.state, 'collection'))
        self.client.get_collection.assert_called_once_with(COLLECTION)


if __name__ == '__main__':
    unittest.main()
