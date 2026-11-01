"""
End-to-end tests for the ``rota`` application.
"""

import os
import pathlib
import signal
import sys
import termios
import textwrap
import threading
import time
import tty
import unittest.mock
import uuid
from collections.abc import Generator

import pytest

from rota.main import main

B_KEY_ESC = b"\x1b"
B_KEY_RETURN = b"\n"
B_KEY_UP = b"\x1b[A"
B_KEY_DOWN = b"\x1b[B"


@pytest.fixture(autouse=True)
def data_home(tmp_path: pathlib.Path) -> Generator[pathlib.Path]:
    os.environ["XDG_STATE_HOME"] = str(tmp_path)  # probably naughty to add this here too
    os.environ["XDG_DATA_HOME"] = str(tmp_path)
    yield tmp_path / "rota"


def test__rota_without_command_prints_help(
    capsys: pytest.CaptureFixture,
):
    rc = main([])
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

    rc = main(("init", rota_name))
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
        main(("init", name))


def test__init__rota_cannot_be_created__because_rota_already_exists(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("init", rota_name))
    captured = capsys.readouterr()
    assert rc == 1
    assert expected_db_path.exists()
    assert captured.out == ""
    assert captured.err == f"error: rota '{rota_name}' already exists\n"


def test__init__rota_can_be_created__with_no_members(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == ""


@pytest.mark.parametrize(
    "members_csv, expected_stdout",
    [
        ("", ""),
        ("foo", "foo: \n"),
        ("    foo      ", "foo: \n"),
        ("foo,bar", "bar: \nfoo: \n"),
        ("    foo ,     bar    ", "bar: \nfoo: \n"),
        ("Foo Bar,Baz Qux,Ahoy!", "Ahoy!: \nBaz Qux: \nFoo Bar: \n"),
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

    rc = main(("init", rota_name, "--members", members_csv))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == expected_stdout
    assert captured.err == ""


def test__list__no_rotas_prints_nothing(
    capsys: pytest.CaptureFixture,
):
    rc = main(("list",))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == ""
    assert captured.err == ""


def test__list__rotas_can_be_listed(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    for name in ("foo", "bar", "baz"):
        main(("init", name))

    rc = main(("list",))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.err == ""
    assert captured.out == textwrap.dedent(
        f"""\
        bar  ({data_home / 'rota__bar.db'})
        baz  ({data_home / 'rota__baz.db'})
        foo  ({data_home / 'rota__foo.db'})
        """
    )


def test__delete__rota_can_be_deleted(
    data_home: pathlib.Path,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"

    rc = main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("delete", rota_name))
    assert rc == 0
    assert not expected_db_path.exists()


def test__delete__rota_cannot_be_deleted__because_it_does_not_exist(
    data_home: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = data_home / f"rota__{rota_name}.db"
    assert not expected_db_path.exists()

    rc = main(("delete", rota_name))
    captured = capsys.readouterr()
    assert not expected_db_path.exists()
    assert rc == 1
    assert captured.out == ""
    assert captured.err.startswith("error: rota not found at ")


def test__run__rota_can_be_run__with_existing_member(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nfoo: \n"
    assert captured.err == ""

    foo_at = '2020-01-01 10:00:00'
    main(("run", rota_name, "--member", "foo", "--at", foo_at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar: \nfoo: {foo_at}\n"
    assert captured.err == ""

    bar_at = '2020-01-01 11:00:00'
    main(("run", rota_name, "--member", "bar", "--at", bar_at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"foo: {foo_at}\nbar: {bar_at}\n"
    assert captured.err == ""


def test__run__rota_can_be_run__with_new_member(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nfoo: \n"
    assert captured.err == ""

    at = '2020-01-01 12:00:00'
    main(("run", rota_name, "--member", "baz", "--at", at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar: \nfoo: \nbaz: {at}\n"
    assert captured.err == ""


def test__run__rota_can_be_run__and_then_shown(
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nfoo: \n"
    assert captured.err == ""

    at = '2020-01-01 12:00:00'
    rc = main(
        ("run", rota_name, "--member", "baz", "--at", at, "--show")
    )
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar: \nfoo: \nbaz: {at}\n"
    assert captured.err == ""


def test__run__rota_can_be_run__with_interactive_menu(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nbaz: \nfoo: \n"
    assert captured.err == ""

    monkeypatch.setattr(termios, "tcgetattr", lambda _: [])
    monkeypatch.setattr(termios, "tcsetattr", lambda *_: None)
    monkeypatch.setattr(tty, "setcbreak", lambda _: None)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)  # noqa

    mock_read = unittest.mock.Mock()
    # Test that the cursor can move *and* cycle
    mock_read.side_effect = [
        B_KEY_DOWN,
        B_KEY_DOWN,
        B_KEY_DOWN,
        B_KEY_DOWN,
        B_KEY_UP,
        B_KEY_DOWN,
        B_KEY_RETURN,
    ]
    monkeypatch.setattr(os, "read", mock_read)
    at = '2020-01-01 12:00:00'

    rc = main(("run", rota_name, "--at", at))
    capsys.readouterr()

    main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nfoo: \nbaz: 2020-01-01 12:00:00\n"
    assert captured.err == ""


def test__run__rota_can_be_run__and_interactive_menu_cancelled(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nbaz: \nfoo: \n"
    assert captured.err == ""

    monkeypatch.setattr(termios, "tcgetattr", lambda _: [])
    monkeypatch.setattr(termios, "tcsetattr", lambda *_: None)
    monkeypatch.setattr(tty, "setcbreak", lambda _: None)
    monkeypatch.setattr(sys.stdin, "fileno", lambda: 0)  # noqa
    monkeypatch.setattr(os, "read", lambda *_: B_KEY_ESC)

    rc = main(("run", rota_name))
    capsys.readouterr()

    main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nbaz: \nfoo: \n"
    assert captured.err == ""


def test__run__rota_can_be_run__and_sigint_is_handled_gracefully(
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar,baz"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nbaz: \nfoo: \n"
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

    rc = main(("run", rota_name))
    capsys.readouterr()

    main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: \nbaz: \nfoo: \n"
    assert captured.err == ""
