import datetime
import os
import pathlib
import uuid
from collections.abc import Generator

import pytest

from rota.main import main


@pytest.fixture
def tmp_dir(tmp_path: pathlib.Path) -> Generator[pathlib.Path]:
    os.chdir(tmp_path)
    yield tmp_path


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


def test__rota_list__is_not_implemented(
    capsys: pytest.CaptureFixture,
):
    rc = main(("list",))
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert captured.err == "error: not implemented yet\n"


@pytest.mark.parametrize(
    "name",
    [
        "bad name",
        "bad_name",
        "bad-name!",
    ],
)
def test__rota_cannot_be_created__because_of_invalid_name(
    tmp_dir: pathlib.Path,
    name: str,
):
    with pytest.raises(ValueError):
        main(("init", name))


def test__rota_can_be_created(
    tmp_dir: pathlib.Path,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = tmp_dir / f"rota__{rota_name}.db"

    rc = main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()


def test__rota_can_be_deleted(
    tmp_dir: pathlib.Path,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = tmp_dir / f"rota__{rota_name}.db"

    rc = main(("init", rota_name))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("delete", rota_name))
    assert rc == 0
    assert not expected_db_path.exists()


def test__rota_cannot_be_deleted__because_it_does_not_exist(
    tmp_dir: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = tmp_dir / f"rota__{rota_name}.db"
    assert not expected_db_path.exists()

    rc = main(("delete", rota_name))
    captured = capsys.readouterr()
    assert not expected_db_path.exists()
    assert rc == 1
    assert captured.out == ""
    assert captured.err.startswith("error: rota not found at ")


def test__rota_can_be_created__with_no_members(
    tmp_dir: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = tmp_dir / f"rota__{rota_name}.db"

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
        ("foo", "foo: 1900-01-01 00:00:00\n"),
        ("    foo      ", "foo: 1900-01-01 00:00:00\n"),
        ("foo,bar", "bar: 1900-01-01 00:00:00\nfoo: 1900-01-01 00:00:00\n"),
        ("    foo ,     bar    ", "bar: 1900-01-01 00:00:00\nfoo: 1900-01-01 00:00:00\n"),
        ("Foo Bar,Baz Qux,Ahoy!", "Ahoy!: 1900-01-01 00:00:00\nBaz Qux: 1900-01-01 00:00:00\nFoo Bar: 1900-01-01 00:00:00\n"),
    ],
)
def test__rota_can_be_created__with_members(
    tmp_dir: pathlib.Path,
    capsys: pytest.CaptureFixture,
    members_csv: str,
    expected_stdout: str,
):
    rota_name = str(uuid.uuid4())
    expected_db_path = tmp_dir / f"rota__{rota_name}.db"

    rc = main(("init", rota_name, "--members", members_csv))
    assert rc == 0
    assert expected_db_path.exists()

    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == expected_stdout
    assert captured.err == ""


def test__rota_can_be_run__with_existing_member(
    tmp_dir: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: 1900-01-01 00:00:00\nfoo: 1900-01-01 00:00:00\n"
    assert captured.err == ""

    foo_at = '2020-01-01 10:00:00'
    main(("run", rota_name, "--member", "foo", "--at", foo_at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar: 1900-01-01 00:00:00\nfoo: {foo_at}\n"
    assert captured.err == ""

    bar_at = '2020-01-01 11:00:00'
    main(("run", rota_name, "--member", "bar", "--at", bar_at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"foo: {foo_at}\nbar: {bar_at}\n"
    assert captured.err == ""


def test__rota_can_be_run__with_new_member(
    tmp_dir: pathlib.Path,
    capsys: pytest.CaptureFixture,
):
    rota_name = str(uuid.uuid4())

    main(("init", rota_name, "--members", "foo,bar"))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "bar: 1900-01-01 00:00:00\nfoo: 1900-01-01 00:00:00\n"
    assert captured.err == ""

    at = '2020-01-01 12:00:00'
    main(("run", rota_name, "--member", "baz", "--at", at))
    rc = main(("show", rota_name))
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == f"bar: 1900-01-01 00:00:00\nfoo: 1900-01-01 00:00:00\nbaz: {at}\n"
    assert captured.err == ""
