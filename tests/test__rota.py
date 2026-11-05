"""
End-to-end tests for the ``rota`` application.
"""

import os
import pathlib
import signal
import sys
import textwrap
import threading
import time
import unittest.mock
import uuid
from collections.abc import Generator

import pytest

from rota import colours, main, menu

if sys.platform == "win32":  # pragma: win32 cover
    import msvcrt
else:  # pragma: win32 no cover
    import termios
    import tty


@pytest.fixture(autouse=True)
def data_home(tmp_path: pathlib.Path) -> Generator[pathlib.Path]:
    os.environ["XDG_STATE_HOME"] = str(tmp_path)  # probably naughty to add this here too
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    yield tmp_path / "rota"


def test__rota_without_command_prints_help(
    capsys: pytest.CaptureFixture,
):
    rc = main.main([])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert "usage:" in captured.out
    assert "positional arguments:" in captured.out
    assert "options:" in captured.out


def test__init__rota_can_be_created(
    data_home: pathlib.Path,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main.main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()


@pytest.mark.parametrize(
    "name",
    [
        "bad name",
        "bad_name",
        "bad-name!",
    ],
)
def test__init__rota_cannot_be_created__because_of_invalid_name(
    name: str,
):
    # TODO: This should be a CLI error, not an exception!
    with pytest.raises(ValueError):
        main.main(("init", name))


def test__init__rota_cannot_be_created__because_rota_already_exists(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main.main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main.main(("init", rota_name))
    captured = capsys.readouterr()
    assert rc == 1
    assert expected_db_path.exists()
    assert captured.out == ""
    assert captured.err == f"{colours.RED}error: rota '{rota_name}' already exists{colours.RESET}\n"


def test__init__rota_can_be_created__with_no_members(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main.main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    "members_csv, expected_stdout",
    [
        ("", ""),
        ("foo", "foo  \n"),
        ("    foo      ", "foo  \n"),
        ("foo,bar", "bar  \nfoo  \n"),
        ("    foo ,     bar    ", "bar  \nfoo  \n"),
        ("Foo Bar,Baz Qux,Ahoy!", "Ahoy!    \nBaz Qux  \nFoo Bar  \n"),
    ],
)
def test__init__rota_can_be_created__with_members(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
    members_csv: str,
    expected_stdout: str,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main.main(("init", rota_name, "--members", members_csv))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == expected_stdout
    assert captured.err == ""


def test__list__no_rotas_prints_nothing(
    capsys: pytest.CaptureFixture,
):
    rc = main.main(("list",))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == ""


def test__list__rotas_can_be_listed(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    for name in ("foo", "bar", "baz"):
        main.main(("init", name))

    rc = main.main(("list",))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert captured.out == textwrap.dedent(
        f"""\
        bar     {colours.GREY}{data_home / 'rota__bar.db'}{colours.RESET}
        baz     {colours.GREY}{data_home / 'rota__baz.db'}{colours.RESET}
        foo     {colours.GREY}{data_home / 'rota__foo.db'}{colours.RESET}
        """
    )


def test__delete__rota_can_be_deleted(
    data_home: pathlib.Path,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main.main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main.main(("delete", rota_name))
    assert rc == 0
    assert not expected_db_path.exists()


def test__delete__rota_cannot_be_deleted__because_it_does_not_exist(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"
    assert not expected_db_path.exists()

    rc = main.main(("delete", rota_name))
    captured = capsys.readouterr()
    assert not expected_db_path.exists()
    assert rc == 1
    assert captured.out == ""
    assert captured.err.startswith(f"{colours.RED}error: rota not found at ")


def test__run__rota_can_be_run__with_existing_member(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nfoo  \n"
    assert captured.err == ""

    foo_at = '2020-01-01 10:00:00'
    main.main(("run", rota_name, "--member", "foo", "--at", foo_at))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar  \nfoo  {foo_at}\n"
    assert captured.err == ""

    bar_at = '2020-01-01 11:00:00'
    main.main(("run", rota_name, "--member", "bar", "--at", bar_at))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"foo  {foo_at}\nbar  {bar_at}\n"
    assert captured.err == ""


def test__run__rota_can_be_run__with_new_member(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nfoo  \n"
    assert captured.err == ""

    at = '2020-01-01 12:00:00'
    main.main(("run", rota_name, "--member", "baz", "--at", at))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar  \nfoo  \nbaz  {at}\n"
    assert captured.err == ""


def test__run__rota_can_be_run__and_then_shown(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nfoo  \n"
    assert captured.err == ""

    at = '2020-01-01 12:00:00'
    rc = main.main(
        ("run", rota_name, "--member", "baz", "--at", at, "--show")
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar  {colours.GREY}{colours.RESET}\nfoo  {colours.GREY}{colours.RESET}\nbaz  {colours.GREY}{at}{colours.RESET}\n"
    assert captured.err == ""
    assert captured.err == ""


def test__run__rota_cannot_be_run__because_there_are_no_members(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name))
    rc = main.main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == ""

    rc = main.main(("run", rota_name))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert captured.err == f"{colours.RED}error: no members to choose from{colours.RESET}\n"


@pytest.mark.skipif(sys.platform != "win32", reason="only run on windows")
def test__run__rota_can_be_run__with_interactive_menu__windows(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""

    mock_read = unittest.mock.Mock()
    # Test that the cursor can move *and* cycle
    mock_read.side_effect = [
        *(b"\xe0", b"P"),  # Down
        *(b"\xe0", b"P"),  # Down
        *(b"\xe0", b"P"),  # Down
        *(b"\xe0", b"P"),  # Down
        *(b"\xe0", b"H"),  # Up
        *(b"\xe0", b"P"),  # Down
        menu.B_KEY_RETURN,
    ]
    monkeypatch.setattr(msvcrt, "getch", mock_read)
    at = '2020-01-01 12:00:00'

    rc = main.main(("run", rota_name, "--at", at))
    capsys.readouterr()

    main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nfoo  \nbaz  2020-01-01 12:00:00\n"
    assert captured.err == ""


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test__run__rota_can_be_run__with_interactive_menu__posix(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""

    monkeypatch.setattr(termios, "tcgetattr", lambda _: [])
    monkeypatch.setattr(termios, "tcsetattr", lambda *_: None)
    monkeypatch.setattr(tty, "setcbreak", lambda _: None)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)  # noqa

    mock_read = unittest.mock.Mock()
    # Test that the cursor can move *and* cycle
    mock_read.side_effect = [
        menu.B_KEY_DOWN,
        menu.B_KEY_DOWN,
        menu.B_KEY_DOWN,
        menu.B_KEY_DOWN,
        menu.B_KEY_UP,
        menu.B_KEY_DOWN,
        menu.B_KEY_RETURN,
    ]
    monkeypatch.setattr(os, "read", mock_read)
    at = '2020-01-01 12:00:00'

    rc = main.main(("run", rota_name, "--at", at))
    capsys.readouterr()

    main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nfoo  \nbaz  2020-01-01 12:00:00\n"
    assert captured.err == ""


@pytest.mark.skipif(sys.platform != "win32", reason="only run on windows")
def test__run__rota_can_be_run__and_interactive_menu_cancelled__windows(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""

    monkeypatch.setattr(msvcrt, "getch", lambda *_: menu.B_KEY_ESC)

    rc = main.main(("run", rota_name))
    capsys.readouterr()

    main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test__run__rota_can_be_run__and_interactive_menu_cancelled__posix(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""

    monkeypatch.setattr(termios, "tcgetattr", lambda _: [])
    monkeypatch.setattr(termios, "tcsetattr", lambda *_: None)
    monkeypatch.setattr(tty, "setcbreak", lambda _: None)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)  # noqa
    monkeypatch.setattr(os, "read", lambda *_: menu.B_KEY_ESC)

    rc = main.main(("run", rota_name))
    capsys.readouterr()

    main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""


@pytest.mark.skipif(sys.platform == "win32", reason="does not run on windows")
def test__run__rota_can_be_run__and_sigint_is_handled_gracefully(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main.main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""

    monkeypatch.setattr(termios, "tcgetattr", lambda _: [])
    monkeypatch.setattr(termios, "tcsetattr", lambda *_: None)
    monkeypatch.setattr(tty, "setcbreak", lambda _: None)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)  # noqa
    monkeypatch.setattr(os, "read", lambda *_: time.sleep(1))

    pid = os.getpid()
    def trigger_signal():
        # https://stackoverflow.com/a/49615525/8213085
        time.sleep(0.01)
        os.kill(pid, signal.SIGINT)

    thread = threading.Thread(target=trigger_signal)
    thread.daemon = True
    thread.start()

    rc = main.main(("run", rota_name))
    capsys.readouterr()

    main.main(("show", rota_name, "--no-colour"))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar  \nbaz  \nfoo  \n"
    assert captured.err == ""
