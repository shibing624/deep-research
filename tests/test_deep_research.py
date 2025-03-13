import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.deep_research import (
    generate_serp_queries, 
    process_serp_result, 
    deep_research,
    write_final_report,
    write_final_answer
)

class TestDeepResearch(unittest.TestCase):
    """测试深度研究功能"""
    
    def setUp(self):
        """测试前准备"""
        # 创建事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
    
    def tearDown(self):
        """测试后清理"""
        self.loop.close()
    
    @patch('src.deep_research.get_model')
    @patch('src.deep_research.generate_object')
    def test_generate_serp_queries(self, mock_generate_object, mock_get_model):
        """测试生成搜索查询"""
        # 模拟返回值
        mock_generate_object.return_value = {
            "queries": [
                {"query": "test query 1", "researchGoal": "goal 1"},
                {"query": "test query 2", "researchGoal": "goal 2"}
            ]
        }
        
        # 执行函数
        result = self.loop.run_until_complete(
            generate_serp_queries("test prompt", num_queries=2)
        )
        
        # 验证结果
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["query"], "test query 1")
        self.assertEqual(result[1]["researchGoal"], "goal 2")
    
    @patch('src.deep_research.get_model')
    @patch('src.deep_research.generate_object')
    def test_process_serp_result(self, mock_generate_object, mock_get_model):
        """测试处理搜索结果"""
        # 模拟返回值
        mock_generate_object.return_value = {
            "learnings": ["fact 1", "fact 2"],
            "followUpQuestions": ["question 1", "question 2"]
        }
        
        # 模拟搜索结果
        serp_result = {
            "data": [
                {
                    "title": "Test Title",
                    "url": "https://example.com",
                    "content": "Test content"
                }
            ]
        }
        
        # 执行函数
        result = self.loop.run_until_complete(
            process_serp_result("test query", serp_result)
        )
        
        # 验证结果
        self.assertEqual(len(result["learnings"]), 2)
        self.assertEqual(result["learnings"][0], "fact 1")
        self.assertEqual(len(result["followUpQuestions"]), 2)
        self.assertEqual(result["followUpQuestions"][0], "question 1")
    
    @patch('src.deep_research.search_client')
    @patch('src.deep_research.generate_serp_queries')
    @patch('src.deep_research.process_serp_result')
    def test_deep_research(self, mock_process_serp, mock_generate_queries, mock_search_client):
        """测试深度研究功能"""
        # 模拟查询生成
        mock_generate_queries.return_value = [
            {"query": "test query", "researchGoal": "test goal"}
        ]
        
        # 模拟搜索客户端
        mock_search = AsyncMock()
        mock_search.return_value = {
            "data": [{"url": "https://example.com", "content": "test content"}]
        }
        mock_search_client.search = mock_search
        
        # 模拟处理结果
        mock_process_serp.return_value = {
            "learnings": ["fact 1", "fact 2"],
            "followUpQuestions": ["question 1"]
        }
        
        # 执行函数
        result = self.loop.run_until_complete(
            deep_research("test query", breadth=1, depth=1)
        )
        
        # 验证结果
        self.assertIn("learnings", result)
        self.assertIn("visitedUrls", result)
        self.assertEqual(len(result["learnings"]), 2)
        self.assertEqual(len(result["visitedUrls"]), 1)
    
    @patch('src.deep_research.get_model')
    def test_write_final_report(self, mock_get_model):
        """测试生成最终报告"""
        # 模拟模型配置
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = "Test report"
        mock_client.chat.completions.create.return_value = mock_response
        
        mock_get_model.return_value = {
            "client": mock_client,
            "model": "test-model"
        }
        
        # 执行函数
        result = self.loop.run_until_complete(
            write_final_report(
                prompt="test query",
                learnings=["fact 1", "fact 2"],
                visited_urls=["https://example.com"]
            )
        )
        
        # 验证结果
        self.assertEqual(result, "Test report")
        
        # 验证调用
        mock_client.chat.completions.create.assert_called_once()

if __name__ == '__main__':
    unittest.main() 