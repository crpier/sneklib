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
    params: list[tuple]


T = TypeVar("T")
P = ParamSpec("P")
type Generator[T] = _Generator[T, None, None]

_fixture_configs: dict[str, FixtureConfig] = {}


def load_fixture(fixture: Callable[..., _Generator[T, None, None]]) -> T:
    fixture_data = _fixture_configs[fixture.__name__]
    test_name = test_runner._get_fixture_context()
    if test_name is None:
        msg = f"Could not find test for fixture {fixture.__name__}"
        raise ValueError(msg)
    if fixture.__name__ not in test_runner._test_fixtures_calls[test_name]:
        test_runner._test_fixtures_calls[test_name][fixture.__name__] = 0
    try:
        generator = fixture(
            *fixture_data["params"][
                test_runner._test_fixtures_calls[test_name][fixture.__name__]
            ]
        )
    except IndexError:
        generator = fixture(*fixture_data["params"][0])

    # that's so ugly I'm ashamed of myself
    test_runner._test_fixtures_calls[test_name][fixture.__name__] += 1
    if (
        len(fixture_data["params"])
        - test_runner._test_fixtures_calls[test_name][fixture.__name__]
        > 0
    ):
        test_name = test_runner._get_fixture_context()
        if test_name is not None and test_name in test_runner._tests:
            tests_to_duplicate = test_runner._tests[test_name]
            test_runner._tests[test_name].extend(tests_to_duplicate)
    if _fixture_configs[fixture.__name__]["scope"] == "test":
        test_runner._add_test_fixture(fixture, generator)
    elif _fixture_configs[fixture.__name__]["scope"] == "session":
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


def fixture(*params: Unpack[T2], scope: FixtureScope = "test"):
    def decorator(func: Callable[..., Generator[T]]):
        if (fixture_config := _fixture_configs.get(func.__name__)) is None:
            _fixture_configs[func.__name__] = {
                "scope": scope,
                "params": [params],
            }
        else:
            if fixture_config.get("params") is None:
                _fixture_configs[func.__name__]["params"] = [params]
            else:
                _fixture_configs[func.__name__]["params"].append(params)
        return func

    return decorator


class TestRunner:
    def __init__(self) -> None:
        self._tests: Dict[str, List[Tuple[Callable[..., None], Tuple[Any, ...]]]] = {}
        self._test_fixtures_generators: Dict[
            str, Dict[str, _Generator[Any, None, None]]
        ] = defaultdict(dict)
        self._test_fixtures_calls: Dict[str, Dict[str, int]] = defaultdict(dict)

    def _add_test(self, new_test: Callable[..., None], params: Any) -> None:
        if new_test.__name__ not in self._tests:
            self._tests[new_test.__name__] = []
        self._tests[new_test.__name__].append((new_test, params))

    def _get_fixture_context(self) -> str | None:
        """Return the current test name"""
        # walk up the stack until we find load_fixture
        # the frame before that is the test that called it
        test_name: str | None = None
        for idx, frame in enumerate(traceback.extract_stack()):
            if frame.name == "load_fixture":
                test_name = traceback.extract_stack()[idx - 1].name
        return test_name

    def _add_test_fixture(
        self,
        fixture: Callable[..., _Generator[T, None, None]],
        generator: _Generator[T, None, None],
    ) -> None:
        fixture_name = fixture.__name__
        test_name = self._get_fixture_context()

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
                except Exception:
                    status = TestStatus.failed
                    message = f"Unexpected error: {traceback.format_exc()}"

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
            self._test_fixtures_calls = defaultdict(dict)
            self._test_fixtures_generators = defaultdict(dict)
        show_results(test_results)


test_runner = TestRunner()
