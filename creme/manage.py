#!/usr/bin/env python
import os
import sys


def is_coverage_parallel_mode(argv):
    if 'test' not in argv or '--parallel' not in argv:
        # Not running tests, or running tests with one process
        return False

    # `COVERAGE_PROCESS_START` environment variable only has to be defined
    if os.getenv("COVERAGE_PROCESS_START") is None:
        return False

    return True


def start_parallel_coverage():
    """
    Start the coverage process manually for multi-process measurement.
    """
    import coverage

    coverage.process_startup()


def execute():
    # Allow to define external django settings
    sys.path.append(os.getcwd())

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "creme.settings")

    from django.core.management import execute_from_command_line

    argv = sys.argv
    if is_coverage_parallel_mode(argv):
        start_parallel_coverage()

    execute_from_command_line(argv)


if __name__ == "__main__":
    execute()
