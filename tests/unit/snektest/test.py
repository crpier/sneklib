from snek.snektest.runner import fixture, load_fixture, test, test_runner

root_fixture_started_up = False
root_fixture_torn_down = False
child_fixture_started_up = False
child_fixture_torn_down = False


@fixture()
def load_root_fixture():
    global root_fixture_started_up
    root_fixture_started_up = True

    yield 1

    global root_fixture_torn_down
    root_fixture_torn_down = True


@fixture()
def load_child_fixture():
    root_fixture = load_fixture(load_root_fixture)
    global child_fixture_started_up
    child_fixture_started_up = True

    yield root_fixture + 1

    global child_fixture_torn_down
    child_fixture_torn_down = True


@test()
def root_fixture_passes_correct_value():
    root_fixture = load_fixture(load_root_fixture)
    assert root_fixture == 1


@test()
def root_fixture_is_started_up():
    load_fixture(load_root_fixture)
    assert root_fixture_started_up is True


@test()
def root_fixture_is_torn_down():
    assert root_fixture_torn_down is True


@test()
def child_fixture_passes_correct_value():
    child_fixture = load_fixture(load_child_fixture)
    assert child_fixture == 2


@test()
def child_fixture_is_started_up():
    load_fixture(load_child_fixture)
    assert child_fixture_started_up is True


@test()
def child_fixture_is_torn_down():
    load_fixture(load_child_fixture)
    assert child_fixture_torn_down is True


test_runner.run_tests()
