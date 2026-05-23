import sys
import logging

from config import ZHIPU_API_KEY
from app import VoiceInputApp


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if not ZHIPU_API_KEY:
        logging.error("请先设置 ZHIPU_API_KEY（config.py 或环境变量）")
        logging.error("获取: https://open.bigmodel.cn")
        sys.exit(1)

    logging.info("语音输入助手启动中...")
    logging.info("首次运行会加载 ASR 模型，请稍候")
    app = VoiceInputApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
