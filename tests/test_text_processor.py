import json
import pytest
from unittest.mock import patch, MagicMock
from text_processor import TextProcessor


def _mock_response(text):
    resp = MagicMock()
    resp.read.return_value = json.dumps({
        "content": [{"text": text}],
    }).encode("utf-8")
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestTextProcessor:
    @patch("text_processor.urllib.request.urlopen")
    def test_improve_returns_corrected_text(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response("你好，世界！")

        proc = TextProcessor()
        result = proc.improve("你好世界")
        assert result == "你好，世界！"

    @patch("text_processor.urllib.request.urlopen")
    def test_improve_strips_whitespace(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response("  你好  ")

        proc = TextProcessor()
        result = proc.improve("你好")
        assert result == "你好"

    def test_improve_empty_input(self):
        proc = TextProcessor()
        result = proc.improve("")
        assert result == ""

    @patch("text_processor.urllib.request.urlopen")
    def test_improve_fallback_on_error(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("API error")

        proc = TextProcessor()
        result = proc.improve("原始文本")
        assert result == "原始文本"

    @patch("text_processor.urllib.request.urlopen")
    def test_improve_sends_correct_params(self, mock_urlopen):
        mock_urlopen.return_value = _mock_response("修正后")

        proc = TextProcessor()
        proc.improve("测试")

        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        body = json.loads(req.data.decode("utf-8"))
        assert body["model"] == "glm-5.1"
        assert body["max_tokens"] == 1024
        assert body["system"] is not None
        assert "修正" in body["system"]
        assert body["messages"][0]["content"] == "测试"
