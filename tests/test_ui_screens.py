import pytest
from textual.widgets import OptionList, Tree

from rocototop.app import ActionMenu, HelpScreen, RocotoApp


@pytest.mark.asyncio
async def test_help_screen(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test() as pilot:
        # Wait for app to be ready
        for _ in range(50):
            if not app.workers and app.query_one("#cycle_tree", Tree).root.children:
                break
            await pilot.pause(0.1)

        # Press 'h' to open help
        await pilot.press("h")
        await pilot.pause(0.1)

        # Verify HelpScreen is active
        assert isinstance(app.screen, HelpScreen)

        # Verify HelpScreen content is mounted
        assert app.screen.query_one("#help_title")
        assert app.screen.query_one("#help_content")

        # Close help
        await pilot.press("q")
        await pilot.pause(0.1)
        # Verify it returned to the main screen
        assert not isinstance(app.screen, HelpScreen)


@pytest.mark.asyncio
async def test_action_menu(mock_rocoto_files):
    wf, db = mock_rocoto_files
    app = RocotoApp(workflow_file=wf, database_file=db)
    async with app.run_test() as pilot:
        # Wait for app to be ready
        for _ in range(50):
            if not app.workers and app.query_one("#cycle_tree", Tree).root.children:
                break
            await pilot.pause(0.1)

        # Select a task
        tree = app.query_one("#cycle_tree", Tree)
        cycle_node = tree.root.children[0]
        cycle_node.expand()
        await pilot.pause(0.1)
        task_node = cycle_node.children[0]
        tree.select_node(task_node)
        await pilot.pause(0.1)

        # Press 'm' to open action menu
        await pilot.press("m")
        await pilot.pause(0.1)

        # Verify ActionMenu is active
        assert isinstance(app.screen, ActionMenu)

        # Verify options
        option_list = app.screen.query_one(OptionList)
        assert option_list.option_count > 0

        # Select first option (Check Task)
        await pilot.press("enter")
        await pilot.pause(0.1)

        # Verify it returned to the main screen
        assert not isinstance(app.screen, ActionMenu)
