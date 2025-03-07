from setuptools import setup


setup(
    name='cli2-httpx',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['chttpx'],
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
            'cli2-httpx-example = chttpx.example:cli.entry_point',
        ],
    },
)
