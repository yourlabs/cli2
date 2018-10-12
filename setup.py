from setuptools import setup
import os


# Utility function to read the README file.
# Used for the long_description. It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = os.getenv('VERSION', '@VERSION')


setup(
    name='clilabs',
    version=VERSION,
    description='Cheap CLI framework, gives rich commands for Django',
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/clilabs',
    packages=['clilabs'],
    include_package_data=True,
    long_description=read('README.md'),
    license='MIT',
    keywords='django cli',
    entry_points={
        'console_scripts': [
            'clilabs = clilabs:cli',
        ],
    },
    install_requires=['tabulate'],
    classifiers=[
        'Development Status :: 1 - Planning',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
    ],
    python_requires='>=3',
)
