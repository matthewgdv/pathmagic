from __future__ import annotations

import os
from abc import ABC
from typing import Any, Callable, Dict, List, Union, Type, TYPE_CHECKING

from subtypes import Str

from .basepath import BasePath

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


# TODO: cause dotaccessors to update before accessing, to prevent them being unable to find things that are actually there

class Accessor(ABC):
    """Utility class for managing item access to the underlying _files and _dirs attributes held by Dir objects."""

    collection_name: str
    class_type: Union[Type[File], Type[Dir]]

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

    def __setitem__(self, key: str, val: Any) -> None:
        if isinstance(val, self.class_type):
            val.newcopy(os.path.join(self.parent.path, key)).dir = self.parent
        else:
            raise TypeError(f"Item to be set must be type {self.class_type.__name__}, not {type(val).__name__}")

    def __delitem__(self, key: str) -> None:
        self[key].delete()


class FileAccessor(Accessor):
    collection_name = "_files"

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._set_class_type()
        self._sync, self._access = self.parent._synchronize_files, self.parent._access_files

    def __getitem__(self, key: str) -> File:
        return self._access(key)

    def __setitem__(self, key: str, val: File) -> None:
        super().__setitem__(key, val)

    def _set_class_type(self) -> None:
        from .file import File
        self.class_type = File


class DirAccessor(Accessor):
    collection_name = "_dirs"

    def __init__(self, parent: Dir):
        super().__init__(parent=parent)
        self._sync, self._access = self.parent._synchronize_dirs, self.parent._access_dirs

    def __getitem__(self, key: str) -> Dir:
        return self._access(key)

    def __setitem__(self, key: str, val: Dir) -> None:
        super().__setitem__(key, val)

    def _set_class_type(self) -> None:
        from .dir import Dir
        self.class_type = Dir


class DotAccessor:
    _strip_extension: bool = None

    def __init__(self, accessor: Accessor) -> None:
        self.__accessor, self.__ready = accessor, False
        self.__mappings: Dict[str, List[str]] = None
        self.__pending: List[str] = None

    def __getattribute__(self, name: str) -> Any:
        if name.startswith("_"):
            return super().__getattribute__(name)
        else:
            return self.__accessor[super().__getattribute__(name)]

    def __getattr__(self, attr: str) -> Any:
        if attr.startswith("_"):
            raise AttributeError(attr)

        if not self.__ready:
            self.__prepare()

        if attr in self.__mappings:
            names = self.__mappings[attr]
            if len(names) > 1:
                raise AmbiguityError(f"""'{attr}' does not resolve uniquely. Could refer to any of: {", ".join([f"'{name}'" for name in names])}.""")
            else:
                return self.__accessor[names[0]]
        else:
            return self.__accessor[attr]

    def _acquire(self, names: List[str]) -> None:
        self.__pending, self.__ready = names, False

        if not self.__accessor.parent.lazy:
            self.__acquire_references_as_attributes()
            self.__ready = True

    def __prepare(self) -> None:
        if self.__accessor.parent.lazy:
            self.__set_mappings_from_pending()
            self.__ready = True

    def __set_mappings_from_pending(self) -> None:
        self.__mappings = {}
        for name in self.__pending:
            clean = str((Str(name).before_first(r"\.") if self._strip_extension else Str(name)).identifier())
            self.__mappings.setdefault(clean, []).append(name)

    def __acquire_references_as_attributes(self) -> None:
        self.__set_mappings_from_pending()
        for clean, names in self.__mappings.items():
            if len(names) == 1:
                setattr(self, clean, names[0])


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
