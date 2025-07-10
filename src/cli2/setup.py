from setuptools import setup

# We're not having that for the moment
# from setuptools.command.install import install
# from setuptools.command.develop import develop
# from pathlib import Path
# import os
# import shutil
# import sys
#
#
# class CollectionInstaller:
#     @property
#     def collection_target(self):
#         target = Path(os.getenv('HOME'))
#         target /= '.ansible/collections/ansible_collections/yourlabs/cli2'
#         return target
#
#
# class Develop(CollectionInstaller, develop):
#     def run(self):
#         super().run()
#
#         source = Path(self.egg_path) / 'cli2/ansible/collection'
#         if self.collection_target.exists():
#             if self.collection_target.is_symlink():
#                 if self.collection_target.resolve() == source:
#                     return
#             elif self.collection_target.is_dir():
#                 shutil.rmtree(self.collection_target)
#
#         self.collection_target.parent.mkdir(exist_ok=True, parents=True)
#         self.collection_target.symlink_to(source)
#
#
# class Install(CollectionInstaller, install):
#     def run(self):
#         super().run()
#
#         self.collection_target.parent.mkdir(exist_ok=True, parents=True)
#         source = Path(self.install_lib) / 'cli2/ansible/collection'
#         shutil.copytree(source, self.collection_target, dirs_exist_ok=True)


setup(
    name='cli2',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['cli2'],
    install_requires=[
        'docstring_parser',
        'pyyaml',
        'pygments',
        'structlog',
        'aiofiles',
    ],
    extras_require=dict(
        httpx=['chttpx'],
        ansible=['cansible'],
        test=[
            'freezegun',
            'pytest',
            'pytest-cov',
            'pytest-mock',
            'pytest-asyncio',
            'pytest-httpx',
            'pytest-env',
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
            'cli2-theme = cli2.theme:main',
            'cli2-traceback = cli2.examples.traceback_demo:main',
            'cli2-example = cli2.examples.obj:cli.entry_point',
            'cli2-example2 = cli2.examples.obj2:cli.entry_point',
            'cli2-example-nesting = cli2.examples.nesting:cli.entry_point',
            'cli2-example-client = cli2.examples.client:cli.entry_point',
        ],
        'flow2': [
            'find = cli2.flow2:FindPlugin',
        ],
        'template2': [
            'cli2 = cli2.template2:Cli2Template2Plugin',
        ],
    },
    # cmdclass={
    #     'install': Install,
    #     'develop': Develop,
    # },
)
