from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from prompt_utils_core.defaults import LANG_BY_EXT


@dataclass(frozen=True)
class BundleOptions:
    max_file_bytes: int = 200_000
    include_tree: bool = True
    include_file_contents: bool = True
    include_extensions: tuple[str, ...] = ()  # empty --> include all


# TODO refactor into a ContextBundle class


def build_bundle(selected_paths: Iterable[Path], options: BundleOptions) -> str:
    files = list(set(p for p in selected_paths if _is_extension_allowed(p, options)))
    files = sorted(files, key=lambda x: str(x).lower())
    root = _common_root(files)

    parts: list[str] = []
    parts.append("# AI Context Bundle")
    parts.append("")
    parts.append(f"- Files included: {len(files)}")
    parts.append(f"- Root: {root if root else '(mixed)'}")
    parts.append("")

    if options.include_tree:
        parts.append("## Tree")
        parts.append("```text")
        if files:
            for line in _tree_lines(files, root):
                parts.append(line)
        else:
            parts.append("(no files selected)")
        parts.append("```")
        parts.append("")

    if options.include_file_contents:
        parts.append("## Contents")
        parts.append("")

        root_path = Path(root) if root else None

        for f in files:
            display_path: str
            try:
                if root_path:
                    display_path = str(Path(str(f)).resolve().relative_to(root_path.resolve()))
                else:
                    display_path = str(f)
            except Exception:
                display_path = str(f)

            text, warning = _read_text_file(Path(str(f)), options.max_file_bytes)
            parts.append(f"### File: {display_path}")

            if warning is not None:
                parts.append(f"_({warning})_")
                parts.append("")
                continue

            lang = _guess_lang(Path(display_path))
            parts.append(f"```{lang}".rstrip())
            parts.append(text or "")
            parts.append("```")
            parts.append("")

    return "\n".join(parts).rstrip() + "\n"


def _looks_binary(sample: bytes) -> bool:
    """ Looks for NUL byte and checks if sample is mostly text characters """
    if not sample: 
        return False
    if b"\x00" in sample: 
        return True  # NUL byte

    text_score = sum(1 for b in sample if (
        b in (9, 10, 13) or  # \t \n \r
        32 <= b <= 126 or    # ASCII chars
        b >= 128             # UTF-8 multibyte chars
    ))

    return (text_score / len(sample)) < 0.80


def _guess_lang(path: Path) -> str:
    """ Returns the correct language annotation for each file type """
    return LANG_BY_EXT.get(path.suffix.lower(), "")


def _read_text_file(path: Path, max_bytes: int) -> tuple[Optional[str], Optional[str]]:
    """ Returns (file text, warning if skipped) """
    if not path.exists():
        return None, "SKIPPED (missing)"

    try:
        size = path.stat().st_size
    except OSError as e:
        return None, f"SKIPPED (stat failed): {e}"
    
    if size == 0:
        return "", None

    if size > max_bytes:
        return None, f"SKIPPED (too large: {size} bytes > {max_bytes})"

    try:
        with path.open("rb") as fh:
            data = fh.read(max_bytes + 1)
    except OSError as e:
        return None, f"SKIPPED (read failed): {e}"
    
    if len(data) > max_bytes:
        return None, f"SKIPPED (too large: > {max_bytes} bytes)"

    if _looks_binary(data[:4096]):
        return None, "SKIPPED (looks like binary)"

    return data.decode("utf-8", errors="replace"), None


def _common_root(files: list[Path]) -> str:
    """ Return common parent of all input paths, or "" if mixed (e.g. different drives). Used only for the bundle header. """
    dirs: list[str] = []
    for f in files:
        try:
            dirs.append(str(f.resolve().parent))
        except OSError:
            pass

    try:
        return os.path.commonpath(dirs)
    except ValueError:
        return ""
    

def _is_extension_allowed(path: Path, options: BundleOptions) -> bool:
    if not options.include_extensions:
        return True

    ext = path.suffix.lower()
    return ext in {e.lower() for e in options.include_extensions}
    

def _tree_lines(files: Iterable[Path], root: str) -> list[str]:
    """ Builds a minimal tree from a list of files, using relative paths to a common root if possible """
    tree: dict = {}

    for f in files:
        try:
            if root:
                rel = Path(str(f)).resolve().relative_to(Path(root).resolve())
                parts = list(rel.parts)
            else:
                parts = list(Path(str(f)).parts)
        except Exception:
            parts = [str(f)]
        if not parts:
            parts = [Path(str(f)).name]

        cur = tree
        for part in parts[:-1]:
            cur = cur.setdefault(part, {})
        cur.setdefault(parts[-1], None)

    lines: list[str] = []

    def walk(node: dict, prefix: str = "") -> None:
        items = list(node.items())
        for i, (name, child) in enumerate(items):
            is_last = i == len(items) - 1
            branch = "└── " if is_last else "├── "
            lines.append(prefix + branch + str(name))
            if isinstance(child, dict):
                extension = "    " if is_last else "│   "
                walk(child, prefix + extension)

    walk(tree, "")
    return lines
