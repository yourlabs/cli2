from setuptools import setup


setup(
    name='template2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'cli2',
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
            'template2 = template2:cli.entry_point',
        ],
        'flow2_plugins': [
            'jinja2 = template2:TemplateTask',
        ],
    },
)
