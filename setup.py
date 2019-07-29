from setuptools import setup, find_packages
from os import path

__version__ = "0.0.2"

here = path.abspath(path.dirname(__file__))

with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="pathmagic",
    version=__version__,
    description="Provides ORM path classes (File and Dir), which automatically emit file system IO operations upon having their attributes modified. File objects allow for easy content manipulation of many forms of files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/matthewgdv/pathmagic",
    license="MIT",
    classifiers=[
      "Development Status :: 3 - Alpha",
      "Intended Audience :: Developers",
      "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        'Pillow',
        'PyPDF2',
        'appdirs',
        'bs4',
        'dill',
        'docx',
        'lazy_property',
        'maybe',
        'moviepy',
        'pydub',
        'subtypes'
    ],
    author="Matt GdV",
    author_email="matthewgdv@gmail.com"
)
