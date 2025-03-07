from setuptools import setup


setup(
    name='cli2-client',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['cclient'],
    install_requires=[
        'httpx',
        'truststore',
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
            'cli2-client-example = cclient.example:cli.entry_point',
        ],
    },
)
