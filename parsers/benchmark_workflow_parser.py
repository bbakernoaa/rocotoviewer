
import timeit
import tempfile
import os
import sys
from pathlib import Path
from typing import List

# Add project root to sys.path to allow imports from other modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from parsers.workflow_parser import WorkflowParser

def generate_xml_content(num_tasks: int) -> str:
    """Generates a large XML content string with a specified number of tasks."""
    tasks: List[str] = []
    for i in range(num_tasks):
        tasks.append(f"""
    <task name="task{i}">
        <command>echo "hello from task {i}"</command>
        <dependency>
            <taskdep task="task{i-1}"/>
        </dependency>
        <envar name="TASK_NUM" value="{i}"/>
    </task>""")

    return f"""
<workflow>
    {''.join(tasks)}
    <cycledef group="group1">20230101T0000Z</cycledef>
    <resources>
        <pool>
            <entry key="cores" value="4"/>
        </pool>
    </resources>
</workflow>
"""

def create_test_xml_file(content: str) -> str:
    """Creates a temporary XML file for benchmarking."""
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, 'w') as f:
        f.write(content)
    return path

def run_benchmark(xml_path: str):
    """Runs the benchmark for the WorkflowParser."""
    parser = WorkflowParser()
    stmt = lambda: parser.parse(xml_path)
    iterations = 100
    total_time = timeit.timeit(stmt, number=iterations)
    avg_time = total_time / iterations
    print(f"--- WorkflowParser Benchmark ---")
    print(f"Total time for {iterations} iterations: {total_time:.4f} seconds")
    print(f"Average time per parse: {avg_time * 1e3:.2f} milliseconds")

def main():
    """Main function to run the benchmark."""
    xml_file_path = None
    try:
        # Generate a more realistic XML with 100 tasks
        xml_content = generate_xml_content(100)
        xml_file_path = create_test_xml_file(xml_content)

        # Benchmark the refactored implementation
        run_benchmark(xml_file_path)

    finally:
        if xml_file_path and os.path.exists(xml_file_path):
            os.remove(xml_file_path)

if __name__ == "__main__":
    main()
