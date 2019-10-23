from __future__ import annotations

import os
from typing import Any, Union, Type, TYPE_CHECKING
import pathlib

from maybe import Maybe
from subtypes import AutoEnum

if TYPE_CHECKING:
    from .file import File
    from .dir import Dir

PathLike = Union[str, os.PathLike]


def is_running_in_ipython() -> bool:
    try:
        assert __IPYTHON__  # type: ignore
        return True
    except (NameError, AttributeError):
        return False


class IfExists(AutoEnum):
    FAIL, ALLOW, MAKE_COPY  # noqa


class Settings:
    """A Settings class for Path objects. Holds the constructors that Path objects will use when they need to instanciate relatives, as well as controlling other aspects of behaviour."""

    def __init__(self, if_exists: str = None, lazy_instanciation: bool = None, file_class: Type[File] = None, dir_class: Type[Dir] = None) -> None:
        from .file import File
        from .dir import Dir

        self.if_exists = Maybe(if_exists).else_(Path.DEFAULT_IF_EXISTS)
        self.lazy = Maybe(lazy_instanciation).else_(False if is_running_in_ipython() else True)
        self.file_class, self.dir_class = Maybe(file_class).else_(File), Maybe(dir_class).else_(Dir)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"


class Path(os.PathLike):
    """Abstract Base Class from which 'File' and 'Dir' objects derive."""

    __subclasshook__ = object.__subclasshook__  # type:ignore

    IfExists = IfExists
    DEFAULT_IF_EXISTS = IfExists.FAIL

    if_exists: bool
    _path: pathlib.Path

    def __init__(self, *args: Any, **kwargs: Any):
        self.settings = Settings()
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
        return os.stat(self)

    def resolve(self) -> Dir:
        return type(self)(self.path.resolve(), settings=self.settings)

    def _validate(self, path: PathLike) -> None:
        path = os.path.abspath(path)
        if self == path:
            raise FileExistsError(f"Path '{path}' is already this {type(self).__name__}'s path. Cannot copy or move a {type(self).__name__} to its own path.")
        else:
            if os.path.exists(path):
                if self.settings.if_exists == IfExists.ALLOW:
                    pass
                elif self.settings.if_exists == IfExists.MAKE_COPY:
                    raise NotImplementedError
                elif self.settings.if_exists == IfExists.FAIL:
                    raise PermissionError(f"Path '{path}' already exists and current setting is '{self.settings.if_exists}'. To change this behaviour set the '{type(self).__name__}.settings.if_exists' attribute to one of: {Path.IfExists}.")
                else:
                    IfExists.raise_if_not_a_member(self.settings.if_exists)

    def _get_settings(self) -> Settings:
        return Settings()

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

    @classmethod
    def from_pathlike(cls, pathlike: PathLike, settings: Settings = None) -> Path:
        return pathlike if isinstance(pathlike, cls) else cls(path=pathlike, settings=settings)
