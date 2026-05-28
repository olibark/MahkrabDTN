from importlib.metadata import PackageNotFoundError, version


def get_version() -> str:
    try:
        return version("mahkrabdtn")
    except PackageNotFoundError:
        return "0.0.0"
