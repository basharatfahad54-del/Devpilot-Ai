from src.devpilot.config import OPENROUTER_API_KEY, get_config_summary


def test_config_summary():
    cfg = get_config_summary()
    assert isinstance(cfg, dict)
    assert "workspace" in cfg
    assert "model" in cfg
    assert "has_api_key" in cfg

def test_no_api_key_in_normal_env():
    # API key comes from env; in tests it may be unset - we just check format
    assert OPENROUTER_API_KEY is None or isinstance(OPENROUTER_API_KEY, str)
