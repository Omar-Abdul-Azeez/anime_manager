from setuptools import setup


setup(
    name='anime_manager',
    version='1.0.4',
    packages=['anime'],
    url='https://github.com/Omar-Abdul-Azeez/anime_manager',
    install_requires=[
        'requests>=2.28',
        'regex>=2022.10.31',
        'rapidfuzz>=3.0',
        'cfscrape>=2.1',
        'PyQt5>=5.15'
    ],
    python_requires=">=3.9.0",
    author="Omar Abdul'Azeez",
    entry_points={
        "console_scripts": [
            "anime=anime.__main__:main",
        ]
    },
)
