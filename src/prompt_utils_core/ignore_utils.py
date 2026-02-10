from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable
from pathspec import PathSpec

from prompt_utils_core.defaults import DEFAULT_IGNORE_PATTERNS


def find_repo_root(start: Path) -> Path | None:
    """ Looks for closest parent with a .git directory """
    cur = start if start.is_dir() else start.parent
    for _ in range(30):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def load_gitignore_patterns(repo_root: Path) -> list[str]:
    """ Reads .gitignore if it exists """
    p = repo_root / ".gitignore"
    if not p.exists():
        return []
    lines: list[str] = []
    try:
        for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
            s = raw.strip()
            if s and not s.startswith("#"):
                lines.append(s)
    except OSError:
        pass
    return lines


def build_ignore_spec(roots: Iterable[Path], use_defaults: bool = True, respect_gitignore: bool = True) -> tuple[Path | None, PathSpec | None]:
    """
    Returns (ignore_root, spec). 
    Matches are calculated relative to ignore_root.
    """
    patterns: list[str] = []
    if use_defaults:
        patterns.extend(DEFAULT_IGNORE_PATTERNS)

    ignore_root: Path | None = None
    
    # try to find git root
    if respect_gitignore:
        for p in roots:
            # TODO handle edge case with multiple repos
            rr = find_repo_root(p)
            if rr is not None:
                ignore_root = rr
                patterns.extend(load_gitignore_patterns(rr))
                break

    # use common ancestor
    if ignore_root is None and patterns:
        try:
            resolved_roots = [p.resolve(strict=False) for p in roots]
            if resolved_roots:
                common = Path(os.path.commonpath(resolved_roots))

                if common.is_file():
                    ignore_root = common.parent
                else:
                    ignore_root = common

        except (OSError, ValueError):
            ignore_root = None
        
    if not patterns or ignore_root is None:
        return ignore_root, None
    
    spec = PathSpec.from_lines("gitignore", patterns)
    return ignore_root, spec


def is_file_ignored(path: Path, ignore_root: Path | None, spec: PathSpec | None) -> bool:
    if spec is None or ignore_root is None:
        return False
    
    try:
        rel = path.resolve(strict=False).relative_to(ignore_root.resolve(strict=False))
        rel_str = rel.as_posix()
    except ValueError:
        return False
    
    if path.is_dir():
        rel_str += "/"

    return spec.match_file(rel_str)