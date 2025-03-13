import unittest
from unittest.mock import patch, MagicMock
from src.serper_client import SerperClient


class TestSerperClient(unittest.TestCase):
    """测试 Serper 搜索客户端"""

    @patch('src.serper_client.get_config')
    def setUp(self, mock_get_config):
        """测试前准备"""
        # 模拟配置
        mock_get_config.return_value = {
            "serper": {
                "api_key": "test_api_key",
                "base_url": "https://test.serper.dev/search"
            }
        }

        # 创建客户端实例
        self.client = SerperClient()

    def test_init(self):
        """测试初始化"""
        self.assertEqual(self.client.api_key, "test_api_key")
        self.assertEqual(self.client.base_url, "https://test.serper.dev/search")

    @patch('httpx.Client.post')
    def test_search(self, mock_post):
        """测试搜索功能"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "organic": [
                {
                    "title": "Test Result",
                    "link": "https://example.com",
                    "snippet": "This is a test result"
                }
            ]
        }
        mock_post.return_value = mock_response

        # 执行搜索
        result = self.client.search("test query")

        # 验证请求
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["headers"]["X-API-KEY"], "test_api_key")
        self.assertEqual(kwargs["json"]["q"], "test query")

        # 验证结果转换
        self.assertEqual(result["query"], "test query")
        self.assertEqual(len(result["data"]), 1)
        self.assertEqual(result["data"][0]["title"], "Test Result")
        self.assertEqual(result["data"][0]["url"], "https://example.com")
        self.assertEqual(result["data"][0]["content"], "This is a test result")

    @patch('httpx.Client.post')
    def test_search_with_options(self, mock_post):
        """测试带选项的搜索"""
        # 模拟响应
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"organic": []}
        mock_post.return_value = mock_response

        # 执行搜索
        self.client.search("test query", {"gl": "us", "num": 5})

        # 验证请求选项
        args, kwargs = mock_post.call_args
        self.assertEqual(kwargs["json"]["gl"], "us")
        self.assertEqual(kwargs["json"]["num"], 5)


if __name__ == '__main__':
    unittest.main()
