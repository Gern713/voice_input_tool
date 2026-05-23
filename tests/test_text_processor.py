import pytest
from unittest.mock import patch, MagicMock
from text_processor import TextProcessor


class TestTextProcessor:
    @patch("text_processor.ZhipuAI")
    def test_improve_returns_corrected_text(self, mock_zhipu):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "你好，世界！"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_zhipu.return_value = mock_client

        proc = TextProcessor()
        result = proc.improve("你好世界")
        assert result == "你好，世界！"

    @patch("text_processor.ZhipuAI")
    def test_improve_strips_whitespace(self, mock_zhipu):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "  你好  "
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_zhipu.return_value = mock_client

        proc = TextProcessor()
        result = proc.improve("你好")
        assert result == "你好"

    @patch("text_processor.ZhipuAI")
    def test_improve_empty_input(self, mock_zhipu):
        proc = TextProcessor()
        result = proc.improve("")
        assert result == ""
        mock_zhipu.return_value.chat.completions.create.assert_not_called()

    @patch("text_processor.ZhipuAI")
    def test_improve_fallback_on_error(self, mock_zhipu):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API error")
        mock_zhipu.return_value = mock_client

        proc = TextProcessor()
        result = proc.improve("原始文本")
        assert result == "原始文本"

    @patch("text_processor.ZhipuAI")
    def test_improve_sends_correct_params(self, mock_zhipu):
        mock_client = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "修正后"
        mock_resp = MagicMock()
        mock_resp.choices = [mock_choice]
        mock_client.chat.completions.create.return_value = mock_resp
        mock_zhipu.return_value = mock_client

        proc = TextProcessor()
        proc.improve("测试")

        call_kwargs = mock_client.chat.completions.create.call_args
        assert call_kwargs.kwargs["temperature"] == 0.1
        assert call_kwargs.kwargs["max_tokens"] == 1024
        messages = call_kwargs.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert "修正" in messages[0]["content"]
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "测试"
