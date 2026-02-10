from pathlib import Path

from prompt_utils_core.ignore_utils import build_ignore_spec, is_file_ignored


def test_default_ignores_skip_node_modules(tmp_path: Path) -> None:
    node_modules = tmp_path / "node_modules"
    node_modules.mkdir()
    bad_file = node_modules / "x.js"
    good_file = tmp_path / "keep.py"
    
    # We test the ignore logic directly
    # 1. Build the spec based on the root
    ignore_root, spec = build_ignore_spec([tmp_path], use_defaults=True, respect_gitignore=False)
    
    assert ignore_root == tmp_path
    assert spec is not None

    # 2. Check files
    assert is_file_ignored(bad_file, ignore_root, spec) is True
    assert is_file_ignored(good_file, ignore_root, spec) is False


def test_gitignore_skips_patterns(tmp_path: Path) -> None:
    # simulate a repo by adding .git directory + .gitignore
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")

    secret = tmp_path / "secret.txt"
    ok = tmp_path / "ok.txt"

    # respect_gitignore=True
    ignore_root, spec = build_ignore_spec([tmp_path], use_defaults=False, respect_gitignore=True)

    assert ignore_root == tmp_path
    assert spec is not None

    assert is_file_ignored(secret, ignore_root, spec) is True
    assert is_file_ignored(ok, ignore_root, spec) is False