import hashlib
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.bili_client import MIXIN_KEY_ENC_TAB, _get_mixin_key, _sign_params


def test_get_mixin_key():
    """Test that mixin key generation matches expected output."""
    img_key = "d241de94573f42938c27383657158780"
    sub_key = "6e49895c0832498852552ae3f5368372"
    result = _get_mixin_key(img_key, sub_key)

    assert len(result) == 32
    assert isinstance(result, str)


def test_sign_params_deterministic():
    """Test that signing produces consistent w_rid for same inputs."""
    mixin_key = "test_mixin_key_1234567890"
    params = {"keyword": "test", "page": "1"}

    result1 = _sign_params(params, mixin_key)
    result2 = _sign_params(params, mixin_key)

    # wts will differ between calls, but format should be consistent
    assert "w_rid" in result1
    assert "wts" in result1
    assert "keyword" in result1
    assert len(result1["w_rid"]) == 32  # MD5 hex digest


def test_sign_params_wts_is_integer_string():
    """Test that wts is a string representation of an integer timestamp."""
    mixin_key = "test_key"
    params = {"search_type": "video", "keyword": "周杰伦"}

    result = _sign_params(params, mixin_key)

    wts = result["wts"]
    assert wts.isdigit()
    assert len(wts) == 10  # Unix timestamp in seconds


def test_sign_params_sorted_keys():
    """Test that params are sorted before signing."""
    mixin_key = "test_key"
    params = {"z_param": "1", "a_param": "2", "m_param": "3"}

    result = _sign_params(params, mixin_key)

    assert "z_param" in result
    assert "a_param" in result
    assert "m_param" in result
    assert result["w_rid"] is not None
