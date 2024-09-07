from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Callable

from snek.snektest.presentation import Colors, pad_string_to_screen_width


class TestStatus(StrEnum):
    passed = auto()
    failed = auto()
    xfailed = auto()
    xpassed = auto()
    skipped_unconditionally = auto()
    skipped_conditionally = auto()
    skippped_dynamically = auto()


@dataclass
class TestResult:
    status: TestStatus
    message: str


class TestRunner:
    def __init__(self) -> None:
        self._tests: dict[str, Callable] = {}
        self._fixtures: dict[str, Callable] = {}  # New dictionary to store fixtures

    def _add_test(self, new_test: Callable):
        if new_test.__name__ in self._tests:
            raise ValueError("Test with this name already exists")
        self._tests[new_test.__name__] = new_test

    def _add_fixture(self, fixture: Callable) -> None:
        fixture_name = fixture.__name__
        if fixture_name in self._fixtures:
            raise ValueError(f"Fixture with this name already exists: {fixture_name}")
        self._fixtures[fixture_name] = fixture

    def _show_results(self, test_results: dict[str, TestResult]):
        no_passed = sum(
            1 for test in test_results.values() if test.status == TestStatus.passed
        )
        no_failed = sum(
            1 for test in test_results.values() if test.status == TestStatus.failed
        )
        no_xfailed = sum(
            1 for test in test_results.values() if test.status == TestStatus.xfailed
        )
        no_xpassed = sum(
            1 for test in test_results.values() if test.status == TestStatus.xpassed
        )

        message = ""

        for test_name, test_result in test_results.items():
            if test_result.status == TestStatus.failed:
                message += (
                    f"{Colors.RED}{test_name}{Colors.RESET}:\n{test_result.message}\n"
                )
            if test_result.status == TestStatus.xfailed:
                message += f"{Colors.YELLOW}{test_name}: {test_result.message}\n"
        print(message)

        colored_message = {
            f"{no_passed} passed, ": Colors.GREEN,
            f"{no_failed} failed, ": Colors.RED,
            f"{no_xfailed} xfailed, ": Colors.YELLOW,
            f"{no_xpassed} xpassed, ": Colors.BLUE,
            f"{len(self._tests)} total": None,
        }
        summary = Colors.apply_multiple_colors(colored_message)

        summary = pad_string_to_screen_width(summary)
        print(summary)

    def run_tests(self) -> None:
        test_results: dict[str, TestResult] = {}
        for test_name, test_func in self._tests.items():
            message = ""
            try:
                test_func()
                status = TestStatus.passed
            except AssertionError as e:
                status = TestStatus.failed
                message = str(e)
            except Exception as e:
                status = TestStatus.failed
                message = f"Unexpected error: {str(e)}"

            test_results[test_name] = TestResult(
                status=status,
                message=message if status == TestStatus.failed else "Test passed",
            )
        self._show_results(test_results)


test_runner = TestRunner()


def test():
    def decorator(test_func: Callable):
        test_runner._add_test(test_func)
        return test_func

    return decorator


def fixture(fixture_func: Callable):
    test_runner._add_fixture(fixture_func)
    return fixture_func
