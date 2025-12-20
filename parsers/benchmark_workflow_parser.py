import timeit
import tempfile
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from other modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from parsers.workflow_parser import WorkflowParser


def generate_large_xml_content(num_tasks: int) -> str:
    """Generates a large XML string with a specified number of tasks."""
    tasks_xml = []
    for i in range(num_tasks):
        task_xml = f"""
    <task name="task{i}">
        <command>echo "Executing task {i}"</command>
        <dependency>
            <taskdep task="task{i-1}"/>
        </dependency>
        <envar name="TASK_INDEX" value="{i}"/>
        <status>COMPLETED</status>
        <walltime>00:05:00</walltime>
    </task>"""
        tasks_xml.append(task_xml)

    return f"""
<workflow>
    <description>A large workflow with {num_tasks} tasks.</description>
    {''.join(tasks_xml)}
    <cycledef group="default">20230101T0000Z</cycledef>
    <resources>
        <pool>
            <entry key="cores" value="8"/>
        </pool>
    </resources>
</workflow>
"""


def create_test_xml_file(num_tasks: int = 500):
    """Creates a temporary XML file with a specified number of tasks."""
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, "w") as f:
        xml_content = generate_large_xml_content(num_tasks)
        f.write(xml_content)
    return path


def run_benchmark(xml_path: str, title: str):
    """Runs the benchmark for the WorkflowParser."""
    parser = WorkflowParser()
    stmt = lambda: parser.parse(xml_path)
    iterations = 100
    total_time = timeit.timeit(stmt, number=iterations)
    avg_time = total_time / iterations
    print(f"--- {title} ---")
    print(f"Total time for {iterations} iterations: {total_time:.4f} seconds")
    print(f"Average time per parse: {avg_time * 1e3:.2f} milliseconds")


def main():
    """Main function to run the benchmark."""
    xml_file_path = None
    try:
        xml_file_path = create_test_xml_file(num_tasks=500)
        run_benchmark(xml_file_path, "After Refactor")
    finally:
        if xml_file_path and os.path.exists(xml_file_path):
            os.remove(xml_file_path)


if __name__ == "__main__":
    main()
