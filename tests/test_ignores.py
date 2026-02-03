from pathlib import Path

from prompt_utils_core import BundleOptions, build_bundle


def test_default_ignores_skip_node_modules(tmp_path: Path) -> None:
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.js").write_text("bad\n", encoding="utf-8")
    (tmp_path / "keep.py").write_text("ok\n", encoding="utf-8")

    out = build_bundle([tmp_path], BundleOptions(use_default_ignores=True, respect_gitignore=False))
    assert "### File: keep.py" in out
    assert "bad" not in out


def test_gitignore_skips_patterns(tmp_path: Path) -> None:
    # simulate a repo by adding .git directory + .gitignore
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("secret.txt\n", encoding="utf-8")

    (tmp_path / "secret.txt").write_text("nope\n", encoding="utf-8")
    (tmp_path / "ok.txt").write_text("yep\n", encoding="utf-8")

    out = build_bundle([tmp_path], BundleOptions(use_default_ignores=False, respect_gitignore=True))
    assert "### File: ok.txt" in out
    assert "yep" in out
    assert "### File: secret.txt" not in out
    assert "nope" not in out