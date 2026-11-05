import contextlib
import os
import sys
from collections import namedtuple
from collections.abc import Generator, Sequence
from typing import TextIO

import rota.colours

ASCII_CURSOR_UP = "\x1b[1F"
ASCII_CLEAR_LINE = "\x1b[2K"
ASCII_HIDE_CURSOR = "\x1b[?25l"
ASCII_SHOW_CURSOR = "\x1b[?25h"

B_KEY_ESC = b"\x1b"
if sys.platform == "win32":  # pragma: win32 cover
    B_KEY_RETURN = b"\r"
    B_KEY_UP = b"\xe0H"
    B_KEY_DOWN = b"\xe0P"
    B_KEY_RIGHT = b"\xe0M"
    B_KEY_LEFT = b"\xe0K"
else:  # pragma: win32 no cover
    B_KEY_RETURN = b"\n"
    B_KEY_UP = b"\x1b[A"
    B_KEY_DOWN = b"\x1b[B"
    B_KEY_RIGHT = b"\x1b[C"
    B_KEY_LEFT = b"\x1b[D"
    B_KEY_SHIFT_UP = b"\x1b[1;2A"
    B_KEY_SHIFT_DOWN = b"\x1b[1;2B"
    B_KEY_SHIFT_RIGHT = b"\x1b[1;2C"
    B_KEY_SHIFT_LEFT = b"\x1b[1;2D"

MenuOption = namedtuple("MenuOption", ["value", "label"])


def _write(stream: TextIO, message: str) -> None:
    """
    Write and flush a message to the given stream.
    """

    stream.write(message)
    stream.flush()


def _getch() -> bytes:
    """
    Prompt for single-key user input.

    Like `input()`, but returns immediately after one keypress.

    ---

    Source - https://stackoverflow.com/a/47197390
    Posted by neoDev, modified by community. See post 'Timeline' for change history
    Retrieved 2026-10-30, License - CC BY-SA 3.0
    """

    if sys.platform == "win32":  # pragma: win32 cover
        import msvcrt

        key = msvcrt.getch()
        if key in (bytes([0]), bytes([224])):
            key = key + msvcrt.getch()

        return key
    else:  # pragma: win32 no cover
        import termios
        import tty

        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        try:
            return os.read(sys.stdin.fileno(), 32)
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


@contextlib.contextmanager
def hide_cursor() -> Generator[None]:
    """
    Return a context manager which hides the terminal cursor.
    """

    _write(sys.stdout, ASCII_HIDE_CURSOR)
    yield
    _write(sys.stdout, ASCII_SHOW_CURSOR)


def display_menu(options: Sequence[MenuOption]) -> str | None:
    """
    Display a navigable menu for the provided options, and return the
    selected option.
    """

    l, i, row = len(options), -1, 0
    while True:
        i += 1
        if i == 0:
            key = b""
        else:
            key = _getch()
            for _ in range(l):
                _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}{ASCII_CURSOR_UP}")

        if key == B_KEY_ESC:
            _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}")
            return None
        elif key == B_KEY_RETURN:
            _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}")
            return options[row].value

        increment = {B_KEY_UP: -1, B_KEY_DOWN: 1}.get(key, 0)
        row = (row + increment) % l

        output = ""
        for n, (_, label) in enumerate(options):
            if n == row:
                output += f"* {rota.colours.colour(label, rota.colours.BLUE + rota.colours.BOLD)}\n"
            else:
                output += f"  {label}\n"

        _write(sys.stdout, output)
