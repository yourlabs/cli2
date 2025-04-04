from setuptools import setup


setup(
    name='code2',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['code2'],
    install_requires=[
        'cli2',
        'tree-sitter',
        'tree-sitter-language-pack',
        'litellm',
        'rich',
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
            'code2 = code2.cli:cli.entry_point',
        ],
        'code2_assist': [
            'ask = code2.plugins.assist.ask:Ask',
            'analyze = code2.plugins.assist.analyze:Analyze',
            'hack = code2.plugins.assist.hack:Hack',
        ],
        'code2_llm': [
            'litellm = code2.plugins.llm.litellm:LiteLLM',
        ],
    },
)
