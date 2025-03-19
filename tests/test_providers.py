import unittest
from unittest.mock import patch, MagicMock
from src.providers import get_model, trim_prompt


class TestProviders(unittest.TestCase):
    """测试 providers 模块功能"""

    @patch('src.providers.get_config')
    @patch('src.providers.openai_client')
    def test_get_model(self, mock_openai_client, mock_get_config):
        """测试获取模型配置"""
        # 模拟配置
        mock_get_config.return_value = {
            "openai": {
                "model": "test-model"
            }
        }

        # 模拟 OpenAI 客户端
        mock_openai_client.__bool__.return_value = True

        # 获取模型配置
        model_config = get_model()

        # 验证结果
        self.assertEqual(model_config["client"], mock_openai_client)
        self.assertEqual(model_config["model"], "test-model")

    def test_trim_prompt_short(self):
        """测试短提示不需要裁剪"""
        prompt = "This is a short prompt"
        result = trim_prompt(prompt, context_size=1000)
        self.assertEqual(result, prompt)

    @patch('src.providers.encoder.encode')
    def test_trim_prompt_long(self, mock_encode):
        """测试长提示需要裁剪"""
        # 模拟编码器返回超长 token 数
        mock_encode.return_value = [0] * 2000

        prompt = "This is a very long prompt" * 100
        result = trim_prompt(prompt, context_size=1000)

        # 验证结果被裁剪
        self.assertLess(len(result), len(prompt))



if __name__ == '__main__':
    unittest.main()
