<span align="center">

[![Python](https://img.shields.io/badge/Python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![tests](https://github.com/billwallis/rota/actions/workflows/tests.yaml/badge.svg)](https://github.com/billwallis/rota/actions/workflows/tests.yaml)
[![coverage](https://raw.githubusercontent.com/billwallis/rota/refs/heads/main/coverage.svg)](https://smarie.github.io/python-genbadge/)

[![pre-commit.ci status](https://results.pre-commit.ci/badge/github/billwallis/rota/main.svg)](https://results.pre-commit.ci/latest/github/billwallis/rota/main)
[![GitHub last commit](https://img.shields.io/github/last-commit/billwallis/rota)](https://shields.io/badges/git-hub-last-commit)

</span>

---

# Rota

Manage people rotas.

## Summary

"Who did <the thing> last time? Who's next?"

Heard this before? Yeah, me too 😋

## Usage

```shell
# create a "test" rota with members "foo", "bar", and "baz"
rota init 'test' --members 'foo,bar,baz'

# list the available rotas
rota list

# show the current state of the "test" rota
rota show 'test'

# run the "test" rota interactively (select from a navigable menu)
rota run 'test'

# run the "test" rota for a given member
rota run 'test' --member 'foo'

# run the "test" rota for a new member, then show the updated rota
rota run 'test' --member 'someone new' --show

# add a new member to the rota
rota edit 'test' --add 'new member'

# remove an existing member from the rota
rota edit 'test' --remove 'old member'

# delete the "test" rota
rota delete 'test'
```

Rota data is stored in `$XDG_DATA_HOME/rota`, where `XDG_DATA_HOME` defaults to `~/.local/share`.

Rota logs are stored in `$XDG_STATE_HOME/rota`, where `XDG_STATE_HOME` defaults to `~/.local/state`.

## Contributing

Install the dependencies:

```shell
pip install --editable . --group dev --group test
pre-commit install --install-hooks
```
