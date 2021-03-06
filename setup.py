import setuptools

from botw_flag_util.__version__ import VERSION

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="botw_flag_util",
    version=VERSION,
    author="Ginger",
    author_email="chodness@gmail.com",
    description="Game data and save game data flag utilities for LoZ:BotW",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/GingerAvalanche/botw_flag_util",
    include_package_data=True,
    packages=setuptools.find_packages(),
    entry_points={"console_scripts": ["botw_flag_util = botw_flag_util.__main__:main"]},
    classifiers=[
        "Programming Language :: Python :: 3.7",
        "License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
    ],
    python_requires=">=3.7.4",
    install_requires=["bcml>=3.0.0b25", "oead>=0.11.2"],
)
