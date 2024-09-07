import pytest

from snek.snektest.presentation import Colors


def test_remove_color_codes():
    colored_text = f"{Colors.RED}This is red{Colors.RESET} and {Colors.BLUE}this is blue{Colors.RESET}"
    expected_text = "This is red and this is blue"
    assert (
        Colors.remove_color_codes(colored_text) == expected_text
    ), "Color codes were not removed correctly"


def test_remove_color_codes_empty_string():
    assert Colors.remove_color_codes("") == "", "Empty string should remain empty"


def test_remove_color_codes_no_colors():
    text = "This text has no color codes"
    assert (
        Colors.remove_color_codes(text) == text
    ), "Text without color codes should remain unchanged"


def test_add_color():
    text = "This text has no color codes"
    assert (
        Colors.add_color(text, Colors.RED) == f"{Colors.RED}{text}{Colors.RESET}"
    ), "Color codes were not added correctly"


def test_apply_multiple_colors_single_color():
    color_map = {"Hello": Colors.RED}
    result = Colors.apply_multiple_colors(color_map)
    print(result, end=" ")
    assert result == f"{Colors.RED}Hello{Colors.RESET}"


def test_apply_multiple_colors_multiple_colors():
    color_map = {"Hello, ": Colors.RED, "World": Colors.BLUE}
    result = Colors.apply_multiple_colors(color_map)
    print(result, end=" ")
    assert (
        result == f"{Colors.RED}Hello, {Colors.RESET}{Colors.BLUE}World{Colors.RESET}"
    )


def test_apply_multiple_colors_empty_map():
    color_map = {}
    result = Colors.apply_multiple_colors(color_map)
    print(result, end=" ")
    assert result == ""


def test_apply_multiple_colors_with_spaces():
    color_map = {"Hello ": Colors.RED, "World": Colors.BLUE}
    result = Colors.apply_multiple_colors(color_map)
    print(result, end=" ")
    assert result == f"{Colors.RED}Hello {Colors.RESET}{Colors.BLUE}World{Colors.RESET}"


@pytest.mark.parametrize(
    "color_map, expected_output",
    [
        (
            {"Hello": Colors.RED, " ": None, "World": Colors.BLUE},
            f"{Colors.RED}Hello{Colors.RESET} {Colors.BLUE}World{Colors.RESET}",
        ),
        (
            {"Test": Colors.GREEN, "ing": Colors.YELLOW},
            f"{Colors.GREEN}Test{Colors.RESET}{Colors.YELLOW}ing{Colors.RESET}",
        ),
        ({"No": None, " ": None, "Color": None}, "No Color"),
    ],
)
def test_apply_multiple_colors(color_map, expected_output):
    result = Colors.apply_multiple_colors(color_map)
    print(result, end=" ")
    assert result == expected_output
