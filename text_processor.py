import json
import logging
import urllib.request

from config import ZHIPU_API_KEY, GLM_MODEL

API_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"


class TextProcessor:
    def __init__(self):
        self._api_key = ZHIPU_API_KEY

    def improve(self, raw_text: str) -> str:
        if not raw_text:
            return raw_text

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            }
            data = json.dumps({
                "model": GLM_MODEL,
                "max_tokens": 1024,
                "system": (
                    "你是一个语音输入后处理助手。用户给你一段语音识别的原始文本，"
                    "你需要：\n"
                    "1. 修正同音字错误和错别字\n"
                    "2. 添加正确的标点符号\n"
                    "3. 只输出修正后的文本，不要任何解释\n"
                    "如果原文已经正确，直接返回原文即可。"
                ),
                "messages": [{"role": "user", "content": raw_text}],
            }).encode("utf-8")

            req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
        except Exception as e:
            logging.warning("GLM 纠错失败: %s", e)
            return raw_text
