import sys
from unittest.mock import patch

import pytest

from rocototop.cli import main


def test_cli_missing_workflow(tmp_path, capsys):
    db_file = tmp_path / "test.db"
    db_file.write_text("dummy")

    test_args = ["rocototop", "-w", "nonexistent.xml", "-d", str(db_file)]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Workflow file not found" in captured.out


def test_cli_missing_database(tmp_path, capsys):
    wf_file = tmp_path / "test.xml"
    wf_file.write_text("dummy")

    test_args = ["rocototop", "-w", str(wf_file), "-d", "nonexistent.db"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1

    captured = capsys.readouterr()
    assert "Error: Database file not found" in captured.out
