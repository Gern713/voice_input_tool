from zhipuai import ZhipuAI
from config import ZHIPU_API_KEY, GLM_MODEL


class TextProcessor:
    def __init__(self):
        self.client = ZhipuAI(api_key=ZHIPU_API_KEY)

    def improve(self, raw_text: str) -> str:
        if not raw_text:
            return raw_text

        try:
            resp = self.client.chat.completions.create(
                model=GLM_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是一个语音输入后处理助手。用户给你一段语音识别的原始文本，"
                            "你需要：\n"
                            "1. 修正同音字错误和错别字\n"
                            "2. 添加正确的标点符号\n"
                            "3. 只输出修正后的文本，不要任何解释\n"
                            "如果原文已经正确，直接返回原文即可。"
                        ),
                    },
                    {"role": "user", "content": raw_text},
                ],
                temperature=0.1,
                max_tokens=1024,
            )
            return resp.choices[0].message.content.strip()
        except Exception:
            return raw_text
