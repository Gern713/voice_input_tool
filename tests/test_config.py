import pytest
from config import ZHIPU_API_KEY, GLM_MODEL, SAMPLE_RATE, CHANNELS


class TestConfig:
    def test_api_key_is_string(self):
        assert isinstance(ZHIPU_API_KEY, str)

    def test_model_name(self):
        assert GLM_MODEL == "glm-5.1"

    def test_sample_rate(self):
        assert SAMPLE_RATE == 16000

    def test_channels(self):
        assert CHANNELS == 1
