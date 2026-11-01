from app.services.llm_cache import make_cache_key


def test_cache_key_is_deterministic_for_same_inputs():
    assert make_cache_key("model", "system", "prompt") == make_cache_key(
        "model",
        "system",
        "prompt",
    )


def test_cache_key_changes_for_model_prompt_or_version():
    base = make_cache_key("model", "system", "prompt", "v1")

    assert make_cache_key("other-model", "system", "prompt", "v1") != base
    assert make_cache_key("model", "system", "other prompt", "v1") != base
    assert make_cache_key("model", "system", "prompt", "v2") != base


def test_cache_key_separates_system_prompt_from_user_prompt():
    first = make_cache_key("model", "system|prompt", "value")
    second = make_cache_key("model", "system", "prompt|value")

    assert first != second
