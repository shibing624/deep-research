import os
import tempfile
import unittest
import yaml
from src.config import load_config, get_config, DEFAULT_CONFIG


class TestConfig(unittest.TestCase):
    """测试配置加载和管理功能"""

    def setUp(self):
        """测试前准备"""
        # 创建临时配置文件
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "test_config.yaml")

        # 测试配置数据
        self.test_config = {
            "api": {
                "port": 5000
            },
            "openai": {
                "api_key": "test_key",
                "model": "test_model"
            },
            "research": {
                "default_breadth": 5,
                "default_depth": 3
            }
        }

        # 写入测试配置文件
        with open(self.config_path, 'w') as f:
            yaml.dump(self.test_config, f)

    def tearDown(self):
        """测试后清理"""
        self.temp_dir.cleanup()

    def test_load_config_from_file(self):
        """测试从文件加载配置"""
        config = load_config(self.config_path)

        # 验证配置值
        self.assertEqual(config["api"]["port"], 5000)
        self.assertEqual(config["openai"]["api_key"], "test_key")
        self.assertEqual(config["openai"]["model"], "test_model")
        self.assertEqual(config["research"]["default_breadth"], 5)
        self.assertEqual(config["research"]["default_depth"], 3)

        # 验证默认值保留
        self.assertEqual(config["openai"]["base_url"], DEFAULT_CONFIG["openai"]["base_url"])

    def test_get_config(self):
        """测试获取配置"""
        # 先加载配置
        load_config(self.config_path)

        # 然后获取配置
        config = get_config()

        # 验证配置值
        self.assertEqual(config["api"]["port"], 5000)
        self.assertEqual(config["openai"]["api_key"], "test_key")

    def test_env_vars_override(self):
        """测试环境变量覆盖配置文件"""
        # 设置环境变量
        os.environ["OPENAI_KEY"] = "env_test_key"
        os.environ["CONTEXT_SIZE"] = "200000"

        # 加载配置
        config = load_config(self.config_path)

        # 验证环境变量覆盖
        self.assertEqual(config["openai"]["api_key"], "env_test_key")
        self.assertEqual(config["research"]["context_size"], 200000)

        # 清理环境变量
        del os.environ["OPENAI_KEY"]
        del os.environ["CONTEXT_SIZE"]


if __name__ == '__main__':
    unittest.main()
