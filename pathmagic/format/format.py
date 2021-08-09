from __future__ import annotations


from abc import ABCMeta
from typing import Any, Callable, Optional, Type, TYPE_CHECKING

from subtypes import Str, NameSpace

if TYPE_CHECKING:
    from pathmagic.file import File


# TODO: Refactor the interface of the Format class in Python 3.10 once the match statement is available


class FormatHandler:
    """A class to manage file formats and react accordingly by file extension when reading and writing to/from files."""
    extensions: dict[str, Type[Format]] = {}
    formats = NameSpace()

    def __init__(self, file: File):
        self.file = file
        self.format: Optional[Format] = None

        if self.file.extension not in self.extensions:
            self._ensure_format()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(format={type(self.format).__name__ if self.format is not None else None}, file={self.file})"

    def read(self, **kwargs: Any) -> Any:
        self._ensure_format()
        return self.format.read(**kwargs)

    def write(self, item: Any, **kwargs: Any) -> Any:
        self._ensure_format()
        return self.format.write(item=item, **kwargs)

    def append(self, text: str) -> None:
        from .default import Default

        self._ensure_format()
        if not isinstance(self.format, Default):
            raise RuntimeError(f"Cannot 'append' to non-textual File with extension '{self.file.extension}'.")

        self.format.write(item=text, append=True)

    def read_help(self) -> None:
        self._ensure_format()
        self.format.read_help()

    def write_help(self) -> None:
        self._ensure_format()
        self.format.write_help()

    def _ensure_format(self) -> None:
        from .default import Default

        if self.format is None or self.file.extension not in self.format.extensions:
            try:
                self.format = self.extensions.get(self.file.extension, Default)(self.file)
            except ImportError as ex:
                raise ImportError(f"Import failed: {ex}. Please ensure this module is available in order to read or write to '{self.file.extension}' files.")

    @classmethod
    def add_format(cls, formatter_class: Type[Format]) -> None:
        if formatter_class.extensions is None:
            raise TypeError(f"Cannot register {Format.__name__} subclass {formatter_class.__name__} without valid extensions")

        cls.extensions.update({extension: formatter_class for extension in (formatter_class.extensions or {})})
        cls.formats[formatter_class.__name__] = NameSpace({str(Str(extension).case.constant()): extension for extension in formatter_class.extensions})


class FormatMeta(ABCMeta):
    def __new__(mcs, name: str, bases: Any, namespace: dict) -> Type[Format]:
        # noinspection PyTypeChecker
        cls: Type[Format] = super().__new__(mcs, name, bases, namespace)

        cls.readfuncs, cls.writefuncs = {}, {}

        if cls.extensions:
            FormatHandler.add_format(cls)

        return cls


class Format(metaclass=FormatMeta):
    """
    An abstract base class representing a file format. Descendants must provide a 'Format.extensions' class attribute (a set of file extensions), and must update the
    'Format.readfuncs' and 'Format.writefuncs' dictionaries to teach the class how to read from and write to files by extension.
    The Format.initialize() classmethod must be overriden, and the Format.read(), Format.write(), Format.read_help(), and Format.write_help() methods may also be overriden
    in situations where simply registering the currect callback to the 'Format.readfuncs' and 'Format.writefuncs' dicts is not enough (such as when the callback doesn't have the correct signature).
    """

    extensions: set[str] = None
    readfuncs = writefuncs = None  # type: dict[str, Callable]

    initialized = False
    module: Any = None

    def __init__(self, file: File):
        self.file = file

        if not type(self).initialized:
            self.initialize()
            type(self).initialized = True

    @classmethod
    def initialize(cls) -> None:
        raise TypeError("Must provide an implementation of Format.initialize(), which will only be called the first time the Format is instanciated. This method should import expensive modules (if needed) and update the Format.readfuncs and Format.writefuncs dictionaries.")

    def read(self, **kwargs: Any) -> Any:
        return self.readfuncs[self.file.extension](str(self.file), **kwargs)

    def read_help(self) -> None:
        help(self.readfuncs[self.file.extension])

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item, str(self.file), **kwargs)

    def write_help(self) -> None:
        help(self.writefuncs[self.file.extension])
