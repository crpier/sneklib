from snek.snektest.runner import fixture, test, test_runner


@fixture
def fixture_func():
    print("I'm a fixture")


@test()
def test_basic_works():
    assert True


@test()
def test_basic_fails():
    assert False


# TODO: test xfail, xpass, async tests, fixtures, async fixtures

test_runner.run_tests()
