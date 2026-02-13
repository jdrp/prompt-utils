from __future__ import annotations

import sys
from pathlib import Path
import traceback

from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtWidgets import QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox, QSplitter, QTextEdit, QTreeWidget, QVBoxLayout, QWidget

from prompt_utils_core import BundleOptions, build_bundle, AppConfig, load_config, save_config
from prompt_utils_core.defaults import FILETYPE_CHOICES
from prompt_utils_core.ignore_utils import build_ignore_spec, is_file_ignored
from .file_tree import FileTreeWidget, ReturnListIncludes


class BundleWorker(QObject):  # TODO move to bundler.py
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, selected: list[Path], options: BundleOptions) -> None:
        super().__init__()
        self.selected = selected
        self.options = options

    def run(self) -> None:
        try:
            out = build_bundle(self.selected, self.options)
            self.finished.emit(out)
        except Exception:
            self.failed.emit(traceback.format_exc())

# TODO apply FileTreeWidget changes

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.cfg: AppConfig = load_config()

        self.setWindowTitle("Prompt Utils")
        self.resize(1100, 700)

        self.selected: list[Path] = []
        self.preview_text: str = ""

        # Left: selection list + controls
        self.tree_widget = FileTreeWidget()
        self.tree_widget.setSelectionMode(QTreeWidget.ExtendedSelection)
        self.tree_widget.itemChanged.connect(self.refresh_preview)

        btn_add_files = QPushButton("Add files…")
        btn_add_dir = QPushButton("Add directory…")
        btn_remove = QPushButton("Remove selected")
        btn_clear = QPushButton("Clear")

        btn_add_files.clicked.connect(self.add_files)
        btn_add_dir.clicked.connect(self.add_directory)
        btn_remove.clicked.connect(self.remove_selected)
        btn_clear.clicked.connect(self.clear_all)

        # Options
        self.chk_tree = QCheckBox("Include tree summary")
        self.chk_tree.setChecked(self.cfg.include_tree)

        self.chk_contents = QCheckBox("Include file contents")
        self.chk_contents.setChecked(self.cfg.include_file_contents)

        self.chk_default_ignores = QCheckBox("Use default ignores")
        self.chk_default_ignores.setChecked(self.cfg.use_default_ignores)

        self.chk_gitignore = QCheckBox("Respect .gitignore (if found)")
        self.chk_gitignore.setChecked(self.cfg.respect_gitignore)

        self.chk_filter_ext = QCheckBox("Filter by file extension")
        self.chk_filter_ext.setChecked(self.cfg.filter_by_extension)

        self.ext_list = QListWidget()
        self.ext_list.setMaximumHeight(170)
        # TODO clean comments from here
        # populate extencion list
        selected = {e.lower() for e in self.cfg.selected_extensions}
        for ext, label in FILETYPE_CHOICES:
            item = QListWidgetItem(f"{label} ({ext})")
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if ext.lower() in selected else Qt.Unchecked)
            # store the extension on the item
            item.setData(Qt.UserRole, ext)
            self.ext_list.addItem(item)

        # enable/disable list based on checkbox
        self.ext_list.setEnabled(self.chk_filter_ext.isChecked())

        # If the user toggles/filter changes, update preview
        self.chk_default_ignores.toggled.connect(self._update_ignore_logic)
        self.chk_gitignore.toggled.connect(self._update_ignore_logic)
        self.chk_filter_ext.toggled.connect(self._on_filter_changed)
        self.ext_list.itemChanged.connect(self._on_filter_changed)
        self.chk_tree.toggled.connect(self.refresh_preview)
        self.chk_contents.toggled.connect(self.refresh_preview)

        self.max_bytes = QSpinBox()
        self.max_bytes.setRange(1_000, 10_000_000)
        self.max_bytes.setSingleStep(50_000)
        self.max_bytes.setValue(int(self.cfg.max_file_bytes))
        self.max_bytes.setSuffix(" bytes max/file")

        btn_refresh = QPushButton("Build preview")
        btn_copy = QPushButton("Copy to clipboard")
        btn_refresh.clicked.connect(self.refresh_preview)
        btn_copy.clicked.connect(self.copy_to_clipboard)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Selected paths"))
        left_layout.addWidget(self.tree_widget)

        row1 = QHBoxLayout()
        row1.addWidget(btn_add_files)
        row1.addWidget(btn_add_dir)
        left_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(btn_remove)
        row2.addWidget(btn_clear)
        left_layout.addLayout(row2)

        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("Options"))
        left_layout.addWidget(self.chk_tree)
        left_layout.addWidget(self.chk_contents)
        left_layout.addWidget(self.chk_default_ignores)
        left_layout.addWidget(self.chk_gitignore)
        left_layout.addWidget(self.chk_filter_ext)

        left_layout.addWidget(self.ext_list)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Limit"))
        row3.addWidget(self.max_bytes)
        left_layout.addLayout(row3)

        left_layout.addSpacing(10)
        row4 = QHBoxLayout()
        row4.addWidget(btn_refresh)
        row4.addWidget(btn_copy)
        left_layout.addLayout(row4)

        left_layout.addStretch(1)

        # Right: preview
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)  # TODO make it editable
        self.preview.setLineWrapMode(QTextEdit.NoWrap)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self.setCentralWidget(splitter)

        self._update_ignore_logic()
        self.refresh_preview()

    def _on_build_finished(self, text: str) -> None:
        self.preview_text = text
        self.preview.setPlainText(text)
        self.setEnabled(True)

    def _on_build_failed(self, err: str) -> None:
        self.preview_text = ""
        self.preview.setPlainText("Build failed:\n\n" + err)
        self.setEnabled(True)

    def _cleanup_build_thread(self) -> None:
        self._worker.deleteLater()
        self._build_thread.deleteLater()
        self._worker = None
        self._build_thread = None

    def _selected_extensions(self) -> tuple[str, ...]:
        if not self.chk_filter_ext.isChecked():
            return ()
        exts: list[str] = []
        for i in range(self.ext_list.count()):
            item = self.ext_list.item(i)
            if item.checkState() == Qt.Checked:
                exts.append(str(item.data(Qt.UserRole)))
        return tuple(exts)

    def _on_filter_changed(self, *args) -> None:
        self.ext_list.setEnabled(self.chk_filter_ext.isChecked())
        self.refresh_preview()

    def _update_ignore_logic(self, *args) -> None:
        """
        Constructs a checker function based on current roots and checkboxes,
        then pushes it to the tree.
        """
        use_defaults = self.chk_default_ignores.isChecked()
        respect_gitignore = self.chk_gitignore.isChecked()

        cache: dict[Path, bool] = {}

        def checker(path: Path) -> bool:
            if path in cache: 
                return cache[path] 
            root, spec = build_ignore_spec([path], use_defaults, respect_gitignore)  # TODO stop calling build_ignore_spec for every file (probably inefficient)
            res = is_file_ignored(path, root, spec)
            cache[path] = res
            return res
        
        self.tree_widget.set_ignore_checker(checker)
        self.tree_widget.refresh_ignore_state()
        self.refresh_preview()

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if not files:
            return
        for f in files:
            self.tree_widget.add_path(Path(f))
        self.refresh_preview()

    def add_directory(self) -> None:
        # TODO convert to add_directories (also change the button)
        d = QFileDialog.getExistingDirectory(self, "Select a directory")
        if not d:
            return
        self.tree_widget.add_path(Path(d))
        self.refresh_preview()

    def remove_selected(self) -> None:
        self.tree_widget.remove_selected_roots()
        self.refresh_preview()

    def clear_all(self) -> None:
        self.tree_widget.clear_all()
        self.refresh_preview()

    def refresh_preview(self) -> None:
        # prevent overlapping builds
        if getattr(self, "_build_thread", None) is not None:
            return
        
        files_to_bundle = self.tree_widget.get_checked_files(ReturnListIncludes.FILES_ONLY)
        if not files_to_bundle:
            self.preview_text = ""
            self.preview.setPlainText("(No files selected)")
            return

        options = BundleOptions(
            max_file_bytes=int(self.max_bytes.value()),
            include_tree=self.chk_tree.isChecked(),
            include_file_contents=self.chk_contents.isChecked(),
            include_extensions=self._selected_extensions(),
        )

        # update UI to show busy state
        self.preview.setPlainText("Building preview…")
        self.setEnabled(False)

        self._build_thread = QThread()
        self._worker = BundleWorker(files_to_bundle, options)
        self._worker.moveToThread(self._build_thread)

        self._build_thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._on_build_finished)
        self._worker.failed.connect(self._on_build_failed)

        # cleanup
        self._worker.finished.connect(self._build_thread.quit)
        self._worker.failed.connect(self._build_thread.quit)
        self._build_thread.finished.connect(self._cleanup_build_thread)

        self._build_thread.start()
        
    def copy_to_clipboard(self) -> None:
        if not self.preview_text.strip():
            print(self.preview_text)
            # QMessageBox.information(self, "Nothing to copy", "Preview is empty.")
            self.statusBar().showMessage("Nothing to copy. Preview is empty.", 3000)
            return
        QApplication.clipboard().setText(self.preview_text)
        self.statusBar().showMessage("Bundle copied to clipboard!", 3000)
        # QMessageBox.information(self, "Copied", "Bundle copied to clipboard.")

    def closeEvent(self, event) -> None:
        """ On close, persists user settings """
        self.cfg.include_tree = self.chk_tree.isChecked()
        self.cfg.include_file_contents = self.chk_contents.isChecked()
        self.cfg.max_file_bytes = int(self.max_bytes.value())
        self.cfg.use_default_ignores = self.chk_default_ignores.isChecked()
        self.cfg.respect_gitignore = self.chk_gitignore.isChecked()
        self.cfg.filter_by_extension = self.chk_filter_ext.isChecked()
        self.cfg.selected_extensions = list(self._selected_extensions())
        save_config(self.cfg)
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)

    icon_path = Path(__file__).resolve().parents[2] / "assets" / "icon.ico"
    app.setWindowIcon(QIcon(str(icon_path)))

    w = MainWindow()
    w.setWindowIcon(QIcon(str(icon_path)))
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()