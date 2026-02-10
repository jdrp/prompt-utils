from __future__ import annotations

from pathlib import Path
from typing import Callable
from enum import Enum

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QPalette
from PySide6.QtWidgets import QApplication, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator, QHeaderView

# TODO turn this into a proper module


class ReturnListIncludes(Enum):  # TODO find better name
    FILES_ONLY = 1
    DIRS_ONLY = 2
    ALL = 3

class FileTreeItem(QTreeWidgetItem):
    def __init__(self, path: Path, is_ignored: bool = False, *, 
                 display_full_path: bool = False, default_state: Qt.CheckState = Qt.Checked):
        # TODO allow widget size config
        super().__init__()
        self.path = path
        self.is_ignored = is_ignored

        if display_full_path:
            self.setText(0, str(path))
        else:
            self.setText(0, path.name)

        self.setData(0, Qt.UserRole, str(path))
        self.apply_visual_state(is_ignored)
    
    def get_path(self) -> Path:
        return self.path
    
    def apply_visual_state(self, is_ignored: bool) -> None:
        self.is_ignored = is_ignored
        palette = QApplication.palette()

        font = self.font(0)
        if is_ignored:
            self.setCheckState(0, Qt.Unchecked)
            color = palette.color(QPalette.Disabled, QPalette.Text)
            self.setForeground(0, QBrush(color))
            font.setItalic(True)
            
        else:
            if self.checkState(0) == Qt.Unchecked:
                self.setCheckState(0, Qt.Checked)
            self.setData(0, Qt.ForegroundRole, None)
            font.setItalic(False)
        self.setFont(0, font)
    

class FileTreeWidget(QTreeWidget):
    """
    A reusable file tree widget that handles directory recursion,
    gitignore-style filtering visualization, and custom check-state propagation.
    """
    def __init__(self, parent=None, *, header: str = "Files") -> None:
        super().__init__(parent)
        self.setHeaderLabels([header])
        self.header().setSectionResizeMode(QHeaderView.ResizeToContents)

        self._ignore_checker: Callable[[Path], bool] | None = None
        self.itemChanged.connect(self._on_item_changed)

    def set_ignore_checker(self, callback: Callable[[Path], bool]) -> None:
        self._ignore_checker = callback

    def add_path(self, path: Path) -> None:
        """Adds a new root directory or file to the tree."""
        # TODO add search_in_other_roots -> if its already included as a subchild, expand to it instead of adding
        is_ignored = False
        if self._ignore_checker:
            is_ignored = self._ignore_checker(path)

        root_item = self._add_item(self, path, is_ignored)
        root_item.setExpanded(False)

    def clear_all(self):
        self.clear()

    def remove_selected_roots(self):
        """Removes top-level items that are selected (highlighted)."""
        root = self.invisibleRootItem()
        for item in self.selectedItems():
            if item.parent() is None:
                root.removeChild(item)

    def get_checked_files(self, include = ReturnListIncludes.FILES_ONLY) -> list[Path]:
        """Returns a flat list of all files currently checked."""
        results = []

        iterator = QTreeWidgetItemIterator(self, QTreeWidgetItemIterator.Checked)
        while (item := iterator.value()):
            path = item.path

            if (include == ReturnListIncludes.FILES_ONLY and path.is_file()) or \
               (include == ReturnListIncludes.DIRS_ONLY  and path.is_dir())  or \
               (include == ReturnListIncludes.ALL):
                results.append(path)
            
            iterator += 1

        return results
    
    def refresh_ignore_state(self) -> None:
        """
        Re-evaluates every item in the tree against the current ignore_checker.
        Useful when the user toggles '.gitignore' or 'default ignores'.
        """
        self.blockSignals(True)
        try:
            iterator = QTreeWidgetItemIterator(self)
            while (item := iterator.value()):
                if isinstance(item, FileTreeItem):
                    is_ignored = False
                    if self._ignore_checker:
                        is_ignored = self._ignore_checker(item.path)
                    item.apply_visual_state(is_ignored)
                iterator += 1
        
        finally:
            self.blockSignals(False)
            self._force_update_all_parents()

    def _add_item(self, parent_widget: FileTreeWidget | FileTreeItem, path: Path, is_ignored: bool) -> FileTreeItem:
        item = FileTreeItem(path, is_ignored)

        if isinstance(parent_widget, FileTreeWidget):
            parent_widget.addTopLevelItem(item)
        else:
            parent_widget.addChild(item)

        if path.is_dir():
            try:
                # sort -> first directories, then files (alphabetical)
                children = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
            except PermissionError:
                children = []

            for child in children:
                # propagate ignore rules
                child_ignored = is_ignored
                if not child_ignored and self._ignore_checker:
                    child_ignored = self._ignore_checker(child)

                self._add_item(item, child, child_ignored)

        return item
    
    def _on_item_changed(self, item: FileTreeItem, column: int) -> None:
        """
        Handles manual check state changes.
        Triggers propagation logic while preventing signal loops.
        """
        self.blockSignals(True)  # prevent callback loops
        try:
            state = item.checkState(column)

            self._propagate_state_down(item, state)

            # propagate upwards
            parent = item.parent()
            while parent:
                self._update_parent_state(parent)
                parent = parent.parent()
        finally:
            self.blockSignals(False)

    def _propagate_state_down(self, item: FileTreeItem, state: Qt.CheckState) -> None:
        """
        Apply state to children. 
        Logic:
        - If Unchecking: Uncheck everything.
        - If Checking: Check normal items, keep ignored items Unchecked.
        """
        for i in range(item.childCount()):
            child = item.child(i)
            
            if state == Qt.Checked and child.is_ignored:
                pass
            else:
                child.setCheckState(0, state)

            self._propagate_state_down(child, state)

    def _update_parent_state(self, parent: FileTreeItem):
        """
        Look at a parent's children and determine if the parent 
        should be Checked, Unchecked, or PartiallyChecked.
        """
        # TODO skip ignored children
        checked_count = 0
        partial_count = 0
        total_count = parent.childCount()

        for i in range(total_count):
            child = parent.child(i)
            state = child.checkState(0)
            if state == Qt.Checked:
                checked_count += 1
            elif state == Qt.PartiallyChecked:
                checked_count += 1

        if checked_count == total_count:
            parent.setCheckState(0, Qt.Checked)
        elif checked_count == 0 and partial_count == 0:
            parent.setCheckState(0, Qt.Unchecked)
        else:
            parent.setCheckState(0, Qt.PartiallyChecked)

    def _force_update_all_parents(self) -> None:
        """
        Recalculates the check state of all parents based on their children.
        We do this bottom-up (children first) so the parents know the correct status.
        """
        def update_recursive(item: FileTreeItem) -> None:
            for i in range(item.childCount()):
                update_recursive(item.child(i))

            if item.childCount() > 0:
                self._update_parent_state(item)

        for i in range(self.topLevelItemCount()):
            update_recursive(self.topLevelItem(i))