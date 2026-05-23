import pytest
from config import ZHIPU_API_KEY, GLM_MODEL, SAMPLE_RATE, CHANNELS


class TestConfig:
    def test_api_key_exists(self):
        assert ZHIPU_API_KEY is not None
        assert len(ZHIPU_API_KEY) > 0

    def test_model_name(self):
        assert GLM_MODEL == "glm-4-flash"

    def test_sample_rate(self):
        assert SAMPLE_RATE == 16000

    def test_channels(self):
        assert CHANNELS == 1
