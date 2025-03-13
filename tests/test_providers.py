import unittest
from unittest.mock import patch, MagicMock
from src.providers import get_model, trim_prompt, generate_object

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
    
    @patch('src.providers.get_model')
    def test_generate_object(self, mock_get_model):
        """测试生成结构化对象"""
        # 模拟模型配置
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '{"result": "test"}'
        mock_client.chat.completions.create.return_value = mock_response
        
        mock_get_model.return_value = {
            "client": mock_client,
            "model": "test-model"
        }
        
        # 生成对象
        result = generate_object(
            model_config=mock_get_model.return_value,
            system="test system",
            prompt="test prompt",
            schema=None
        )
        
        # 验证结果
        self.assertEqual(result, {"result": "test"})
        
        # 验证调用
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        self.assertEqual(kwargs["model"], "test-model")
        self.assertEqual(kwargs["messages"][0]["role"], "system")
        self.assertEqual(kwargs["messages"][1]["role"], "user")

if __name__ == '__main__':
    unittest.main() 