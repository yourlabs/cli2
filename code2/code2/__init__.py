import cli2


cli2.cfg.defaults.update(dict(
    MODEL='litellm openrouter/deepseek/deepseek-chat max_tokens=16384 temperature=.7 top_p=.9',  # noqa
))
