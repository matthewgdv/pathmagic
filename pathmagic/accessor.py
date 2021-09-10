from __future__ import annotations

import os
from abc import ABC
from typing import Any, TYPE_CHECKING
from pathlib import Path

from subtypes import Str

from .helper import is_running_in_ipython, is_special, clean_filename

if TYPE_CHECKING:
    from .pathmagic import PathMagic
    from .dir import Dir
    from .file import File


class Accessor(ABC):
    """Utility class for managing item access to the underlying files and dirs held by Dir objects."""

    def __init__(self, parent: Dir) -> None:
        self._parent_ = parent
        self._items_: dict[str, PathMagic] = {}

    def __repr__(self) -> str:
        return f"{type(self).__name__}(num_items={len(self)}, items={list(self._items_)})"

    def __call__(self) -> list[str]:
        self._synchronize_(force_attributes=False)
        return list(self._items_)

    def __len__(self) -> int:
        self._synchronize_(force_attributes=False)
        return len(self._items_)

    def __iter__(self) -> Any:
        return (self[name] for name in self())

    def __contains__(self, other: os.PathLike) -> bool:
        if not (path := Path(other)).is_absolute():
            path = self._parent_.path.joinpath(path)

        return self._parent_ == path.resolve().parent and path.exists()

    def __getitem__(self, key: str) -> PathMagic:
        raise NotImplementedError

    def __setitem__(self, key: str, val: PathMagic) -> None:
        self._items_[key] = val

    def __delitem__(self, key: str) -> None:
        self[key].delete()

    def __getattribute__(self, name: str) -> PathMagic:
        if isinstance(val := object.__getattribute__(self, name), Name):
            return val.access()

        return val

    def __getattr__(self, name: str) -> Any:
        if is_special(name):
            raise AttributeError(name)

        self._synchronize_(force_attributes=True)

        if name in self.__dict__:
            return getattr(self, name)
        else:
            raise AttributeError(name)

    def _synchronize_(self, force_attributes: bool) -> None:
        try:
            real_paths = self._get_path_names_()
            new_paths = {name: self._items_.get(name) for name in real_paths}
            self._items_.clear()
            self._items_.update(new_paths)

            if force_attributes or is_running_in_ipython():
                self._acquire_attributes_(names=real_paths)
        except PermissionError:
            pass

    def _get_path_names_(self) -> list[str]:
        raise NotImplementedError

    def _acquire_attributes_(self, names: list[str]) -> None:
        name_mappings: dict[str, list[str]] = {}

        for name in names:
            if not is_special(name):
                stem, _ = os.path.splitext(name)
                clean = Str(stem).case.identifier()
                name_mappings.setdefault(clean, []).append(name)

        for stale_key in ({name for name in self.__dict__ if not is_special(name)} - set(name_mappings)):
            delattr(self, stale_key)

        for new_key in (set(name_mappings) - set(self.__dict__)):
            setattr(self, new_key, Name(clean_name=new_key, raw_names=name_mappings[new_key], accessor=self))


class FileAccessor(Accessor):
    """Utility class for managing item access to the underlying files held by Dir objects."""

    def __getitem__(self, key: str) -> File:
        try:
            file = self._items_[key]
        except KeyError:
            self._synchronize_(force_attributes=False)
            try:
                file = self._items_[key]
            except KeyError:
                raise FileNotFoundError(f"File '{key}' not found in '{self}'")

        return file if file is not None else self._parent_.new_file(key)

    def _get_path_names_(self) -> list[str]:
        return [clean_filename(item.name) for item in os.scandir(self._parent_) if item.is_file()]


class DirAccessor(Accessor):
    """Utility class for managing item access to the underlying dirs held by Dir objects."""

    def __getitem__(self, key: str) -> Dir:
        try:
            dir = self._items_[key]
        except KeyError:
            self._synchronize_(force_attributes=False)
            try:
                dir = self._items_[key]
            except KeyError:
                raise FileNotFoundError(f"Dir '{key}' not found in '{self}'")

        return dir if dir is not None else self._parent_.new_dir(key)

    def _get_path_names_(self) -> list[str]:
        return [item.name for item in os.scandir(self._parent_) if item.is_dir()]


class AmbiguityError(RuntimeError):
    pass


class Name:
    def __init__(self, clean_name, raw_names: list[str], accessor: Accessor) -> None:
        self.clean_name, self.raw_names, self.accessor = clean_name, raw_names, accessor

    def __repr__(self) -> str:
        return f"{type(self).__name__}('{self.clean_name}')"

    def access(self):
        if len(self.raw_names) == 1:
            name, = self.raw_names
            return self.accessor[name]
        else:
            raise AmbiguityError(f"""'{self.clean_name}' does not resolve uniquely. Could refer to any of: {", ".join([f"'{name}'" for name in self.raw_names])}.""")
