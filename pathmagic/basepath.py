from __future__ import annotations

import contextlib
import os
from abc import ABC, abstractmethod
from typing import Any, Iterator, Union, Type, TYPE_CHECKING
import pathlib

from lazy_property import LazyProperty

from maybe import Maybe
from subtypes import Enum

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


class IfExists(Enum):
    FAIL, ALLOW, MAKE_COPY = "fail", "allow", "make_copy"


class Settings:
    def __init__(self, if_exists: str = None, lazy_instanciation: bool = None, fileclass: Type[File] = None, dirclass: Type[Dir] = None) -> None:
        from .file import File
        from .dir import Dir

        self.if_exists = Maybe(if_exists).else_(BasePath.DEFAULT_IF_EXISTS)
        self.lazy = Maybe(lazy_instanciation).else_(False if is_running_in_ipython() else True)
        self.fileclass, self.dirclass = Maybe(fileclass).else_(File), Maybe(dirclass).else_(Dir)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"


class BasePath(ABC):
    """Abstract Base Class from which 'File' and 'Dir' objects derive."""

    IfExists = IfExists
    DEFAULT_IF_EXISTS = IfExists.FAIL

    if_exists: bool
    _path: pathlib.Path

    @abstractmethod
    def __init__(self, *args: Any, **kwargs: Any):
        pass

    def __str__(self) -> str:
        return str(self.path)

    def __fspath__(self) -> str:
        return str(self)

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: Any) -> bool:
        return os.fspath(self) == os.fspath(other)

    def __ne__(self, other: Any) -> bool:
        return os.fspath(self) != os.fspath(other)

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

    @LazyProperty
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
                if self.settings.if_exists == BasePath.IfExists.ALLOW:
                    pass
                elif self.settings.if_exists == BasePath.IfExists.MAKE_COPY:
                    raise NotImplementedError
                elif self.settings.if_exists == BasePath.IfExists.FAIL:
                    raise PermissionError(f"Path '{path}' already exists and current setting is '{self.settings.if_exists}'. To change the behaviour set the '{type(self).__name__}.settings.if_exists' attribute to one of: {BasePath.IfExists}.")

    @classmethod
    def from_pathlike(cls, pathlike: PathLike, settings: Settings = None) -> BasePath:
        return pathlike if isinstance(pathlike, cls) else cls(path=pathlike, settings=settings)

    @staticmethod
    def chdir(path: PathLike) -> None:
        """
        Convenience staticmethod available to all Path objects for making calls to os.chdir without needing to import the os module.
        Will change the current location of the Python interpreter to the specified path. If called from an object, this method will not affect that object in any way.
        """
        os.chdir(path)

    @staticmethod
    @contextlib.contextmanager
    def cwd_context(path: PathLike) -> Iterator[None]:
        current = os.getcwd()
        try:
            os.chdir(path)
            yield None
        finally:
            os.chdir(current)

    def _get_settings(self) -> Settings:
        return Settings()

    @staticmethod
    def _prepare_dir_if_not_exists(path: PathLike) -> None:
        pathlib.Path(os.path.abspath(path)).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _prepare_file_if_not_exists(path: PathLike) -> None:
        path = os.path.abspath(path)
        BasePath._prepare_dir_if_not_exists(os.path.dirname(path))
        pathlib.Path(path).touch()
