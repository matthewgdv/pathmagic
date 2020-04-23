from __future__ import annotations

import os
from typing import Any, Union, Type, TYPE_CHECKING
import pathlib

from send2trash import send2trash

from maybe import Maybe
from subtypes import Enum

if TYPE_CHECKING:
    from .file import File
    from .dir import Dir

PathLike = Union[str, os.PathLike, pathlib.Path]


# TODO: Implement IfExists.COPY behaviour


def is_running_in_ipython() -> bool:
    try:
        assert __IPYTHON__  # type: ignore
        return True
    except (NameError, AttributeError):
        return False


class Settings:
    """A Settings class for Path objects. Holds the constructors that Path objects will use when they need to instanciate relatives, as well as controlling other aspects of behaviour."""

    def __init__(self, if_exists: Path.IfExists = None, lazy_instanciation: bool = None, file_class: Type[File] = None, dir_class: Type[Dir] = None) -> None:
        self.if_exists, self.lazy, self.file_class, self.dir_class = if_exists, lazy_instanciation, file_class, dir_class
        self._apply_default_settings()

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    def _apply_default_settings(self) -> None:
        if self.if_exists is None:
            self.if_exists = Path.IfExists.FAIL

        if self.lazy is None:
            self.lazy = not is_running_in_ipython()

        if self.file_class is None:
            from .file import File
            self.file_class = File

        if self.dir_class is None:
            from .dir import Dir
            self.dir_class = Dir


class Path(os.PathLike):
    """Abstract Base Class from which 'File' and 'Dir' objects derive."""

    class IfExists(Enum):
        FAIL, ALLOW, MAKE_COPY = "fail", "allow", "make_copy"

    __subclasshook__ = object.__subclasshook__  # type:ignore

    Settings = Settings

    settings: Settings
    _path: pathlib.Path

    def __init__(self, *args: Any, **kwargs: Any):
        raise TypeError(f"Cannot instanciate object of abstract type {type(self).__name__}. Please instanciate one of its subclasses.")

    def __str__(self) -> str:
        return str(self.path)

    def __fspath__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: Any) -> bool:
        return bool(os.fspath(self) == os.fspath(other))

    def __ne__(self, other: Any) -> bool:
        return bool(os.fspath(self) != os.fspath(other))

    def __lt__(self, other: Any) -> bool:
        return os.fspath(other) in os.fspath(self)

    def __le__(self, other: Any) -> bool:
        return os.fspath(self) == os.fspath(other) or os.fspath(other) in os.fspath(self)

    def __gt__(self, other: Any) -> bool:
        return os.fspath(self) in os.fspath(other)

    def __ge__(self, other: Any) -> bool:
        return os.fspath(self) == os.fspath(other) or os.fspath(self) in os.fspath(other)

    @property
    def path(self) -> pathlib.Path:
        return self._path

    @property
    def stat(self) -> os.stat_result:
        return os.stat(str(self))

    def resolve(self) -> Path:
        return type(self)(self.path.resolve(), settings=self.settings)

    def trash(self) -> Path:
        """Move this object's mapped path to your OS' implementation of a recycling bin. The object will persist and may still be used."""
        send2trash(str(self))
        return self

    @classmethod
    def from_pathlike(cls, pathlike: PathLike, settings: Settings = None) -> Path:
        return pathlike if isinstance(pathlike, cls) else cls(path=pathlike, settings=settings)

    def _validate(self, path: PathLike) -> None:
        if self == (path := os.path.abspath(path)):
            raise FileExistsError(f"Path '{path}' is already this {type(self).__name__}'s path. Cannot copy or move a {type(self).__name__} to its own path.")
        else:
            if os.path.exists(path):
                if self.settings.if_exists == self.IfExists.ALLOW:
                    pass
                elif self.settings.if_exists == self.IfExists.MAKE_COPY:
                    raise NotImplementedError
                elif self.settings.if_exists == self.IfExists.FAIL:
                    raise PermissionError(f"Path '{path}' already exists and current setting is '{self.settings.if_exists}'. To change this behaviour change the '{type(self).__name__}.settings.if_exists' attribute.")
                else:
                    self.IfExists(self.settings.if_exists)

    @staticmethod
    def _prepare_dir_if_not_exists(path: PathLike) -> None:
        pathlib.Path(os.path.abspath(path)).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _prepare_file_if_not_exists(path: PathLike) -> None:
        path = os.path.abspath(path)
        Path._prepare_dir_if_not_exists(os.path.dirname(path))

        try:
            with open(path, "a"):
                pass
        except PermissionError as ex:
            if not pathlib.Path(path).is_file():
                raise ex

    @staticmethod
    def _clean_extension(extension: str) -> str:
        return f".{extension.strip('.')}" if extension is not None else ''
