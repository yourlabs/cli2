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
            'cli2 = cli2.cli2:main.entry_point',
            'cli2-example = cli2.examples.obj:cli.entry_point',
            'cli2-example2 = cli2.examples.obj2:cli.entry_point',
            'cli2-example-nesting = cli2.examples.nesting:cli.entry_point',
            'cli2-example-client = cli2.examples.client:cli.entry_point',
        ],
        'pytest11': [
            'cli2-ansible-fixtures = cli2.ansible.pytest',
        ],
    },
)
