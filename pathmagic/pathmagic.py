from __future__ import annotations

import os
from typing import Any
from pathlib import Path

from send2trash import send2trash

from subtypes import Enum

from .helper import PathLike
from .settings import Settings


class PathMagic(os.PathLike):
    """Abstract Base Class from which 'File' and 'Dir' objects derive."""

    class Enums:
        class IfExists(Enum):
            FAIL = ALLOW = TRASH = Enum.Auto()

    __subclasshook__ = object.__subclasshook__

    Settings = Settings

    settings: Settings
    _path: Path

    def __init__(self, *args: Any, **kwargs: Any):
        raise NotImplementedError(f"Cannot instanciate object of abstract type {type(self).__name__}. Please instanciate one of its subclasses.")

    def __str__(self) -> str:
        return str(self.path)

    def __fspath__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: Any) -> bool:
        return self.path == Path(other).absolute()

    def __ne__(self, other: Any) -> bool:
        return not (self == other)

    def __lt__(self, other: Any) -> bool:
        return str(self).startswith(str(Path(other).absolute())) and not self == other

    def __le__(self, other: Any) -> bool:
        return str(self).startswith(str(Path(other).absolute()))

    def __gt__(self, other: Any) -> bool:
        return str(Path(other).absolute()).startswith(str(self)) and not self == other

    def __ge__(self, other: Any) -> bool:
        return str(Path(other).absolute()).startswith(str(self))

    @property
    def path(self) -> Path:
        return self._path

    @property
    def stat(self) -> os.stat_result:
        return os.stat(str(self))

    def trash(self) -> PathMagic:
        """Move this object's mapped path to your OS' implementation of a recycling bin. The object will persist and may still be used."""
        send2trash(str(self))
        return self

    def delete(self) -> PathMagic:
        raise NotImplementedError

    @classmethod
    def from_pathlike(cls, pathlike: PathLike, settings: Settings = None) -> PathMagic:
        return pathlike if isinstance(pathlike, cls) else cls(path=pathlike, settings=settings)

    def _validate(self, path: Path) -> None:
        if self == path:
            raise FileExistsError(f"PathMagic '{path}' is already this {type(self).__name__}'s path. Cannot copy or move a {type(self).__name__} to its own path.")
        else:
            if path.exists():
                if self.settings.if_exists is self.Enums.IfExists.ALLOW:
                    pass
                elif self.settings.if_exists is self.Enums.IfExists.TRASH:
                    send2trash(str(path))
                elif self.settings.if_exists is self.Enums.IfExists.FAIL:
                    raise FileExistsError(f"PathMagic '{path}' already exists and current setting is '{self.settings.if_exists}'. To change this behaviour change the '{type(self).__name__}.settings.if_exists' attribute.")
                else:
                    raise NotImplementedError

    def _prepare_dir_if_not_exists(self, path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)

    def _prepare_file_if_not_exists(self, path: Path) -> None:
        self._prepare_dir_if_not_exists(path.parent)

        try:
            path.touch(exist_ok=True)
        except PermissionError as ex:
            if not Path(path).is_file():
                raise ex

    def _parse_filename_args(self, name_or_stem: str, *, extension: str = None) -> Path:
        return (
            self.path.with_name(name_or_stem)
            if extension is None else
            self.path.with_stem(name_or_stem).with_suffix(extension)
        )
