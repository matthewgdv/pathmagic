from __future__ import annotations

import os
from abc import ABC
from typing import Any, Callable, Dict, List, Union, TYPE_CHECKING

from subtypes import Str

from .basepath import BasePath

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


class Accessor(ABC):
    """Utility class for managing item access to the underlying _files and _dirs attributes held by Dir objects."""

    collection_name: str

    def __init__(self, parent: Dir) -> None:
        self.parent = parent
        self._access = self._sync = None  # type: Callable

    def __call__(self, full_path: bool = False) -> List[str]:
        self._sync()
        return [filename if not full_path else os.path.join(self.parent.path, filename) for filename in getattr(self.parent, self.collection_name)]

    def __len__(self) -> int:
        return len(getattr(self.parent, self.collection_name))

    def __iter__(self) -> Any:
        self.__iter = (self[name] for name in self())
        return self

    def __next__(self) -> Union[File, Dir]:
        return next(self.__iter)

    def __contains__(self, other: os.PathLike) -> bool:
        with BasePath.cwd_context(self.parent):
            return os.path.realpath(other) in self(full_path=True)

    def __getitem__(self, key: str) -> Union[File, Dir]:
        return self._access(key)

    def __delitem__(self, key: str) -> None:
        self[key].delete()


class FileAccessor(Accessor):
    collection_name = "_files"

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._sync, self._access = self.parent._synchronize_files, self.parent._access_files

    def __getitem__(self, key: str) -> File:
        return self._access(key)

    def __setitem__(self, key: str, val: File) -> None:
        super().__setitem__(key, val)


class DirAccessor(Accessor):
    collection_name = "_dirs"

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._sync, self._access = self.parent._synchronize_dirs, self.parent._access_dirs

    def __getitem__(self, key: str) -> Dir:
        return self._access(key)

    def __setitem__(self, key: str, val: Dir) -> None:
        super().__setitem__(key, val)


class DotAccessor:
    _strip_extension: bool = None

    class Name:
        def __init__(self, name: str) -> None:
            self.name = name

    def __init__(self, accessor: Accessor) -> None:
        self._accessor = accessor
        self._mappings: Dict[str, List[str]] = {}
        self._pending: List[str] = []

    def __getattribute__(self, name: str) -> Any:
        val = object.__getattribute__(self, name)
        if isinstance(val, DotAccessor.Name):
            return object.__getattribute__(self, "_accessor")[val.name]
        else:
            return val

    def __getattr__(self, name: str) -> Any:
        if not name.startswith("__"):
            names = self._mappings.get(name)
            if names is None:
                self._accessor._sync()
                if self._accessor.parent.lazy:
                    self.__acquire_references_as_attributes()
                names = self._mappings.get(name)

            if names is None:
                return self._accessor[name]
            else:
                if len(names) > 1:
                    raise AmbiguityError(f"""'{name}' does not resolve uniquely. Could refer to any of: {", ".join([f"'{fullname}'" for fullname in names])}.""")
                else:
                    return self._accessor[names[0]]

    def _acquire(self, names: List[str]) -> None:
        self._pending = names
        if not self._accessor.parent.lazy:
            self.__acquire_references_as_attributes()

    def __acquire_references_as_attributes(self) -> None:
        self._mappings.clear()
        for name in self._pending:
            clean = str((Str(name).before_first(r"\.") if type(self)._strip_extension else Str(name)).identifier())
            self._mappings.setdefault(clean, []).append(name)

        self._pending.clear()

        for clean, names in self._mappings.items():
            if len(names) == 1:
                setattr(self, clean, DotAccessor.Name(name=names[0]))


class FileDotAccessor(DotAccessor):
    _strip_extension = True

    def __getattr__(self, attr: str) -> File:
        return super().__getattr__(attr)


class DirDotAccessor(DotAccessor):
    _strip_extension = False

    def __getattr__(self, attr: str) -> Dir:
        return super().__getattr__(attr)


class AmbiguityError(RuntimeError):
    pass
