import asyncio

# .. note:: warning: "If you modify features, API, or usage, you MUST update the documentation immediately."
import sqlite3

import pytest
from textual.widgets import OptionList, ProgressBar, Static

from rocototop.app import ActionMenu, ConfirmScreen, GlobalSummary, RocotoApp


@pytest.fixture
def mock_rocoto_files(tmp_path):
    workflow_file = tmp_path / "workflow.xml"
    db_file = tmp_path / "rocoto.db"

    workflow_content = """<?xml version="1.0"?>
<workflow name="test">
  <cycledef group="default">202301010000 202301011200 06:00:00</cycledef>
  <task name="task1" cycledefs="default"></task>
</workflow>"""
    workflow_file.write_text(workflow_content)

    conn = sqlite3.connect(db_file)
    c = conn.cursor()
    c.execute("CREATE TABLE cycles (cycle INTEGER)")
    c.execute("INSERT INTO cycles VALUES (1672531200)")  # 2023-01-01 00:00:00
    c.execute("""
        CREATE TABLE jobs (
            taskname TEXT, cycle INTEGER, state TEXT,
            exit_status INTEGER, duration INTEGER, tries INTEGER, jobid TEXT
        )
    """)
    c.execute("INSERT INTO jobs VALUES ('task1', 1672531200, 'SUCCEEDED', 0, 100, 1, '12345')")
    conn.commit()
    conn.close()

    return str(workflow_file), str(db_file)


@pytest.mark.asyncio
async def test_global_summary_presence(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test() as pilot:
        summary = app.query_one(GlobalSummary)
        assert summary is not None

        # Wait for data to load
        for _ in range(50):
            if app.workflow_summary:
                break
            await pilot.pause(0.1)

        assert app.workflow_summary.get("SUCCEEDED") == 1

        counts_static = summary.query_one("#summary_counts", Static)
        assert "S:1" in str(counts_static.render())

        progress_bar = summary.query_one(ProgressBar)
        assert progress_bar.progress == 1
        assert progress_bar.total == 1


@pytest.mark.asyncio
async def test_confirm_modal_on_run(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test() as pilot:
        # Mocking _background_refresh to see if it's called
        refresh_called = asyncio.Event()

        def mock_refresh(run_pulse=False):
            refresh_called.set()
            # Return an awaitable if needed, but here it's called as self._background_refresh(run_pulse=True)
            # which is decorated with @work. @work returns a Worker.
            return None

        app._background_refresh = mock_refresh

        await pilot.press("R")
        await pilot.pause(0.1)
        assert isinstance(app.screen, ConfirmScreen)

        # Click No
        await pilot.click("#confirm_no")
        # Wait for the screen to be dismissed
        for _ in range(20):
            if not isinstance(app.screen, ConfirmScreen):
                break
            await pilot.pause(0.1)

        assert not isinstance(app.screen, ConfirmScreen)
        assert not refresh_called.is_set()

        # Press R again and then click Yes
        await pilot.press("R")
        await pilot.pause(0.1)
        assert isinstance(app.screen, ConfirmScreen)
        await pilot.click("#confirm_yes")

        try:
            await asyncio.wait_for(refresh_called.wait(), timeout=2.0)
        except TimeoutError:
            pytest.fail("Refresh was not called")

        for _ in range(20):
            if not isinstance(app.screen, ConfirmScreen):
                break
            await pilot.pause(0.1)

        assert refresh_called.is_set()


@pytest.mark.asyncio
async def test_action_menu(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test() as pilot:
        await pilot.press("m")
        await pilot.pause(0.1)
        assert isinstance(app.screen, ActionMenu)

        option_list = app.screen.query_one(OptionList)
        assert option_list.option_count == 6

        # ActionMenu has its own bindings, but let's try dismissing directly
        app.screen.dismiss()
        # Wait for the screen to be dismissed
        for _ in range(20):
            if not isinstance(app.screen, ActionMenu):
                break
            await pilot.pause(0.1)

        assert not isinstance(app.screen, ActionMenu)


@pytest.mark.asyncio
async def test_split_pane_layout(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test():
        assert app.query_one("#split_pane")
        assert app.query_one("#details_panel")
        assert app.query_one("#log_container")
        assert app.query_one("#log_panel")

        # Verify they are visible
        assert app.query_one("#details_panel").visible
        assert app.query_one("#log_panel").visible
