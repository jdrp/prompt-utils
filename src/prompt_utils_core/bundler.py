from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple
from pathspec import PathSpec

from prompt_utils_core.defaults import DEFAULT_IGNORE_PATTERNS, LANG_BY_EXT


@dataclass(frozen=True)
class BundleOptions:
    max_file_bytes: int = 200_000
    include_tree: bool = True
    include_file_contents: bool = True

    use_default_ignores: bool = True
    respect_gitignore: bool = True
    extra_ignore_patterns: Tuple[str, ...] = ()

    include_extensions: Tuple[str, ...] = ()  # empty --> include all


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


def _read_text_file(path: Path, max_bytes: int) -> Tuple[Optional[str], Optional[str]]:
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


def _gather_files(selected: Iterable[Path], options: BundleOptions | None = None) -> List[Path]:
    """ Gets recursive list of directories, sorted and without duplicates """
    selected_list = list(selected)
    ignore_root, spec = (None, None)
    if options is not None:
        ignore_root, spec = _build_ignore_spec(selected_list, options)

    out: List[Path] = []
    for p in selected_list:
        try:
            if p.is_file():
                if _ext_allowed(p, options) and not _is_ignored(p, ignore_root, spec):
                    out.append(p)
                continue

            if p.is_dir():
                for dirpath, dirnames, filenames in os.walk(p, topdown=True, followlinks=False):
                    dpath = Path(dirpath)

                    # prune ignored subdirectories
                    kept_dirs: list[str] = []
                    for dn in dirnames:
                        candidate = dpath / dn
                        if not _is_ignored(candidate, ignore_root, spec):
                            kept_dirs.append(dn)
                    dirnames[:] = kept_dirs

                    for fn in filenames:
                        fpath = dpath / fn
                        if fpath.is_file() and _ext_allowed(fpath, options) and not _is_ignored(fpath, ignore_root, spec):
                            out.append(fpath)

        except OSError:
            # TODO handle permission issues
            continue

    out_unique = sorted({str(x.resolve(strict=False)) for x in out}, key=str.lower)
    return [Path(s) for s in out_unique]


def _common_root(files: List[Path]) -> str:
    """ Return common parent of all input paths, or "" if mixed (e.g. different drives) """
    if not files: 
        return ""

    dirs: List[str] = []
    for f in files:
        try:
            p = f.resolve(strict=False)
        except OSError:
            p = f
        dirs.append(str(p.parent))

    try:
        return os.path.commonpath(dirs)
    except ValueError:
        return ""
    

def _find_repo_root(start: Path) -> Path | None:
    """ Looks for closest parent with a .git directory """
    cur = start if start.is_dir() else start.parent
    for _ in range(30):
        if (cur / ".git").exists():
            return cur
        if cur.parent == cur:
            break
        cur = cur.parent
    return None


def _load_gitignore_patterns(repo_root: Path) -> List[str]:
    """ Reads .gitignore if it exists """
    p = repo_root / ".gitignore"
    if not p.exists():
        return []
    lines: list[str] = []
    for raw in p.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s or s.startswith("#"):
            continue
        lines.append(s)
    return lines


def _build_ignore_spec(selected: List[Path], options: BundleOptions) -> Tuple[Path | None, PathSpec | None]:
    """ Returns (ignore_root, spec). Matching is based on ignore_rood, and only applies if spec is not None """
    patterns: list[str] = []

    if options.use_default_ignores:
        patterns.extend(DEFAULT_IGNORE_PATTERNS)

    if options.extra_ignore_patterns:
        patterns.extend(options.extra_ignore_patterns)

    ignore_root: Path | None = None

    if options.respect_gitignore:
        for p in selected:
            rr = _find_repo_root(p)
            if rr is not None:
                ignore_root = rr
                patterns.extend(_load_gitignore_patterns(rr))
                break

    if ignore_root is None:
        gathered = _gather_files(selected)
        root_str = _common_root(gathered)
        ignore_root = Path(root_str) if root_str else None

    if not patterns:
        return ignore_root, None
    
    spec = PathSpec.from_lines("gitignore", patterns)
    return ignore_root, spec


def _ext_allowed(path: Path, options: BundleOptions | None) -> bool:
    if options is None:
        return True
    allowed = options.include_extensions
    if not allowed:
        return True

    ext = path.suffix.lower()
    return ext in {e.lower() for e in allowed}


def _is_ignored(path: Path, ignore_root: Path | None, spec: PathSpec | None) -> bool:
    if spec is None or ignore_root is None:
        return False
    
    try:
        rel = path.resolve(strict=False).relative_to(ignore_root.resolve(strict=False))
        rel_str = rel.as_posix()
    except Exception:
        rel_str = path.as_posix()

    return spec.match_file(rel_str)
    

def _tree_lines(files: List[Path], root: str) -> List[str]:
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

    lines: List[str] = []

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


def build_bundle(selected_paths: Iterable[Path], options: BundleOptions) -> str:
    files = _gather_files(selected_paths, options)
    root = _common_root(files)

    parts: List[str] = []
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