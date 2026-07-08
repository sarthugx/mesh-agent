import os
from pathlib import Path
from typing import List, Dict, Any

class WorkspaceFS:
    """
    A path-traversal-proof filesystem sandbox.
    All operations are jailed to the initialized root_path.
    """
    def __init__(self, root_path: str | Path):
        self.root_path = Path(root_path).resolve()
        self.root_path.mkdir(parents=True, exist_ok=True)

    def _safe_path(self, relative_path: str | Path) -> Path:
        """
        Resolves relative_path against root_path and ensures it does not escape.
        Raises PermissionError if a traversal attempt is detected.
        """
        # Resolve the path relative to the root_path
        # Path(root, rel) resolves rel relative to root. If rel is absolute, it resolves to rel.
        try:
            resolved = Path(self.root_path, relative_path).resolve()
        except Exception as e:
            raise PermissionError(f"Access denied: invalid path '{relative_path}'.") from e

        # Enforce sandbox jail using commonpath
        try:
            root_str = str(self.root_path)
            resolved_str = str(resolved)
            common = os.path.commonpath([root_str, resolved_str])
            if os.path.normpath(common) != os.path.normpath(root_str):
                raise PermissionError(f"Access denied: path '{relative_path}' escapes workspace sandbox.")
        except ValueError as e:
            raise PermissionError(f"Access denied: path '{relative_path}' escapes workspace sandbox due to drive mismatch.")

        return resolved

    def read_text(self, relative_path: str | Path) -> str:
        """Read content of a file as a string."""
        target = self._safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target.read_text(encoding="utf-8")

    def read_bytes(self, relative_path: str | Path) -> bytes:
        """Read content of a file as bytes."""
        target = self._safe_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"File not found: {relative_path}")
        return target.read_bytes()

    def write_text(self, relative_path: str | Path, content: str) -> None:
        """Write string content to a file, creating parent directories if necessary."""
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def write_bytes(self, relative_path: str | Path, content: bytes) -> None:
        """Write bytes content to a file, creating parent directories if necessary."""
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)

    def exists(self, relative_path: str | Path) -> bool:
        """Check if a file or directory exists."""
        target = self._safe_path(relative_path)
        return target.exists()

    def is_dir(self, relative_path: str | Path) -> bool:
        """Check if a path is a directory."""
        target = self._safe_path(relative_path)
        return target.is_dir()

    def is_file(self, relative_path: str | Path) -> bool:
        """Check if a path is a file."""
        target = self._safe_path(relative_path)
        return target.is_file()

    def mkdir(self, relative_path: str | Path) -> None:
        """Create a directory."""
        target = self._safe_path(relative_path)
        target.mkdir(parents=True, exist_ok=True)

    def delete(self, relative_path: str | Path) -> None:
        """Delete a file or directory (recursively if directory)."""
        target = self._safe_path(relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Path not found: {relative_path}")
        
        if target.is_dir():
            # Recursively delete files and folders
            self._delete_recursive(target)
        else:
            target.unlink()

    def _delete_recursive(self, path: Path) -> None:
        for child in path.iterdir():
            if child.is_dir():
                self._delete_recursive(child)
            else:
                child.unlink()
        path.rmdir()

    def list_dir(self, relative_path: str | Path = "") -> List[Dict[str, Any]]:
        """
        List files and folders in a directory relative to the workspace root.
        Returns a list of metadata dictionaries.
        """
        target = self._safe_path(relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Directory not found: {relative_path}")
        if not target.is_dir():
            raise ValueError(f"Path is not a directory: {relative_path}")

        results = []
        for item in target.iterdir():
            # Calculate path relative to workspace root
            rel_path = item.relative_to(self.root_path).as_posix()
            stat = item.stat()
            results.append({
                "name": item.name,
                "path": rel_path,
                "is_dir": item.is_dir(),
                "size": stat.st_size if item.is_file() else 0,
                "modified": stat.st_mtime
            })
        # Sort folders first, then files alphabetically
        results.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
        return results
