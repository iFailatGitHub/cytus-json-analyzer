from setuptools import setup

setup(
    name='cytus_analyzer',
    version='0.1',
    py_modules=['cli'],
    install_requires=[
        'Click', 'mutagen'
    ],
    entry_points='''
        [console_scripts]
        cytus_analyzer=cytus_analyzer:cli
    ''',
)