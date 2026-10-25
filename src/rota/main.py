import argparse
import dataclasses
import datetime
import functools
import logging.config
import os
import pathlib
import re
import sqlite3
import sys
import textwrap
import tomllib
from collections.abc import Sequence
from typing import Protocol, Self, overload

HERE = pathlib.Path(__file__).parent

# https://specifications.freedesktop.org/basedir/latest/
_get = os.environ.get
HOME = pathlib.Path(_get("HOME", _get("USERPROFILE", "."))).resolve()

DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_data_home() -> pathlib.Path:
    # Setting this as a module constant broke the tests because this is set
    # _before_ the test runner mocked the environment variable, so to be
    # safe we just read the env vars directly each time we use this
    return pathlib.Path(_get("XDG_DATA_HOME", HOME / ".local/share")) / "rota"


def get_state_home() -> pathlib.Path:
    return pathlib.Path(_get("XDG_STATE_HOME", HOME / ".local/state")) / "rota"


class FromTupleable(Protocol):
    @classmethod
    def from_tuple(cls, data: tuple) -> Self: ...


def configure_logging() -> None:
    with open(HERE / "logger.toml", "rb") as f:
        config = tomllib.load(f)

    # ensure log destinations exist
    log_directory = get_state_home()
    for handler in config.get("handlers", {}).values():
        if "filename" in handler:
            filename = log_directory / handler["filename"]
            filename.parent.mkdir(parents=True, exist_ok=True)
            handler["filename"] = filename

    logging.config.dictConfig(config)


def configure_local_directories() -> None:
    get_data_home().mkdir(parents=True, exist_ok=True)


def debug(text: str) -> None:
    for line in text.splitlines():
        logging.debug(line)


@functools.cache
def conn(database_name: str) -> sqlite3.Connection:
    return sqlite3.connect(database_name)


@overload
def run_script(
    client: sqlite3.Connection,
    script_name: str,
    *,
    parameters: dict[str, bool | int | str] | None = None,
    model: None = None,
) -> None: ...
@overload
def run_script[T: FromTupleable](
    client: sqlite3.Connection,
    script_name: str,
    *,
    parameters: dict[str, bool | int | str] | None = None,
    model: type[T],
) -> list[T]: ...
def run_script(client, script_name, *, parameters = None, model = None):
    sql_file = HERE / "scripts" / script_name
    assert sql_file.exists(), f"'{sql_file}' does not exist"

    params = parameters or dict()
    cursor = client.cursor()
    try:
        # TODO: This is brittle! Find a better way to run parameterised scripts
        statements = [
            query.strip()
            for query in sql_file.read_text(encoding="utf-8").split(";")
            if query.strip() != ""
        ]
        for statement in statements:
            debug(f"Executing the following SQL with params {params}")
            debug(textwrap.indent(statement, "    "))
            cursor.execute(statement, params)

        client.commit()

        if model:
            return [
                model.from_tuple(result)
                for result in cursor.fetchall()
            ]
        else:
            return None
    finally:
        cursor.close()


@dataclasses.dataclass
class RotaEntry:
    member_name: str
    last_actioned: datetime.datetime | None

    @classmethod
    def from_tuple(cls, data: tuple) -> Self:
        return cls(
            member_name=data[0],
            last_actioned=data[1],
        )

    def __str__(self) -> str:
        return f"{self.member_name}: {self.last_actioned or ''}"


class Rota:
    """
    A rota, which is a queue of members.
    """

    def __init__(self, name: str) -> None:
        self.name = name

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, name: str) -> None:
        if re.match(r"^[A-Za-z0-9-]+$", name):
            self._name = name
        else:
            raise ValueError(
                "Rota name must be alphanumeric and contain only hyphens."
            )

    @property
    def store_path(self) -> pathlib.Path:
        return get_data_home() / f"rota__{self.name}.db"

    @property
    def store(self) -> sqlite3.Connection:
        debug(f"using database at: {self.store_path.as_posix()}")
        return conn(self.store_path)


def initialise_database(
    client: sqlite3.Connection,
    member_names: list[str],
) -> None:
    run_script(client, "create-rota-objects.sql")
    for member_name in member_names:
        run_script(
            client,
            "add-rota-member.sql",
            parameters={"member_name": member_name},
        )


def get_members(client: sqlite3.Connection) -> list[RotaEntry]:
    return run_script(client, "get-all-members.sql", model=RotaEntry)


def run_rota_for_member(
    client: sqlite3.Connection,
    member_name: str,
    actioned_at: datetime.datetime,
) -> None:
    run_script(
        client,
        "run-rota-for-member.sql",
        parameters={
            "member_name": member_name,
            "actioned_at": actioned_at.strftime(DATETIME_FORMAT),
        },
    )


def _list() -> int:
    data_home = get_data_home()
    debug(f"looking for existing rotas in '{data_home.as_posix()}'")
    rota_paths = sorted(data_home.glob("rota__*.db"))
    debug(f"found existing rotas:\n  {'\n  '.join((p.as_posix() for p in rota_paths))}")
    for rota_path in rota_paths:
        rota_name = rota_path.name[6:-3]
        print(f"{rota_name}  ({rota_path})")

    return 0


def _init(args: argparse.Namespace) -> int:
    rota = Rota(name=args.rota_name)
    if rota.store_path.exists():
        print(f"error: rota '{args.rota_name}' already exists", file=sys.stderr)
        return 1

    members = [
        member.strip()
        for member in args.members.split(",")
        if member.strip()
    ]
    initialise_database(rota.store, members)

    return 0


def _delete(args: argparse.Namespace) -> int:
    rota = Rota(name=args.rota_name)
    store_path = rota.store_path
    if store_path.exists():
        debug(f"deleting rota at '{store_path}'")
        rota.store.close()
        store_path.unlink()
        return 0
    else:
        print(f"error: rota not found at '{store_path}'", file=sys.stderr)
        return 1


def _show(args: argparse.Namespace) -> int:
    rota = Rota(name=args.rota_name)
    for member in get_members(rota.store):
        print(member)

    return 0


def _run(args: argparse.Namespace) -> int:
    rota = Rota(name=args.rota_name)
    run_rota_for_member(rota.store, args.member, args.at)

    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """
    Parse the arguments and run the command.
    """

    configure_logging()
    configure_local_directories()

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list")

    parser__init = subparsers.add_parser("init")
    parser__init.add_argument("rota_name")
    parser__init.add_argument(
        "--members",
        default="",
        help="comma-separated list of members to initiate the rota with",
    )

    parser__delete = subparsers.add_parser("delete")
    parser__delete.add_argument("rota_name")

    parser__show = subparsers.add_parser("show")
    parser__show.add_argument("rota_name")

    parser__run = subparsers.add_parser("run")
    parser__run.add_argument("rota_name")
    parser__run.add_argument("--member", required=True)
    parser__run.add_argument(
        "--at",
        type=lambda at: datetime.datetime.strptime(at, DATETIME_FORMAT),
        default=datetime.datetime.now(),
    )

    args = parser.parse_args(argv)
    if args.command == "list":
        return _list()
    if args.command == "init":
        return _init(args)
    if args.command == "delete":
        return _delete(args)
    if args.command == "show":
        return _show(args)
    if args.command == "run":
        return _run(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())  # pragma: no cover
