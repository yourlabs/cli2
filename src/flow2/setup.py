from setuptools import setup


setup(
    name='flow2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'cli2',
        'pyyaml',
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
            'flow2 = flow2.cli:cli.entry_point',
        ],
        'flow2': [
            'serial = flow2.task:SerialTaskGroup',
            'parallel = flow2.task:ParallelTaskGroup',
        ],
    },
)
