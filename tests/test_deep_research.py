import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import asyncio

from src.deep_research import (
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

if __name__ == '__main__':
    unittest.main()
