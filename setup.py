from setuptools import setup


setup(
    name='cli2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'docstring_parser',
        'pyyaml',
        'pygments',
        'structlog',
    ],
    extras_require=dict(
        client=[
            'httpx',
            'truststore',
        ],
        test=[
            'freezegun',
            'pytest',
            'pytest-cov',
            'pytest-mock',
            'pytest-asyncio',
            'pytest-httpx',
        ],
    ),
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/cli2',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.6',
    entry_points={
        'console_scripts': [
            'cli2 = cli2.cli:main.entry_point',
            'cli2-example = cli2.example_obj:cli.entry_point',
            'cli2-example-nesting = cli2.example_nesting:cli.entry_point',
            'cli2-example-client = cli2.example_client:cli.entry_point',
            'cli2-example-client-complex = cli2.example_client_complex:cli.entry_point',
        ],
    },
)
