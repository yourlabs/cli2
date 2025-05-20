from setuptools import setup


setup(
    name='prompt2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'cli2',
        'template2',
    ],
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/cli2',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'prompt2 = prompt2.cli:cli.entry_point',
        ],
        'prompt2_parser': [
            'list = prompt2.parser:List',
            'wholefile = prompt2.parser:Wholefile',
        ],
        'prompt2': [
            'litellm = prompt2.plugins.litellm:LiteLLMPlugin',
        ],
        'template2': [
            'prompt2 = prompt2.template2:PromptTemplatePlugin',
        ],
        'flow2': [
            'prompt = prompt2.flow2:PromptPlugin',
        ],
        'pytest11': [
            'prompt2 = prompt2.pytest',
        ],
    },
)
