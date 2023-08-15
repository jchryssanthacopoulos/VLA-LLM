# VLA-LLM

This repository uses LangChain to create a virtual leasing agent that can answer prospect questions and book tours
using a large language model.

## Installation

To install the package, create and activate a virtual environment, then run

```
pip install -e .
```

To set the environment variables, copy `.env.example` to `.env` and fill in with your information.

To spin up the server, run

```
uvicorn main:app --reload
```

## Notebooks

To run the notebooks, install the extra requirements:

```
pip install -r requirements
```

Then spin up a Jupyter server and open up a notebook in the `notebooks` directory:

```
jupyter notebook
```
