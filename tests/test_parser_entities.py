import pytest
import os
import logging
from rocototop.parser import RocotoParser

def test_parser_missing_system_entity(tmp_path, caplog):
    wf_file = tmp_path / "workflow.xml"
    db_file = tmp_path / "rocoto.db"

    # Workflow with a missing SYSTEM entity
    content = """<?xml version="1.0"?>
<!DOCTYPE workflow [
  <!ENTITY missing SYSTEM "nonexistent.xml">
]>
<workflow name="test">
  <task name="&missing;"></task>
</workflow>"""
    wf_file.write_text(content)

    parser = RocotoParser(workflow_file=str(wf_file), database_file=str(db_file))

    with caplog.at_level(logging.WARNING):
        entities = parser._get_entity_values(content)

    assert "SYSTEM entity file not found" in caplog.text
    assert "missing" in entities
    assert entities["missing"] == ""

def test_parser_unreadable_system_entity(tmp_path, caplog):
    wf_file = tmp_path / "workflow.xml"
    db_file = tmp_path / "rocoto.db"
    entity_file = tmp_path / "unreadable.xml"

    entity_file.write_text("some content")
    # Make it unreadable
    os.chmod(entity_file, 0o000)

    # Workflow with an unreadable SYSTEM entity
    content = f"""<?xml version="1.0"?>
<!DOCTYPE workflow [
  <!ENTITY unreadable SYSTEM "{entity_file.name}">
]>
<workflow name="test">
  <task name="&unreadable;"></task>
</workflow>"""
    wf_file.write_text(content)

    parser = RocotoParser(workflow_file=str(wf_file), database_file=str(db_file))

    try:
        with caplog.at_level(logging.ERROR):
            entities = parser._get_entity_values(content)

        assert "Failed to read SYSTEM entity file" in caplog.text
        assert "unreadable" in entities
        assert entities["unreadable"] == ""
    finally:
        # Restore permissions so it can be deleted
        os.chmod(entity_file, 0o644)
