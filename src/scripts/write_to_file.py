import os
from collections.abc import Iterable
from pathlib import Path


def write(
    data: Iterable | str,
    fname: str,
    mode: str = "w",
    encoding: str = "utf-8",
    separator: str = "\n",
):
    """
    Safely write data to a file.
    - Handles str, Iterable, and other objects correctly.
    - Ensures the folder exists before writing.
    """

    fpath = Path(fname)
    parent_dir = fpath.parent
    if not parent_dir.exists():
        parent_dir.mkdir(parents=True, exist_ok=True)

    with open(fname, mode, encoding=encoding) as f:
        if isinstance(data, str):
            f.write(data)
        elif isinstance(data, Iterable):
            f.write(separator.join(map(str, data)))
        else:
            f.write(str(data))

    try:
        os.chmod(fname, 0o666)
    except (OSError, PermissionError):
        pass
