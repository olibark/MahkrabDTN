# MahkrabDTN

Delay-tolerant encrypted messaging with a relay server and an installable CLI.

## Install

```sh
pipx install mahkrabdtn
```

For local development:

```sh
pip install -e ".[dev]"
```

## CLI

The package exposes the `mkdtn` command.

```sh
mkdtn serve
mkdtn identity
mkdtn register --relay http://127.0.0.1:8000
mkdtn send <recipient-node-id> "hello"
mkdtn poll --ack
mkdtn health
```

The CLI uses `MAHKRABDTN_RELAY` and `MAHKRABDTN_IDENTITY` when set. By default it
uses `http://127.0.0.1:8000` and `~/.mahkrabdtn/node.id`.

## Build

```sh
python -m build
twine check dist/*
twine upload dist/*
```
