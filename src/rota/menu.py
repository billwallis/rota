import contextlib
import os
import sys
import termios
import tty
from collections import namedtuple
from collections.abc import Generator, Sequence
from typing import TextIO

import rota.colours

ASCII_CURSOR_UP = "\x1b[1F"
ASCII_CLEAR_LINE = "\x1b[2K"
ASCII_HIDE_CURSOR = "\x1b[?25l"
ASCII_SHOW_CURSOR = "\x1b[?25h"
KEY_ESC = "\x1b"
KEY_RETURN = "\n"
KEY_UP = "\x1b[A"
KEY_DOWN = "\x1b[B"
KEY_RIGHT = "\x1b[C"
KEY_LEFT = "\x1b[D"
KEY_SHIFT_UP = "\x1b[1;2A"
KEY_SHIFT_DOWN = "\x1b[1;2B"
KEY_SHIFT_RIGHT = "\x1b[1;2C"
KEY_SHIFT_LEFT = "\x1b[1;2D"

MenuOption = namedtuple("MenuOption", ["value", "label"])


def _write(stream: TextIO, message: str) -> None:
    """
    Write and flush a message to the given stream.
    """

    stream.write(message)
    stream.flush()


def _getch() -> str:
    """
    Prompt for single-key user input.

    Like `input()`, but returns immediately after one keypress.

    ---

    Source - https://stackoverflow.com/a/47197390
    Posted by neoDev, modified by community. See post 'Timeline' for change history
    Retrieved 2026-10-30, License - CC BY-SA 3.0
    """

    # TODO: Make OS-independent, currently only works on POSIX

    old_settings = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin.fileno())
    try:
        return os.read(sys.stdin.fileno(), 32).decode()
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
            key = ""
        else:
            key = _getch()
            for _ in range(l):
                _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}{ASCII_CURSOR_UP}")

        if key == KEY_ESC:
            _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}")
            return None
        elif key == KEY_RETURN:
            _write(sys.stdout, f"\r{ASCII_CLEAR_LINE}")
            return options[row].value

        increment = {KEY_UP: -1, KEY_DOWN: 1}.get(key, 0)
        row = (row + increment) % l

        output = ""
        for n, (_, label) in enumerate(options):
            if n == row:
                output += f"* {rota.colours.colour(label, rota.colours.BLUE + rota.colours.BOLD)}\n"
            else:
                output += f"  {label}\n"

        _write(sys.stdout, output)
