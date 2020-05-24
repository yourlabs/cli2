from setuptools import setup


setup(
    name='cli2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=['docstring_parser==0.7.1'],
    extras_require=dict(
        test=[
            'freezegun',
            'pytest',
            'pytest-cov',
        ],
    ),
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/cli2',
    include_package_data=True,
    license='MIT',
    keywords='cli',
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'cli2 = cli2.cli:main.entry_point',
        ],
    },
)
