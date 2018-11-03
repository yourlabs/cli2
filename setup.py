from setuptools import setup
import os


# Utility function to read the README file.
# Used for the long_description. It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


VERSION = '@VERSION'


setup(
    name='clilabs',
    version=VERSION if '@' not in VERSION else 'dev',
    description='Cheap CLI framework, gives rich commands for Django',
    author='James Pic',
    author_email='jamespic@gmail.com',
    url='https://yourlabs.io/oss/clilabs',
    packages=['clilabs'],
    include_package_data=True,
    long_description=read('README.rst'),
    license='MIT',
    keywords='django cli',
    entry_points={
        'console_scripts': [
            'clilabs = clilabs:cli',
        ],
    },
    install_requires=['tabulate', 'processcontroller'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'Environment :: Plugins',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3 :: Only',
        'Topic :: Database',
        'Topic :: Software Development',
        'Topic :: System',
        'Topic :: Terminals',
    ],
    python_requires='>=3',
)
