"""
Test Runner Script for ScheduleZero

Provides convenient commands for running different test suites.
Handles test categorization, reporting, and common test scenarios.
"""
import subprocess
import sys
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=True, markers=None, coverage=False):
    """
    Run tests with specified options.
    
    Args:
        test_type: Type of tests to run (all, unit, integration, zmq, governor, regression)
        verbose: Show verbose output
        markers: Additional pytest markers
        coverage: Generate coverage report
    """
    cmd = ["poetry", "run", "pytest"]
    
    # Test selection
    if test_type == "unit":
        cmd.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd.extend(["-m", "integration"])
    elif test_type == "zmq":
        cmd.extend(["tests/test_zmq_socket_recovery.py"])
    elif test_type == "governor":
        cmd.extend(["tests/test_governor.py"])
    elif test_type == "regression":
        cmd.extend(["-m", "regression"])
    elif test_type == "quick":
        cmd.extend(["-m", "not slow"])
    elif test_type == "all":
        cmd.append("tests/")
    else:
        # Run specific file or pattern
        cmd.append(test_type)
    
    # Verbosity
    if verbose:
        cmd.extend(["-v", "-s"])
    
    # Additional markers
    if markers:
        cmd.extend(["-m", markers])
    
    # Coverage
    if coverage:
        cmd.extend([
            "--cov=src/schedule_zero",
            "--cov-report=html",
            "--cov-report=term-missing"
        ])
    
    # Color output
    cmd.append("--color=yes")
    
    print(f"Running: {' '.join(cmd)}")
    print("=" * 70)
    
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="ScheduleZero Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Test Types:
  all          Run all tests (default)
  unit         Run only unit tests
  integration  Run only integration tests
  zmq          Run ZMQ socket recovery tests
  governor     Run governor tests
  regression   Run regression tests
  quick        Run quick tests (exclude slow tests)
  <path>       Run tests in specific file or directory

Examples:
  python run_tests.py                          # Run all tests
  python run_tests.py quick                    # Run quick tests only
  python run_tests.py zmq -c                   # Run ZMQ tests with coverage
  python run_tests.py governor -v              # Run governor tests verbose
  python run_tests.py tests/test_zmq_*.py      # Run specific test file
        """
    )
    
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=True,
        help="Verbose output (default: True)"
    )
    
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet output (disable verbose)"
    )
    
    parser.add_argument(
        "-m", "--markers",
        help="Additional pytest markers"
    )
    
    parser.add_argument(
        "-c", "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available tests without running"
    )
    
    args = parser.parse_args()
    
    if args.list:
        # List tests
        cmd = ["poetry", "run", "pytest", "--collect-only", "-q"]
        subprocess.run(cmd)
        return 0
    
    verbose = args.verbose and not args.quiet
    
    return run_tests(
        test_type=args.test_type,
        verbose=verbose,
        markers=args.markers,
        coverage=args.coverage
    )


if __name__ == "__main__":
    sys.exit(main())
