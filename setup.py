"""Set up package."""

from setuptools import find_packages
from setuptools import setup


setup(
    name="VLA-LLM",
    description="Package for building a virtual leasing agent using large language models",
    url="https://github.com/jchryssanthacopoulos/VLA-LLM",
    packages=find_packages(),
    install_requires=[
        "langchain==0.0.240",
        "openai==0.27.8"
    ]
)
