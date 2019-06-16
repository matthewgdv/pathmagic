from __future__ import annotations

import contextlib
import inspect
import os
from abc import ABC, abstractmethod
from typing import Any, Iterator, Union

PathLike = Union[str, os.PathLike]


def is_running_in_ipython() -> bool:
    try:
        assert __IPYTHON__  # type: ignore
        return True
    except (NameError, AttributeError):
        return False


class BasePath(os.PathLike, ABC):
    """Abstract Base Class from which 'File' and 'Dir' objects derive."""

    safe: bool
    _path: str

    @abstractmethod
    def __init__(self, path: PathLike, **kwargs: Any):
        pass

    def __str__(self) -> str:
        return self.path

    def __fspath__(self) -> str:
        return str(self)

    @property
    def path(self) -> str:
        return self._path

    def _validate(self, path: PathLike) -> None:
        if path == self.path:
            raise FileExistsError(f"Path '{path}' is already this {type(self).__name__}'s path. Cannot copy or move a {type(self).__name__} to its own path.")
        else:
            if os.path.exists(path) and self.safe:
                raise PermissionError(f"Path '{path}' already exists. Safemode prevents overwriting. If this is desired behaviour set the '{type(self).__name__}.safe' attribute to 'False'.")

    @classmethod
    def from_pathlike(cls, pathlike: PathLike, **kwargs: Any) -> BasePath:
        mro = inspect.getmro(type(pathlike))
        return pathlike if cls in mro else cls(path=pathlike, **kwargs)

    @staticmethod
    def chdir(path: PathLike) -> None:
        """
        Convenience staticmethod available to all Path objects for making calls to os.chdir without needing to import the os module.
        Will change the current location of the Python interpreter to the specified path. If called from an object, this method will not affect that object in any way.
        """
        os.chdir(os.fspath(path))

    @staticmethod
    @contextlib.contextmanager
    def cwd_context(path: PathLike) -> Iterator[None]:
        current = os.getcwd()
        try:
            os.chdir(path)
            yield None
        finally:
            os.chdir(current)

    @staticmethod
    def _prepare_dir_if_not_exists(path: PathLike) -> None:
        try:
            os.makedirs(path)
        except FileExistsError:
            pass

    @staticmethod
    def _prepare_file_if_not_exists(path: PathLike) -> None:
        BasePath._prepare_dir_if_not_exists(os.path.dirname(path))
        try:
            with open(path, "a"):
                pass
        except PermissionError:
            pass
