# MahkrabDTN

Delay-tolerant encrypted messaging with a relay server and a small CLI.

## Install

```sh
pipx install mahkrabdtn
```

For development:

```sh
pip install -e ".[dev]"
```

## CLI

The main command is `mkdtn`.

```sh
mkdtn identity
mkdtn register
mkdtn send <recipient-node-id> "hello"
mkdtn poll --ack
```

Run a local relay when you do not want to use the default relay:

```sh
mkdtn serve
mkdtn identity
mkdtn register --relay http://127.0.0.1:8000
mkdtn send <recipient-node-id> "hello"
mkdtn poll --ack
mkdtn poll --watch --ack
mkdtn health
```

The CLI uses `MAHKRABDTN_RELAY` and `MAHKRABDTN_IDENTITY` when set. By default it
uses `https://relay.mahkrab.com` and `~/.mahkrabdtn/node.id`.

Use `mkdtn poll --watch --ack` to keep a terminal open for incoming messages.

## Build

```sh
python -m build
twine check dist/*
twine upload dist/*
```
