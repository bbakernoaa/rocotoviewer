
import timeit
import sys
from pathlib import Path

# Add project root to sys.path to allow imports from other modules
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from core.log_processor import StreamingLogProcessor
from config.settings import Settings

def run_benchmark():
    """Runs the benchmark for the StreamingLogProcessor.parse_log_line method."""
    config = Settings()
    processor = StreamingLogProcessor(config)
    log_line = '2023-10-27 10:00:00,123 [INFO] task:task1 cycle:20231027T0000Z status:SUCCEEDED - Task completed successfully'

    stmt = lambda: processor.parse_log_line(log_line)
    iterations = 10000
    total_time = timeit.timeit(stmt, number=iterations)
    avg_time = total_time / iterations
    print("--- After Refactor ---")
    print(f"Total time for {iterations} iterations: {total_time:.4f} seconds")
    print(f"Average time per parse: {avg_time * 1e6:.2f} microseconds")

def main():
    """Main function to run the benchmark."""
    run_benchmark()

if __name__ == "__main__":
    main()
