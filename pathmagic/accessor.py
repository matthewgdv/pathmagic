from __future__ import annotations

import os
from abc import ABC
from typing import Any, Callable, Dict, List, Union, TYPE_CHECKING, Optional

from subtypes import Str

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


class Accessor(ABC):
    """Utility class for managing item access to the underlying files and dirs held by Dir objects."""

    def __init__(self, parent: Dir) -> None:
        self.parent = parent
        self._access = self._sync = None  # type: Optional[Callable]
        self._collection: Optional[dict] = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(num_items={len(self)}, items={list(self._collection)})"

    def __call__(self, full_path: bool = False) -> list[str]:
        self._sync()
        return [filename if not full_path else os.path.join(self.parent, filename) for filename in self._collection]

    def __len__(self) -> int:
        self._sync()
        return len(self._collection)

    def __iter__(self) -> Any:
        return (self[name] for name in self())

    def __contains__(self, other: os.PathLike) -> bool:
        with self.parent:
            return os.path.abspath(other) in self(full_path=True)

    def __getitem__(self, key: str) -> Union[File, Dir]:
        return self._access(key)

    def __delitem__(self, key: str) -> None:
        self[key].delete()


class FileAccessor(Accessor):
    """Utility class for managing item access to the underlying files held by Dir objects."""

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._sync, self._access, self._collection = self.parent._synchronize_files, self.parent._access_files, self.parent._files

    def __getitem__(self, key: str) -> File:
        return self._access(key)


class DirAccessor(Accessor):
    """Utility class for managing item access to the underlying dirs held by Dir objects."""

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._sync, self._access, self._collection = self.parent._synchronize_dirs, self.parent._access_dirs, self.parent._dirs

    def __getitem__(self, key: str) -> Dir:
        return self._access(key)


class DotAccessor:
    """Utility class for managing item access to the underlying files and dirs held by Dir objects using attribute access."""
    _strip_extension: bool = None

    def __init__(self, accessor: Accessor) -> None:
        self._accessor = accessor
        self._mappings: dict[str, list[str]] = {}
        self._pending: list[str] = []

    def __getattribute__(self, name: str) -> Any:
        val = object.__getattribute__(self, name)
        if isinstance(val, Name):
            return object.__getattribute__(self, "_accessor")[val.name]
        else:
            return val

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__"):
            raise AttributeError(name)
        else:
            names = self._mappings.get(name)
            if names is None:
                self._accessor._sync()
                if self._accessor.parent.settings.lazy:
                    self.__acquire_references_as_attributes()
                names = self._mappings.get(name)

            if names is None:
                return self._accessor[name]
            else:
                if len(names) > 1:
                    raise AmbiguityError(f"""'{name}' does not resolve uniquely. Could refer to any of: {", ".join([f"'{fullname}'" for fullname in names])}.""")
                else:
                    return self._accessor[names[0]]

    def _acquire(self, names: list[str]) -> None:
        self._pending = names
        if not self._accessor.parent.settings.lazy:
            self.__acquire_references_as_attributes()

    def __acquire_references_as_attributes(self) -> None:
        self._mappings.clear()
        for name in self._pending:
            clean = str((Str(name).slice.before_first(r"\.") if type(self)._strip_extension else Str(name)).case.identifier())
            self._mappings.setdefault(clean, []).append(name)

        self._pending.clear()

        for clean, names in self._mappings.items():
            if len(names) == 1:
                setattr(self, clean, Name(name=names[0]))


class FileDotAccessor(DotAccessor):
    """Utility class for managing item access to the underlying files held by Dir objects using attribute access."""
    _strip_extension = True

    def __getattr__(self, attr: str) -> File:
        return super().__getattr__(attr)


class DirDotAccessor(DotAccessor):
    """Utility class for managing item access to the underlying dirs held by Dir objects using attribute access."""
    _strip_extension = False

    def __getattr__(self, attr: str) -> Dir:
        return super().__getattr__(attr)


class AmbiguityError(RuntimeError):
    pass


class Name:
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self.name}')"
