# Vector-less RAG with PageIndex

This repository shows an end-to-end, reasoning-based RAG workflow using [PageIndex](https://github.com/VectifyAI/PageIndex) and a local Ollama model.

The pipeline in this repo:

1. Parse a PDF into a hierarchical tree index (PageIndex)
2. Select relevant nodes from the tree (LLM-guided tree search)
3. Extract node text as grounded context
4. Generate a final answer from only the retrieved context

## Project Structure

- `vector_less_RAG_optimized.py` - main end-to-end async RAG pipeline
- `vector_less_RAG_pageindex.ipynb` - notebook version of the workflow
- `PageIndex/` - local PageIndex package/code
- `PageIndex/run_pageindex.py` - CLI to build tree structure from PDF/Markdown
- `PageIndex/pageindex/config.yaml` - parsing and model configuration
- `requirements.txt` - Python dependencies

## Prerequisites

- Python 3.10+ (repo `pyproject.toml` targets newer versions; 3.10+ is generally fine)
- [Ollama](https://ollama.com/) installed and running locally
- A pulled Ollama model (configured default is `qwen3.5:0.8b`)
- A PageIndex API key (used in `vector_less_RAG_optimized.py` via env var `pageindex_api_key`)

## Installation

1) Clone and enter the project:

```bash
git clone <your-repo-url>
cd vector_less_RAG
```

2) Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3) Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

4) Create `.env` in project root:

```bash
pageindex_api_key=YOUR_PAGEINDEX_API_KEY
```

5) Start Ollama and pull model (first time only):

```bash
ollama serve
ollama pull qwen3.5:0.8b
```

Note: `vector_less_RAG_optimized.py` uses OpenAI-compatible local endpoint:
- base URL: `http://localhost:11434/v1`
- model default: `llama3:latest` inside `call_llm()`

If you keep `qwen3.5:0.8b` locally, update the model argument in `call_llm()` or pull `llama3:latest`.

## End-to-End Pipeline

### Step 1: Add your PDF

Place your PDF in `data/`, for example:

- `data/entropy-22-00193.pdf`

### Step 2: (Optional) Build tree structure locally with PageIndex CLI

Run:

```bash
python PageIndex/run_pageindex.py --pdf_path data/entropy-22-00193.pdf
```

Output is saved to:

- `PageIndex/results/<pdf_name>_structure.json`

Useful optional flags:

```bash
python PageIndex/run_pageindex.py \
  --pdf_path data/entropy-22-00193.pdf \
  --model "ollama/qwen3.5:0.8b" \
  --max-pages-per-node 2 \
  --max-tokens-per-node 800 \
  --if-add-node-id yes \
  --if-add-node-summary no \
  --if-add-node-text yes
```

### Step 3: Configure pipeline input in script

Open `vector_less_RAG_optimized.py` and update:

- `pdf_path` to your document path
- `doc_id` behavior:
  - first run: uncomment submit line and get fresh `doc_id`
  - later runs: reuse existing `doc_id` for faster iteration
- `query` string to your question

### Step 4: Run RAG pipeline

```bash
python vector_less_RAG_optimized.py
```

What happens at runtime:

1. Loads `.env` and creates `PageIndexClient`
2. Submits PDF (or uses existing `doc_id`)
3. Checks retrieval readiness
4. Fetches tree and prints document structure
5. Runs tree search prompt to select top nodes
6. Extracts text from selected nodes
7. Calls local LLM to answer using retrieved context only
8. Prints answer + debug info (nodes used, context length)

### Step 5: Notebook workflow (alternative)

Use `vector_less_RAG_pageindex.ipynb` if you want interactive, cell-by-cell execution.

## Common Issues and Fixes

- `Connection error to localhost:11434`  
  Ollama is not running. Start with `ollama serve`.

- `model not found`  
  Pull the model first: `ollama pull <model-name>`.

- `pageindex_api_key` is `None`  
  Ensure `.env` exists in repo root and variable name is exactly `pageindex_api_key`.

- Document still processing / not ready  
  Wait and rerun. Large PDFs can take longer.

- JSON parsing failure from tree-search LLM output  
  Script already has fallback logic that selects first few nodes.

## Recommended Run Order (Quick Start)

```bash
source .venv/bin/activate
ollama serve
python vector_less_RAG_optimized.py
```

Then iterate on:

- question (`query`)
- node/context limits (`MAX_NODES`, `MAX_CONTEXT_CHARS`)
- model choice in `call_llm()`
