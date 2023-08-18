FROM python:3.10

WORKDIR /VLA_LLM

COPY . /VLA_LLM

RUN pip install -e .
