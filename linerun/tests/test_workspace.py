import pytest
import tempfile
import os
from pathlib import Path
from linerun.workspace import WorkspaceFS

def test_workspace_crud():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = WorkspaceFS(tmpdir)
        
        # Test writing text
        ws.write_text("hello.txt", "Hello World")
        assert ws.exists("hello.txt")
        assert ws.is_file("hello.txt")
        assert not ws.is_dir("hello.txt")
        
        # Test reading text
        content = ws.read_text("hello.txt")
        assert content == "Hello World"
        
        # Test nested files
        ws.write_text("subdir/nested.txt", "Nested Content")
        assert ws.exists("subdir/nested.txt")
        assert ws.is_dir("subdir")
        
        # Test listing directory
        items = ws.list_dir("")
        assert len(items) == 2
        names = [item["name"] for item in items]
        assert "hello.txt" in names
        assert "subdir" in names
        
        # Test deletion
        ws.delete("subdir/nested.txt")
        assert not ws.exists("subdir/nested.txt")
        ws.delete("subdir")
        assert not ws.exists("subdir")

def test_path_traversal_jail():
    with tempfile.TemporaryDirectory() as tmpdir:
        ws = WorkspaceFS(tmpdir)
        
        # Write a file outside the sandbox (simulating host file system)
        outside_dir = Path(tmpdir).parent
        outside_file = outside_dir / "secret.txt"
        outside_file.write_text("confidential", encoding="utf-8")
        
        try:
            # Traversal attempts should raise PermissionError
            with pytest.raises(PermissionError):
                ws.read_text("../secret.txt")
                
            with pytest.raises(PermissionError):
                ws.write_text("../hacked.txt", "bad content")
                
            with pytest.raises(PermissionError):
                ws.delete("../secret.txt")
                
            # Test absolute path attempt
            with pytest.raises(PermissionError):
                ws.read_text(str(outside_file))
        finally:
            if outside_file.exists():
                outside_file.unlink()
