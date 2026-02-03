# Prompt Utils

Desktop utility to bundle selected files/directories into an AI-friendly format and copy to clipboard.

## What it does
- Select files and/or directories
- Builds a tree summary
- Concatenates contents with clear file boundaries (Markdown + code fences)
- Skips binaries and large files
- Optional ignores (default ignores + `.gitignore` support)
- Preview + Copy to clipboard

---

## Requirements
- Python 3.10+
- Platforms: 
    - Linux (tested on Ubuntu 22.04)
    - Windows (tested on W11)
    - macOS

---

## Run locally (from source)

### Linux (Ubuntu) / macOS
```bash
python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
pip install -e .
python -m prompt_utils_app
```

### Windows

```bat
py -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\pip install -e .
.\.venv\Scripts\python -m prompt_utils_app
```

Tip: run without a console window:

```bat
.\.venv\Scripts\pythonw -m prompt_utils_app
```

---

## Using the app

1. Click **Add files…** and/or **Add directory…**
2. Toggle options (tree, contents, ignore behavior, max size)
3. Click **Build preview**
4. Click **Copy to clipboard**

---

## Development

Install dev tools (lint + tests):

```bash
pip install -e ".[dev]"
```

Run lint:

```bash
ruff check .
```

Run tests:

```bash
pytest -q
```

---

## Roadmap

* Sensitive info detection + masking
* Prompt history (SQLite)
* Prompt templates with placeholders
* Packaging (PyInstaller) + installers

