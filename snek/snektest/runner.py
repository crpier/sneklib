import random
import string
import traceback
from collections.abc import Generator as _Generator
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Iterator,
    Literal,
    NamedTuple,
    ParamSpec,
    Tuple,
    TypeVar,
    TypeVarTuple,
    Unpack,
)

from snek.snektest.results import TestResult, TestStatus, show_results

T = TypeVar("T")
T2 = TypeVarTuple("T2")
P = ParamSpec("P")
Generator = _Generator[T, None, None]


FixtureScope = Literal["test", "session"]


class RegisteredFixture:
    name: str
    function: Callable[..., Generator]
    scope: FixtureScope
    fixture_params: list[tuple[Any]]

    def __init__(
        self,
        name: str,
        function: Callable[..., Generator],
        scope: FixtureScope,
        fixture_params: list[tuple] | None = None,
    ):
        self.name = name
        self.function = function
        self.scope = scope
        if fixture_params is None:
            fixture_params = []
        self.fixture_params = fixture_params
        self._stop_registering = False
        self._params_idx = 0

    def register_params(self, fixture_param: tuple[Any]) -> None:
        if self._stop_registering:
            raise ValueError("Cannot register more params loading the fixture")
        # This happens when a fixture is parametrized
        # TODO: will this ever be None?
        if self.fixture_params is None:
            self.fixture_params = [fixture_param]
        else:
            self.fixture_params.append(fixture_param)

    def next_params(self) -> tuple[Any] | None:
        if self.fixture_params is None:
            return None
        self._params_idx += 1
        # try:
        return self.fixture_params[self._params_idx - 1]
        # except IndexError as e:
        #     __import__('pdb').set_trace()
        #     print(e)

    def reset_params_idx(self) -> tuple[Any] | None:
        self._params_idx = 0


class RegisteredFixturesContainer:
    def __init__(self):
        self._registered_fixtures: dict[Callable, RegisteredFixture] = {}

    def register_fixture(
        self,
        func: Callable[..., Generator],
        fixture_param: tuple[Any],
        scope: FixtureScope = "test",
    ):
        name = func.__name__
        if func not in self._registered_fixtures:
            self._registered_fixtures[func] = RegisteredFixture(
                name, func, scope, [fixture_param]
            )
        else:
            self._registered_fixtures[func].register_params(fixture_param)

    def get_by_function(self, func: Callable) -> RegisteredFixture | None:
        return self._registered_fixtures.get(func)

    def reset_param_indexes(self):
        for fixture in self._registered_fixtures.values():
            fixture.reset_params_idx()


@dataclass
class RegisteredTest:
    func: Callable[..., None]
    test_name: str
    test_params: list[tuple[Any]]

    def register_params(self, test_params: list[tuple[Any]]):
        self.test_params.extend(test_params)


class RegisteredTestsContainer:
    def __init__(self):
        self.registered_tests: dict[Callable, RegisteredTest] = {}

    def register_test(
        self,
        func: Callable[..., None],
        test_params: tuple,
    ):
        """Allow registering a test multipe times with different params"""
        test_params_to_add: list[tuple[Any]]
        # params is be empty if the test is not parametrized
        if len(test_params) == 0:
            test_params_to_add = []
        else:
            test_params_to_add = [test_params]

        if func not in self.registered_tests:
            self.registered_tests[func] = RegisteredTest(
                func, func.__name__, test_params_to_add
            )
        else:
            self.registered_tests[func].register_params(test_params_to_add)

    def __iter__(self) -> Iterator[RegisteredTest]:
        return iter(self.registered_tests.values())


class TestSession:
    def __init__(self):
        self.tests = RegisteredTestsContainer()
        self.fixtures = RegisteredFixturesContainer()

    def register_test_instance(
        self, new_test: Callable[..., None], test_params: tuple
    ) -> None:
        self.tests.register_test(new_test, test_params)

    def register_fixture(
        self,
        func: Callable[..., Generator],
        fixture_params: tuple,
        scope: FixtureScope = "test",
    ):
        self.fixtures.register_fixture(func, fixture_params, scope)

    def run_tests(self) -> None:
        test_results: dict[str, TestResult] = {}
        for test in self.tests:
            global test_runner
            test_runner = TestRunner(
                fixtures=self.fixtures,
                test_func=test.func,
                test_params=test.test_params,
                test_name=test.test_name,
            )
            results = test_runner.run_test()
            # TODO: this should also contain test params and fixture params
            for status, message in results:
                test_results[test.test_name + random_string(5)] = TestResult(
                    status=status, message=message
                )
            test_runner = None

        show_results(test_results)


def random_string(length: int) -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=length))


class StartedFixture(NamedTuple):
    fixture_name: str
    generator: Generator
    last_result: Any


class TestRunner:
    def __init__(
        self,
        fixtures: RegisteredFixturesContainer,
        test_func: Callable,
        test_params: list[tuple[Any]],
        test_name: str,
    ):
        self.fixtures = fixtures
        self.test_func = test_func
        self.test_params = test_params
        self.fixture_params = []
        self.test_name = test_name
        self.started_up_fixtures: dict[Callable, StartedFixture] = {}
        self.fixture_param_repeats = 1

    def load_fixture(self, fixture_func: Callable[..., Generator[T]]) -> T:
        if fixture_func in self.started_up_fixtures:
            return self.started_up_fixtures[fixture_func].last_result

        fixture_data = self.fixtures.get_by_function(fixture_func)
        if fixture_data is None:
            raise ValueError(
                f"Could not load fixture {fixture_func.__name__}: fixture not registered"
            )
        caller = self.get_load_fixture_caller()
        if caller is None:
            raise ValueError(f"Could not find test for fixture {fixture_func.__name__}")

        fixture_params = fixture_data.next_params()
        if len(fixture_data.fixture_params) - fixture_data._params_idx > 0:
            self.fixture_param_repeats += 1

        if fixture_params is None:
            generator = fixture_func()
        else:
            generator = fixture_func(*fixture_params)

        result = next(generator)
        self.started_up_fixtures[fixture_func] = StartedFixture(
            fixture_name=fixture_func.__name__, generator=generator, last_result=result
        )

        return result

    def run_test(self) -> list[Tuple[TestStatus, str]]:
        results: list[Tuple[TestStatus, str]] = []
        if len(self.test_params) == 0:
            while self.fixture_param_repeats > 0:
                self.fixture_param_repeats -= 1
                results.append(self.run_test_instance(self.test_func, tuple()))
            self.fixtures.reset_param_indexes()
        else:
            for params in self.test_params:
                for _ in range(self.fixture_param_repeats):
                    results.append(self.run_test_instance(self.test_func, params))
                self.fixtures.reset_param_indexes()
        return results

    def run_test_instance(
        self, test_func: Callable, test_params: tuple[Any]
    ) -> Tuple[TestStatus, str]:
        try:
            test_func(*test_params)
            status, message = TestStatus.passed, "Test passed"
        except AssertionError:
            status, message = TestStatus.failed, traceback.format_exc()
        except Exception:
            status, message = (
                TestStatus.failed,
                f"Unexpected error: {traceback.format_exc()}",
            )
        message += self._teardown_test_fixtures(self.test_name)
        return status, message

    def _teardown_test_fixtures(self, test_name: str) -> str:
        message = ""
        for fixture in self.started_up_fixtures.values():
            try:
                next(fixture.generator)
                raise ValueError(
                    f"Fixture {fixture.fixture_name} for test {test_name} has more than one 'yield'"
                )
            except StopIteration:
                pass
            except Exception:
                message += f"Unexpected error tearing down fixture {fixture.fixture_name} for test {test_name}: \n{traceback.format_exc()}\n"
        self.started_up_fixtures.clear()
        return message

    def get_load_fixture_caller(self) -> str | None:
        for idx, frame in enumerate(traceback.extract_stack()):
            if frame.name == load_fixture.__name__:
                return traceback.extract_stack()[idx - 1].name
        return None


test_runner: TestRunner | None = None
test_session = TestSession()

### PUBLIC API ###


# TODO: if a certain env var set by the runner is not present,
# these functions should be noops
def load_fixture(fixture: Callable[..., _Generator[T, None, None]]) -> T:
    if test_runner is None:
        raise ValueError("load_fixture can only be used inside a test")
    return test_runner.load_fixture(fixture)


def test(*params: Unpack[T2]) -> Callable[[Callable[..., None]], Callable[..., None]]:
    def decorator(test_func: Callable[..., None]) -> Callable[..., None]:
        test_session.register_test_instance(test_func, params)
        return test_func

    return decorator


def fixture(*params: Unpack[T2], scope: FixtureScope = "test"):
    def decorator(func: Callable[..., Generator[T]]):
        test_session.register_fixture(func, params, scope)
        return func

    return decorator
