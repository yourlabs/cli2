from setuptools import setup


setup(
    name='code2',
    versioning='dev',
    setup_requires='setupmeta',
    packages=['code2'],
    install_requires=[
        'cli2',
        'tree-sitter',
        'tree-sitter-language-pack',
        'litellm',
        'peewee',
        'markdown-it-py',
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
            'code2 = code2.cli:cli.entry_point',
        ],
        'code2_workflow': [
            'cmd = code2.workflows.cmd:CmdWorkflow',
            'analyze = code2.workflows.analyze:AnalyzeWorkflow',
            'edit = code2.workflows.edit:EditWorkflow',
            #'ask = code2.plugins.workflow.ask:AskWorkflow',
            #'hack = code2.plugins.workflow.hack:HackWorkflow',
            #'ask = code2.plugins.workflow.ask:AskWorkflow',
            #'create = code2.plugins.workflow.create:CreateWorkflow',
        ],
        'code2_parser': [
            'wholefile = code2.parser:Wholefile',
        ],
        'code2_jinja2': [
            'read = code2.jinja2:read',
        ],
        'code2_backend': [
            'litellm = code2.backends.litellm:LiteLLMBackend',
        ],
    },
)
