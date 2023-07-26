# VLA-LLM

This repository uses LangChain to create a virtual leasing agent that can answer prospect questions and book tours
using a large language model.

## Installation

To install the package, create and activate a virtual environment, then run

```
pip install -e .
```

To run the notebooks, install the extra requirements:

```
pip install -r requirements
```

If you want to use the OpenAI models, copy `.env.example` to `.env` and fill in with your OpenAI API key.

You may also need to enter your Chuck API key so that the Funnel VLA API can be called.

To run a notebook, spin up a Jupyter server and open up a notebook in the `notebooks` directory:

```
jupyter notebook
```
