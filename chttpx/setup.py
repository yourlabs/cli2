from setuptools import setup


setup(
    name='chttpx',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['chttpx'],
    install_requires=[
        'cli2',
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
            'chttpx-example = chttpx.example:cli.entry_point',
        ],
    },
)
