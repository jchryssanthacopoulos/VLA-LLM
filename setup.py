"""Set up package."""

from setuptools import find_packages
from setuptools import setup


setup(
    name="VLA-LLM",
    description="Package for building a virtual leasing agent using large language models",
    url="https://github.com/jchryssanthacopoulos/VLA-LLM",
    packages=find_packages(),
    install_requires=[
        "langchain==0.0.264",
        "pydantic==1.10.12",
        "python-dotenv==1.0.0",
        "openai==0.27.8",
        "fastapi==0.101.1",
        "uvicorn==0.23.2",
        "redis-om==0.2.1",
        "pytz==2022.1",
        "dateparser==1.1.1",
        "tiktoken==0.4.0"
    ]
)
