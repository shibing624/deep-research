#!/usr/bin/env python3
import unittest
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入测试模块
from tests.test_config import TestConfig
from tests.test_serper_client import TestSerperClient
from tests.test_providers import TestProviders
from tests.test_deep_research import TestDeepResearch


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    test_suite = unittest.TestSuite()

    # 添加测试类
    test_suite.addTest(unittest.makeSuite(TestConfig))
    test_suite.addTest(unittest.makeSuite(TestSerperClient))
    test_suite.addTest(unittest.makeSuite(TestProviders))
    test_suite.addTest(unittest.makeSuite(TestDeepResearch))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)

    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
