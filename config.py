import os

# ZhiPu AI API (智谱AI)
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
GLM_MODEL = "glm-5.1"

# ASR settings
SAMPLE_RATE = 16000
CHANNELS = 1

# Hotwords
HOTWORDS_FILE = os.path.join(os.path.dirname(__file__), "hotwords.txt")

# Streaming ASR
CHUNK_SIZE = [0, 10, 5]
CHUNK_STRIDE = CHUNK_SIZE[1] * 960  # 9600 samples = 600ms
