from pathlib import Path

from prompt_utils_core import BundleOptions, build_bundle


def test_bundle_includes_tree_and_contents(tmp_path: Path) -> None:
    a = tmp_path / "a.py"
    b = tmp_path / "sub" / "b.txt"
    b.parent.mkdir()

    a.write_text("print('hi')\n", encoding="utf-8")
    b.write_text("hello\n", encoding="utf-8")

    # The new bundler expects a flat list of files, it does not recurse.
    files = [a, b]
    
    out = build_bundle(files, BundleOptions(max_file_bytes=200_000))

    assert "## Tree" in out
    assert "a.py" in out
    assert "b.txt" in out
    assert "print('hi')" in out
    assert "hello" in out


def test_binary_files_are_skipped(tmp_path: Path) -> None:
    f = tmp_path / "bin.dat"
    f.write_bytes(b"\x00\x01\x02not text")

    out = build_bundle([f], BundleOptions(max_file_bytes=200_000))
    assert "SKIPPED (looks like binary)" in out