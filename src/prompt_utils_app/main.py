from __future__ import annotations

import sys
from pathlib import Path
from typing import List
import traceback

from PySide6.QtCore import Qt, QObject, QThread, Signal
from PySide6.QtWidgets import QApplication, QCheckBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox, QSplitter, QTextEdit, QVBoxLayout, QWidget

from prompt_utils_core import BundleOptions, build_bundle


class BundleWorker(QObject):
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, selected: List[Path], options: BundleOptions) -> None:
        super().__init__()
        self.selected = selected
        self.options = options

    def run(self) -> None:
        try:
            out = build_bundle(self.selected, self.options)
            self.finished.emit(out)
        except Exception:
            self.failed.emit(traceback.format_exc())


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Prompt Utils")
        self.resize(1100, 700)

        self.selected: List[Path] = []
        self.preview_text: str = ""

        # Left: selection list + controls
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.ExtendedSelection)

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
        self.chk_tree.setChecked(True)

        self.chk_contents = QCheckBox("Include file contents")
        self.chk_contents.setChecked(True)

        self.max_bytes = QSpinBox()
        self.max_bytes.setRange(1_000, 10_000_000)
        self.max_bytes.setSingleStep(50_000)
        self.max_bytes.setValue(200_000)
        self.max_bytes.setSuffix(" bytes max/file")

        btn_refresh = QPushButton("Build preview")
        btn_copy = QPushButton("Copy to clipboard")
        btn_refresh.clicked.connect(self.refresh_preview)
        btn_copy.clicked.connect(self.copy_to_clipboard)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Selected paths"))
        left_layout.addWidget(self.list_widget)

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

        root = QWidget()
        root_layout = QVBoxLayout(root)
        root_layout.addWidget(splitter)

        self.setCentralWidget(root)

        self.refresh_preview()

    def _sync_list(self) -> None:  # TODO rewrite to provide a tree-like checklist
        self.list_widget.clear()
        for p in self.selected:
            item = QListWidgetItem(str(p))
            self.list_widget.addItem(item)

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

    def add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(self, "Select files")
        if not files:
            return
        for f in files:
            self.selected.append(Path(f))
        self.selected = sorted(set(self.selected), key=lambda x: str(x).lower())
        self._sync_list()
        self.refresh_preview()

    def add_directory(self) -> None:
        d = QFileDialog.getExistingDirectory(self, "Select a directory")
        if not d:
            return
        self.selected.append(Path(d))
        self.selected = sorted(set(self.selected), key=lambda x: str(x).lower())
        self._sync_list()
        self.refresh_preview()

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.list_widget.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            del self.selected[r]
        self._sync_list()
        self.refresh_preview()

    def clear_all(self) -> None:
        self.selected = []
        self._sync_list()
        self.refresh_preview()

    def refresh_preview(self) -> None:
        # prevent overlapping builds
        if getattr(self, "_build_thread", None) is not None:
            return

        options = BundleOptions(
            max_file_bytes=int(self.max_bytes.value()),
            include_tree=self.chk_tree.isChecked(),
            include_file_contents=self.chk_contents.isChecked()
        )
        
        selected_copy = list(self.selected)

        # update UI to show busy state
        self.preview.setPlainText("Building preview…")
        self.setEnabled(False)

        self._build_thread = QThread()
        self._worker = BundleWorker(selected_copy, options)
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
            QMessageBox.information(self, "Nothing to copy", "Preview is empty.")
            return
        QApplication.clipboard().setText(self.preview_text)
        QMessageBox.information(self, "Copied", "Bundle copied to clipboard.")


def main() -> None:
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()