from pathlib import Path


def create(path: str) -> Path:
    """
    Create parent directory for a given file path or create the directory itself.
    """
    p = Path(path)

    if p.suffix:
        parent = p.parent
        if not parent.exists():
            parent.mkdir(exist_ok=True, parents=True)
        return parent
    else:
        if not p.exists():
            p.mkdir(exist_ok=True, parents=True)
    return p
