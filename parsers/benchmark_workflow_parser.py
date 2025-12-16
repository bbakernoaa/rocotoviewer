import timeit
import tempfile
import os
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from other modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from parsers.workflow_parser import WorkflowParser

XML_CONTENT = """
<workflow>
    <task name="task1">
        <command>echo "hello"</command>
        <dependency>
            <taskdep task="task0"/>
        </dependency>
        <envar name="MY_VAR" value="my_value"/>
    </task>
    <task name="task2">
        <command>echo "world"</command>
        <dependency>
            <taskdep task="task1"/>
        </dependency>
    </task>
    <cycledef group="group1">20230101T0000Z</cycledef>
    <resources>
        <pool>
            <entry key="cores" value="4"/>
        </pool>
    </resources>
</workflow>
"""

def create_test_xml_file():
    """Creates a temporary XML file for benchmarking."""
    fd, path = tempfile.mkstemp(suffix=".xml")
    with os.fdopen(fd, 'w') as f:
        f.write(XML_CONTENT)
    return path

def run_benchmark(xml_path):
    """Runs the benchmark for the WorkflowParser."""
    parser = WorkflowParser()
    stmt = lambda: parser.parse(xml_path)
    iterations = 1000
    total_time = timeit.timeit(stmt, number=iterations)
    avg_time = total_time / iterations
    print("--- Before Refactor ---")
    print(f"Total time for {iterations} iterations: {total_time:.4f} seconds")
    print(f"Average time per parse: {avg_time * 1e6:.2f} microseconds")

def main():
    """Main function to run the benchmark."""
    xml_file_path = None
    try:
        xml_file_path = create_test_xml_file()
        run_benchmark(xml_file_path)
    finally:
        if xml_file_path and os.path.exists(xml_file_path):
            os.remove(xml_file_path)

if __name__ == "__main__":
    main()
