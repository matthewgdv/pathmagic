from typing import Union
import os
from pathlib import Path


def is_running_in_ipython() -> bool:
    try:
        assert __IPYTHON__  # type: ignore
        return True
    except (NameError, AttributeError):
        return False


def is_special(attribute: str) -> bool:
    return attribute.startswith("_") and attribute.endswith("_")


def clean_filename(name: str) -> str:
    stem, _, ext = name.partition(".")
    return stem if not ext else f"{stem}.{ext.lower()}"


PathLike = Union[str, os.PathLike, Path]
