import json
import logging
import ctypes
import urllib.request

from config import ZHIPU_API_KEY, GLM_MODEL
from asr_client import load_hotwords

API_URL = "https://open.bigmodel.cn/api/anthropic/v1/messages"


def _get_window_title():
    hwnd = ctypes.windll.user32.GetForegroundWindow()
    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


class TextProcessor:
    def __init__(self):
        self._api_key = ZHIPU_API_KEY
        self._hotwords = load_hotwords()

    def reload_hotwords(self):
        self._hotwords = load_hotwords()

    def improve(self, raw_text: str) -> str:
        if not raw_text:
            return raw_text

        system_prompt = (
            "你是一个语音输入后处理助手。用户给你一段语音识别的原始文本，"
            "你需要：\n"
            "1. 修正同音字错误和错别字\n"
            "2. 添加正确的标点符号\n"
            "3. 只输出修正后的文本，不要任何解释\n"
            "如果原文已经正确，直接返回原文即可。"
        )
        if self._hotwords:
            system_prompt += f"\n以下是用户的专业词汇参考：{self._hotwords}，请优先使用这些词的正确写法。"

        title = _get_window_title()
        if title:
            system_prompt += f"\n用户当前正在使用的软件窗口标题是「{title}」，请据此推断可能的领域语境。"

        try:
            headers = {
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            }
            data = json.dumps({
                "model": GLM_MODEL,
                "max_tokens": 1024,
                "system": system_prompt,
                "messages": [{"role": "user", "content": raw_text}],
            }).encode("utf-8")

            req = urllib.request.Request(API_URL, data=data, headers=headers, method="POST")
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode("utf-8"))
            return result["content"][0]["text"].strip()
        except Exception as e:
            logging.warning("GLM 纠错失败: %s", e)
            return raw_text
