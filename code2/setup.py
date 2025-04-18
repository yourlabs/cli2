from setuptools import setup


setup(
    name='code2',
    versioning='dev',
    setup_requires='setupmeta',
    install_requires=[
        'cli2',
        'tree-sitter',
        'tree-sitter-language-pack',
        'sqlalchemy[asyncio]',
        'prompt2',
        'aiosqlite',
        'aiofile',
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
            'inspect = code2.workflows.inspect:InspectWorkflow',
            #'hack = code2.plugins.workflow.hack:HackWorkflow',
            #'edit = code2.workflows.edit:EditWorkflow',
            #'edit = code2.workflows.edit:EditWorkflow',
            #'ask = code2.plugins.workflow.ask:AskWorkflow',
            #'ask = code2.plugins.workflow.ask:AskWorkflow',
            #'create = code2.plugins.workflow.create:CreateWorkflow',
        ],
        'prompt2_paths': [
            'code2 = code2.prompt2:paths',
        ],
        'prompt2_globals': [
            'project = code2.prompt2:project',
            'symbols_src = code2.prompt2:symbols_src',
        ],
    },
)
