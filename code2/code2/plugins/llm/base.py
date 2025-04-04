"""
Base LLM plugin which you can inherit from.

Plugins register themselves over the ``code2_llm`` entrypoint.

To create your own plugin, create a Python package with an entrypoint like:

.. code-block:: python

    'code2_llm': [
        'plugin_name = your.module:ClassName',
    ]

See :py:class:`code2.plugins.llm.litellm` for an example.
"""
import cli2


cli2.cfg.defaults.update(dict(
    MODEL='litellm openrouter/deepseek/deepseek-chat max_tokens=16384 temperature=.7 top_p=.9',  # noqa
))

class LLMPlugin:
    """"
    .. envvar:: MODEL

        An environment variable to configure the default LLM plugin, as far as
        the base plugin is concerned, it must be in the following format::

            <llm plugin name> <llm plugin model configuration string>...

        The first token of the string will be used to load the code2 LLM plugin
        by name, the rest of the string will be used at the discretion of the
        plugin, refere to the plugin documentation for details.

        If the first token of the string is not a registered code2 plugin and
        does not contain a slash, we will consider that you want the
        :py:class:`code2.plugins.llm.litellm` plugin by default, which works
        really great for most cases, supports environment variables for
        configuration very well.

        Example values:

        .. code-block:: bash

            # litellm will be called by default
            MODEL='openrouter/deepseek/deepseek-chat'

            # first token in the model configuration string will be used for
            # model name, the rest will be parsed as kwargs:
            MODEL='litellm openrouter/deepseek/deepseek-chat max_tokens=16384'

            # If you have defined your own custom llm plugin, ie. named
            # "custom", to use an air-gapped IA with a custom API, enable it
            # explicitely
            MODEL='custom stuff that custom will parse'

    .. envvar:: MODEL_OTHER

        This is not a real environment variable name, this would be something
        like ``MODEL_ARCHITECT``, ``MODEL_CHAT``, ``MODEL_CHEAP``, or whatever.
        This system allows to define different models within a given flow
        dependending on the call purpose based on the
        :py:arg:`completion.models` argument.

        See this link for reasons to do this:

        https://aider.chat/2024/09/26/architect.html
    """

    @classmethod
    def factory(cls, *tokens):
        args = list()
        kwargs = dict()

        for token in tokens:
            if '=' in token:
                key, value = token.split('=')
                try:
                    value = int(value)
                except ValueError:
                    try:
                        value = float(value)
                    except ValueError:
                        pass
                kwargs[key] = value
            else:
                args.append(token)

        return cls(*args, **kwargs)

    async def completion(self, messages):
        """
        Request completion for a list of messages for an assist plugin.

        :param message: Messages dict list
        """
        raise NotImplemented()
