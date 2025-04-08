from setuptools import setup


setup(
    name='prompt2',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['prompt2'],
    install_requires=[
        'cli2',
        'markdown-it-py',
        'jinja2',
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
            'wholefile = prompt2.parser:Wholefile',
            'list = prompt2.parser:List',
        ],
        'prompt2_globals': [
            'read = prompt2.jinja2:read',
            'shell = prompt2.jinja2:shell',
        ],
        'prompt2_backend': [
            'litellm = prompt2.backends.litellm:LiteLLMBackend',
        ],
        'pytest11': [
            'prompt2 = prompt2.pytest',
        ],
    },
)
