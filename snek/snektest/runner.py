import traceback
from collections import defaultdict
from collections.abc import Callable
from collections.abc import Generator as _Generator
from typing import Literal, ParamSpec, TypedDict, TypeVar

from snek.snektest.results import TestResult, TestStatus, show_results

FixtureScope = Literal["test", "session"]


class FixtureConfig(TypedDict):
    scope: FixtureScope


T = TypeVar("T")
P = ParamSpec("P")
type Generator[T] = _Generator[T, None, None]

_defined_fixtures: dict[str, FixtureConfig] = {}


def load_fixture(fixture: Callable[..., Generator[T]]) -> T:
    generator = fixture()
    if _defined_fixtures[fixture.__name__]["scope"] == "test":
        test_runner._add_test_fixture(fixture, generator)
    elif _defined_fixtures[fixture.__name__]["scope"] == "session":
        # TODO: session scope fixtures
        pass
    return next(generator)


def test() -> Callable[[Callable], Callable]:
    def decorator(test_func: Callable):
        test_runner._add_test(test_func)
        return test_func

    return decorator


def fixture(scope: FixtureScope = "test"):
    def decorator(func: Callable[[], Generator[T]]):
        _defined_fixtures[func.__name__] = {"scope": scope}
        return func

    return decorator


class TestRunner:
    def __init__(self) -> None:
        self._tests: dict[str, Callable] = {}
        self._test_fixtures_generators: dict[str, dict[str, _Generator]] = defaultdict(
            dict
        )

    def _add_test(self, new_test: Callable):
        if new_test.__name__ in self._tests:
            raise ValueError("Test with this name already exists")
        self._tests[new_test.__name__] = new_test

    def _add_test_fixture(self, fixture: Callable, generator: _Generator) -> None:
        fixture_name = fixture.__name__
        # walk up the stack until we find load_fixture
        # the frame before that is the test that called it
        test_name = None
        for idx, frame in enumerate(traceback.extract_stack()):
            if frame.name == "load_fixture":
                test_name = traceback.extract_stack()[idx - 1].name

        if test_name is None:
            msg = f"Could not find test for fixture {fixture_name}"
            raise ValueError(msg)

        if fixture_name not in self._test_fixtures_generators[test_name]:
            self._test_fixtures_generators[test_name][fixture_name] = generator

    def run_tests(self) -> None:
        test_results: dict[str, TestResult] = {}
        for test_name, test_func in self._tests.items():
            message = ""
            status = TestStatus.passed
            try:
                test_func()
            except AssertionError:
                status = TestStatus.failed
                message = traceback.format_exc()
            except Exception as e:
                status = TestStatus.failed
                message = f"Unexpected error: {e!s}"

            if test_name in self._test_fixtures_generators:
                for fixture_name, generator in self._test_fixtures_generators[
                    test_name
                ].items():
                    try:
                        next(generator)
                        raise ValueError(
                            f"Fixture {fixture_name} for test {test_name} "
                            'has more than one "yield"'
                        )
                    except StopIteration:
                        pass
                    except Exception:
                        status = TestStatus.failed
                        message += (
                            f"Unexpected error tearing down fixture "
                            f"{fixture_name} for test {test_name}: \n{traceback.format_exc()}\n"
                        )

            test_results[test_name] = TestResult(
                status=status,
                message=message if status == TestStatus.failed else "Test passed",
            )
        show_results(test_results)


test_runner = TestRunner()
