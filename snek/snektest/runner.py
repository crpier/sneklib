import traceback
from collections import defaultdict
from collections.abc import Generator as _Generator
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    ParamSpec,
    Tuple,
    TypedDict,
    TypeVar,
    TypeVarTuple,
    Unpack,
)

from snek.snektest.results import TestResult, TestStatus, show_results

FixtureScope = Literal["test", "session"]


class FixtureConfig(TypedDict):
    scope: FixtureScope


T = TypeVar("T")
P = ParamSpec("P")
type Generator[T] = _Generator[T, None, None]

_defined_fixtures: dict[str, FixtureConfig] = {}


def load_fixture(fixture: Callable[..., _Generator[T, None, None]]) -> T:
    generator = fixture()
    if _defined_fixtures[fixture.__name__]["scope"] == "test":
        test_runner._add_test_fixture(fixture, generator)
    elif _defined_fixtures[fixture.__name__]["scope"] == "session":
        # TODO: session scope fixtures
        pass
    return next(generator)


T = TypeVar("T")
T2 = TypeVarTuple("T2")


def test(
    *params: Unpack[T2],
) -> Callable[[Callable[[Unpack[T2]], None]], Callable[[Unpack[T2]], None]]:
    def decorator(
        test_func: Callable[[Unpack[T2]], None],
    ) -> Callable[[Unpack[T2]], None]:
        test_runner._add_test(test_func, params)
        return test_func

    return decorator


def fixture(scope: FixtureScope = "test"):
    def decorator(func: Callable[[], Generator[T]]):
        _defined_fixtures[func.__name__] = {"scope": scope}
        return func

    return decorator


class TestRunner:
    def __init__(self) -> None:
        self._tests: Dict[str, List[Tuple[Callable[..., None], Tuple[Any, ...]]]] = {}
        self._test_fixtures_generators: Dict[
            str, Dict[str, _Generator[Any, None, None]]
        ] = defaultdict(dict)

    def _add_test(self, new_test: Callable[..., None], params: Any) -> None:
        if new_test.__name__ not in self._tests:
            self._tests[new_test.__name__] = []
        self._tests[new_test.__name__].append((new_test, params))

    def _add_test_fixture(
        self,
        fixture: Callable[..., _Generator[T, None, None]],
        generator: _Generator[T, None, None],
    ) -> None:
        fixture_name = fixture.__name__
        # walk up the stack until we find load_fixture
        # the frame before that is the test that called it
        test_name: str | None = None
        for idx, frame in enumerate(traceback.extract_stack()):
            if frame.name == "load_fixture":
                test_name = traceback.extract_stack()[idx - 1].name

        if test_name is None:
            msg = f"Could not find test for fixture {fixture_name}"
            raise ValueError(msg)

        if fixture_name not in self._test_fixtures_generators[test_name]:
            self._test_fixtures_generators[test_name][fixture_name] = generator

    def run_tests(self) -> None:
        test_results: Dict[str, TestResult] = {}
        for test_name, test_cases in self._tests.items():
            for idx, (test_func, params) in enumerate(test_cases):
                case_name = f"{test_name}[{idx}]" if len(test_cases) > 1 else test_name
                message = ""
                status = TestStatus.passed
                try:
                    test_func(*params)
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

                test_results[case_name] = TestResult(
                    status=status,
                    message=message if status == TestStatus.failed else "Test passed",
                )
        show_results(test_results)


test_runner = TestRunner()
