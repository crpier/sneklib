from shutil import get_terminal_size
from typing import Mapping

from colorama import Fore


class ColoredString(str):
    def __new__(cls, string: str, __original_length__: int):
        return super().__new__(cls, string)

    def __init__(self, __string__: str, original_length: int):
        self.original_length = original_length
        super().__init__()


# Color definitions using colorama
class Colors:
    RESET = Fore.RESET
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    BLUE = Fore.BLUE

    @classmethod
    def get_colors(cls) -> list[str]:
        return [
            getattr(cls, attr)
            for attr in dir(cls)
            if not attr.startswith("__") and not callable(getattr(cls, attr))
        ]

    @classmethod
    def remove_color_codes(cls, text: str) -> str:
        color_codes = [color for color in cls.get_colors()]
        for code in color_codes:
            text = text.replace(code, "")
        return text

    @classmethod
    def add_color(cls, text: str, color: str) -> str:
        return f"{color}{text}{cls.RESET}"

    @classmethod
    def apply_multiple_colors(
        cls, color_map: Mapping[str, str | None]
    ) -> ColoredString:
        result_list = []
        original_length = 0
        for substring, color in color_map.items():
            colored_substring = cls.add_color(substring, color) if color else substring
            result_list.append(colored_substring)
            original_length += len(substring)
        result = ColoredString("".join(result_list), original_length)
        return result


def pad_string_to_screen_width(summary: ColoredString, pad_char: str = "-") -> str:
    # TODO: how would I go about validating that the pad_char is a single character?
    terminal_width, _ = get_terminal_size()

    # Add padding if there's enough room
    if summary.original_length + 2 < terminal_width:  # 2 spaces added extra
        padding = pad_char * ((terminal_width - summary.original_length - 2) // 2)
        result = f"{padding} {summary} {padding}"
    else:
        result = summary
    return result
