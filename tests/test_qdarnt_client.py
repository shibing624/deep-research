import unittest
from unittest.mock import patch, MagicMock
import numpy as np
from src.qdrant_client import QdrantSearchClient


class TestQdrantSearchClient(unittest.TestCase):
    """测试 Qdrant 搜索客户端"""

    @patch('src.qdrant_search_client.get_config')
    @patch('src.qdrant_search_client.SentenceTransformerEmbedding')
    @patch('src.qdrant_search_client.QdrantEngine')
    def setUp(self, mock_qdrant_engine, mock_embedding, mock_get_config):
        """测试前准备"""
        # 模拟配置
        mock_get_config.return_value = {
            "qdrant": {
                "qdrant_collection_name": "test_collection",
                "qdrant_host": "test_host",
                "qdrant_port": 1234,
                "embedding_model_path": "test_model_path",
                "device": "cpu"
            }
        }

        # 模拟嵌入生成器
        self.mock_embedding_instance = mock_embedding.return_value
        self.mock_embedding_instance.embedding_size = 384
        self.mock_embedding_instance.generate_embedding.return_value = np.zeros(384)

        # 模拟 Qdrant 引擎
        self.mock_engine_instance = mock_qdrant_engine.return_value
        self.mock_engine_instance.search.return_value = [
            {
                "payload": {
                    "url": "https://test.com",
                    "title": "Test Document",
                    "content": "This is a test document content"
                },
                "score": 0.95
            }
        ]

        # 创建客户端实例
        self.client = QdrantSearchClient()

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.client.collection_name, "test_collection")
        self.assertEqual(self.client.host, "test_host")
        self.assertEqual(self.client.port, 1234)
        self.assertEqual(self.client.embedding_model_path, "test_model_path")
        self.assertEqual(self.client.device, "cpu")

    def test_search_sync(self):
        """测试同步搜索功能"""
        # 执行搜索
        result = self.client.search_sync("test query")

        # 验证嵌入生成
        self.mock_embedding_instance.generate_embedding.assert_called_once_with("test query")

        # 验证 Qdrant 搜索
        self.mock_engine_instance.search.assert_called_once()
        args, kwargs = self.mock_engine_instance.search.call_args
        self.assertEqual(kwargs["text"], "test query")
        self.assertEqual(kwargs["limit"], 5)
        self.assertIsNone(kwargs["query_filter"])

        # 验证结果转换
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["url"], "https://test.com")
        self.assertEqual(result["data"][0]["title"], "Test Document")
        self.assertEqual(result["data"][0]["content"], "This is a test document content")
        self.assertEqual(result["data"][0]["score"], 0.95)
        self.assertEqual(result["data"][0]["source"], "qdrant_search")

    def test_search_sync_with_options(self):
        """测试带选项的同步搜索"""
        # 准备过滤条件
        filter_conditions = [
            {"key": "category", "match": "paper"}
        ]

        # 执行搜索
        result = self.client.search_sync("test query", {
            "limit": 10,
            "filter_conditions": filter_conditions
        })

        # 验证搜索选项
        args, kwargs = self.mock_engine_instance.search.call_args
        self.assertEqual(kwargs["limit"], 10)
        self.assertIsNotNone(kwargs["query_filter"])

    @patch('asyncio.get_event_loop')
    def test_search_async(self, mock_get_event_loop):
        """测试异步搜索功能"""
        # 模拟异步执行
        mock_loop = MagicMock()
        mock_get_event_loop.return_value = mock_loop
        mock_loop.run_in_executor.return_value = MagicMock()

        # 执行异步搜索
        self.client.search("test query")

        # 验证异步执行
        mock_loop.run_in_executor.assert_called_once()
        args = mock_loop.run_in_executor.call_args[0]
        self.assertEqual(args[2], "test query")

    def test_transform_result(self):
        """测试结果转换"""
        # 准备测试数据
        qdrant_results = [
            {
                "payload": {
                    "url": "https://test1.com",
                    "title": "Test 1",
                    "content": "Content 1" * 2000  # 超长内容
                },
                "score": 0.9
            },
            {
                "payload": {
                    "url": "https://test2.com",
                    "title": "Test 2",
                    "content": "Content 2"
                },
                "score": 0.8
            }
        ]

        # 执行转换
        result = self.client._transform_result(qdrant_results, "test query")

        # 验证结果
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["data"]), 2)
        self.assertEqual(result["data"][0]["url"], "https://test1.com")
        self.assertEqual(result["data"][0]["title"], "Test 1")
        self.assertTrue(len(result["data"][0]["content"]) <= 4000)  # 确保内容被截断
        self.assertEqual(result["data"][1]["url"], "https://test2.com")


if __name__ == '__main__':
    unittest.main()