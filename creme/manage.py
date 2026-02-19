#!/usr/bin/env python
import os
import sys


# def is_coverage_parallel_mode(argv):
#     if 'test' not in argv or '--parallel' not in argv:
#         # Not running tests, or running tests with one process
#         return False
#
#     # `COVERAGE_PROCESS_START` environment variable only has to be defined
#     if os.getenv("COVERAGE_PROCESS_START") is None:
#         return False
#
#     return True
def is_test_mode(argv):
    return 'test' in argv


def is_parallel_mode(argv):
    if '--parallel' in argv:
        return True

    prefix = '--parallel='
    for value in argv:
        if value.startswith(prefix):
            return value.removeprefix(prefix) != '1'

    return False


def is_coverage_mode():
    # NB: `COVERAGE_PROCESS_START` environment variable only has to be defined
    return os.getenv("COVERAGE_PROCESS_START") is not None


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
    # if is_coverage_parallel_mode(argv):
    #     start_parallel_coverage()
    if is_test_mode(argv) and is_parallel_mode(argv):
        if os.name == 'posix':
            # NB: (genglert, 19 february 2026, creme 2.8 beta)
            #     with Python 3.14, 'forkserver' became the default mode, but
            #      - it's not compatible with the sqlite backend
            #       See django/db/backends/sqlite3/creation.py => get_test_db_clone_settings()
            #      - it seems to not working well with mariadb on the CI
            #      - (not tested: mysql, pgsql)
            #   It seems 'spawn' does not work either => what about parallel testing
            #   on Windows/macOS?
            import multiprocessing as mp
            mp.set_start_method('fork')

        if is_coverage_mode():
            start_parallel_coverage()

    execute_from_command_line(argv)


if __name__ == "__main__":
    execute()
