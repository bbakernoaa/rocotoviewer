
import time
import random
from core.log_processor import StreamingLogProcessor
from config.settings import Settings

# --- Test Data Generation ---
LOG_LEVELS = ["INFO", "DEBUG", "WARNING", "ERROR"]
TASKS = ["getData", "processData", "uploadData", "verifyData", "cleanup"]
CYCLES = [f"2023{str(i).zfill(2)}01" for i in range(1, 13)]
STATUSES = ["succeeded", "failed", "submitted", "running"]

def generate_log_line():
    """Generates a realistic-looking Rocoto log line."""
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - random.randint(0, 86400)))
    level = random.choice(LOG_LEVELS)
    task = random.choice(TASKS)
    cycle = random.choice(CYCLES)
    status = random.choice(STATUSES)
    message = f"Some detailed log message about the process happening here."

    # Assemble the line in a common Rocoto format
    return f"{timestamp} [{level}] - task={task} cycle={cycle} status is {status}. {message}"

def run_benchmark(processor, num_lines=10000):
    """
    Runs the benchmark for a given log processor.

    Args:
        processor: An instance of a log processor.
        num_lines (int): The number of log lines to generate and parse.

    Returns:
        float: The total time taken in seconds.
    """
    print(f"Generating {num_lines} log lines for benchmarking...")
    log_lines = [generate_log_line() for _ in range(num_lines)]
    print("Generation complete. Starting benchmark...")

    start_time = time.perf_counter()

    for line in log_lines:
        processor.parse_log_line(line)

    end_time = time.perf_counter()
    total_time = end_time - start_time

    print(f"Parsed {num_lines} lines in {total_time:.4f} seconds.")
    print(f"Average time per line: {total_time / num_lines * 1e6:.2f} microseconds.")
    return total_time

def main():
    """Main function to run and compare benchmarks."""
    print("--- Running Benchmark for Current Log Processor ---")

    # Instantiate the processor
    # We pass a simple object for config since it's not deeply used by parse_log_line
    class MockConfig:
        max_log_buffer_size = 1000

    config = MockConfig()
    processor = StreamingLogProcessor(config=config)

    # Run the benchmark
    time_taken = run_benchmark(processor, num_lines=50000)

    print("\n--- Benchmark Complete ---")
    print(f"Total time for current implementation: {time_taken:.4f}s")


if __name__ == "__main__":
    main()
