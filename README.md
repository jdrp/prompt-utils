# Prompt Utils

Desktop utility to bundle selected files/directories into an AI-friendly format and copy to clipboard.

## Current features (v0.1)
- Select files and/or directories
- Tree summary
- Concatenated contents with clear file boundaries
- Skips binaries and large files
- Preview + Copy to clipboard

## Roadmap
- Ignore rules (.gitignore + presets)
- Sensitive info detection + masking
- Prompt history (SQLite)
- Prompt templates with placeholders

## Run locally
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
prompt-utils
```