from pathlib import Path
from prompt_utils_core import BundleOptions, build_bundle


def test_extension_filter_only_includes_selected(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_text("print('a')\n", encoding="utf-8")
    (tmp_path / "b.js").write_text("console.log('b')\n", encoding="utf-8")
    (tmp_path / "c.txt").write_text("nope\n", encoding="utf-8")

    out = build_bundle(
        [tmp_path],
        BundleOptions(include_extensions=(".py", ".js"), use_default_ignores=False, respect_gitignore=False),
    )

    assert "### File: a.py" in out
    assert "### File: b.js" in out
    assert "### File: c.txt" not in out
    assert "nope" not in out
