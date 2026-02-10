from pathlib import Path
from prompt_utils_core import BundleOptions, build_bundle


def test_extension_filter_only_includes_selected(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "b.js"
    c = tmp_path / "c.txt"

    a.write_text("print('a')\n", encoding="utf-8")
    b.write_text("console.log('b')\n", encoding="utf-8")
    c.write_text("nope\n", encoding="utf-8")

    # Pass all files; the bundler is responsible for filtering by extension
    files = [a, b, c]

    out = build_bundle(
        files,
        BundleOptions(include_extensions=(".py", ".js")),
    )

    assert "### File: a.py" in out
    assert "### File: b.js" in out
    assert "### File: c.txt" not in out
    assert "nope" not in out