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


PathLike = Union[str, os.PathLike, Path]
