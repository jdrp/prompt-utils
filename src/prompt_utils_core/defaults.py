from __future__ import annotations


# File extension -> fenced code block language
LANG_BY_EXT: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".jsx": "jsx",
    ".json": "json",
    ".md": "markdown",
    ".toml": "toml",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".rs": "rust",
    ".sh": "bash",
    ".zsh": "zsh",
    ".txt": "text",
    ".html": "html",
    ".css": "css",
    ".xml": "xml",
    ".ini": "ini",
}

# Gitignore-style patterns (gitwildmatch) for common junk
DEFAULT_IGNORE_PATTERNS: tuple[str, ...] = (
    ".git/",
    ".hg/",
    ".svn/",
    "__pycache__/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".mypy_cache/",
    ".venv/",
    "venv/",
    "node_modules/",
    "dist/",
    "build/",
    ".next/",
    ".cache/",
    "target/",      # rust
    "*.egg-info/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
)

# Extensions to show in the UI
FILETYPE_CHOICES: tuple[tuple[str, str], ...] = (
    (".py", "Python"),
    (".js", "JavaScript"),
    (".ts", "TypeScript"),
    (".tsx", "TSX"),
    (".jsx", "JSX"),
    (".rs", "Rust"),
    (".sh", "Shell"),
    (".zsh", "Zsh"),
    (".json", "JSON"),
    (".toml", "TOML"),
    (".yml", "YAML (.yml)"),
    (".yaml", "YAML (.yaml)"),
    (".md", "Markdown"),
    (".txt", "Text"),
    (".html", "HTML"),
    (".css", "CSS"),
    (".xml", "XML"),
    (".ini", "INI"),
)