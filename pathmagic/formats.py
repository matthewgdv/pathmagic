from __future__ import annotations

import os
import json
import tarfile
import zipfile
from abc import ABCMeta
from collections import defaultdict
from types import MethodType
from typing import Any, Callable, Optional, Set, Type, TYPE_CHECKING
import pathlib

from maybe import Maybe
from subtypes import ValueEnum, Str, Html, Xml, Frame, TranslatableMeta

from .path import PathLike

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


class FileFormats:
    """An class holding references to all file formats (and file extensions) currently registered to the FormatHandler."""


class FormatHandler:
    """A class to manage file formats and react accordingly by file extension when reading and writing to/from files."""
    extensions: Set[str] = set()
    mappings: dict[str, Type[Format]] = {}

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
        if self.format is None or self.file.extension not in self.format.extensions:
            try:
                self.format = self.mappings.get(self.file.extension, Default)(self.file)
            except ImportError as ex:
                raise ImportError(f"Import failed: {ex}. Please ensure this module is available in order to read or write to '{self.file.extension}' files.")

    @classmethod
    def add_format(cls, formatter_class: Type[Format]) -> None:
        cls.extensions.update(Maybe(formatter_class.extensions).else_(set()))
        cls.mappings.update({extension: formatter_class for extension in Maybe(formatter_class.extensions).else_({})})
        setattr(FileFormats, formatter_class.__name__, ValueEnum(formatter_class.__name__, {str(Str(extension).case.constant()): extension for extension in formatter_class.extensions}))


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
    extensions: Set[str] = None
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
        raise RuntimeError("Must provide an implementation of Format.initialize(), which will only be called the first time the Format is instanciated. This method should import expensive modules (if needed) and update the Format.readfuncs and Format.writefuncs dictionaries.")

    def read(self, **kwargs: Any) -> Any:
        return self.readfuncs[self.file.extension](str(self.file), **kwargs)

    def read_help(self) -> None:
        help(self.readfuncs[self.file.extension])

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item, str(self.file), **kwargs)

    def write_help(self) -> None:
        help(self.writefuncs[self.file.extension])


class Pdf(Format):
    extensions = {"pdf"}

    @classmethod
    def initialize(cls) -> None:
        import PyPDF2

        cls.module = PyPDF2
        cls.readfuncs.update({"pdf": cls.module.PdfFileReader})


class Tabular(Format):
    extensions = {"xlsx", "csv"}

    @classmethod
    def initialize(cls) -> None:
        import pandas as pd

        cls.module = pd
        cls.readfuncs.update({"xlsx": Frame.from_excel, "csv": Frame.from_csv})
        cls.writefuncs.update({"xlsx": Frame.to_excel, "csv": Frame.to_csv})

    def read_help(self) -> None:
        help({"xlsx": self.module.read_excel, "csv": self.module.read_csv}[self.file.extension])

    def write_help(self) -> None:
        help({"xlsx": self.module.DataFrame.to_excel, "csv": self.module.DataFrame.to_csv}[self.file.extension])


class Word(Format):
    extensions = {"docx"}

    @classmethod
    def initialize(cls) -> None:
        import docx
        from docx.document import Document

        cls.module = docx
        cls.readfuncs.update({"docx": cls.module.Document})
        cls.writefuncs.update({"docx": Document.save})


class Image(Format):
    extensions = {"png", "jpg", "jpeg"}

    @classmethod
    def initialize(cls) -> None:
        from PIL import Image

        cls.module = Image
        cls.readfuncs.update({extension: cls.module.open for extension in cls.extensions})
        cls.writefuncs.update({extension: cls.module.Image.save for extension in cls.extensions})

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item.convert("RGB"), str(self.file), **kwargs)


class Audio(Format):
    extensions = {"mp3", "wav", "ogg", "flv"}

    @classmethod
    def initialize(cls) -> None:
        import pydub

        cls.module = pydub
        cls.readfuncs.update(
            {
                "mp3": cls.module.AudioSegment.from_mp3,
                "wav": cls.module.AudioSegment.from_wav,
                "ogg": cls.module.AudioSegment.from_ogg,
                "flv": cls.module.AudioSegment.from_flv
            }
        )
        cls.writefuncs.update(
            {
                "mp3": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="mp3", **kwargs),
                "wav": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="wav", **kwargs),
                "ogg": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="ogg", **kwargs),
                "flv": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="flv", **kwargs)
            }
        )

    def write_help(self) -> None:
        help(self.module.AudioSegment.export)


class Video(Format):
    extensions = {"mp4", "mkv", "avi", "gif"}

    @classmethod
    def initialize(cls) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import moviepy.editor as edit

        cls.module = edit
        cls.readfuncs.update({extension: edit.VideoFileClip for extension in cls.extensions})

    def read(self, **kwargs: Any) -> Any:
        out = self.readfuncs[self.file.extension](str(self.file), **kwargs)
        out._repr_html_ = MethodType(lambda this: this.ipython_display()._data_and_metadata(), out)
        return out


class Compressed(Format):
    extensions = {"zip", "tar"}

    @classmethod
    def initialize(cls) -> None:
        from pathmagic import Dir

        cls.readfuncs.update({"zip": zipfile.ZipFile, "tar": tarfile.TarFile})
        cls.writefuncs.update({"zip": Dir.compress})

    def read(self, **kwargs: Any) -> Dir:
        output = self.file.parent.new_dir(self.file.stem)
        with self.readfuncs[self.file.extension](str(self.file), **kwargs) as filehandle:
            filehandle.extractall(path=output.path)

        return output

    def write(self, item: Dir, **kwargs: Any) -> None:
        item.compress(**kwargs)

    def write_help(self) -> None:
        help({"zip": zipfile.ZipFile.write}[self.file.extension])


class Link(Format):
    extensions = {"lnk"}

    @classmethod
    def initialize(cls) -> None:
        import win32com.client as win
        cls.module = win
        cls.readfuncs.update({"lnk": cls._readlink})
        cls.writefuncs.update({"lnk": cls._writelink})

    def _readlink(self, linkpath: PathLike) -> PathLike:
        shell = self.module.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        path = pathlib.Path(shortcut.Targetpath)

        if path.is_file():
            constructor = self.file.settings.file_class
        elif path.is_dir():
            constructor = self.file.settings.dir_class
        else:
            raise RuntimeError(f"Unrecognized path type of shortcut target: '{shortcut.Targetpath}'. Must be file or directory.")

        return constructor(path)

    def _writelink(self, item: PathLike, linkpath: PathLike) -> None:
        shell = self.module.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        shortcut.Targetpath = os.path.realpath(item)
        shortcut.save()


class Serialized(Format):
    extensions = {"pkl"}

    def __init__(self, file: File) -> None:
        from iotools import Serializer

        super().__init__(file=file)
        self.serializer = Serializer(file)

    @classmethod
    def initialize(cls) -> None:
        import dill

        cls.module = dill
        cls.readfuncs.update({"pkl": cls.module.load})
        cls.writefuncs.update({"pkl": cls.module.dump})

    def read(self, **kwargs: Any) -> Any:
        return self.serializer.deserialize(**kwargs)

    def write(self, item: PathLike, **kwargs: Any) -> None:
        self.serializer.serialize(item, **kwargs)


class Json(Format):
    extensions = {"json"}

    @classmethod
    def initialize(cls) -> None:
        cls.module, cls.translator = json, TranslatableMeta.translator
        cls.readfuncs.update({"json": json.load})
        cls.writefuncs.update({"json": json.dump})

    def read(self, namespace: bool = True, **kwargs: Any) -> Any:
        try:
            with open(self.file) as file:
                return self.translator(self.readfuncs[self.file.extension](file, **kwargs))
        except self.module.JSONDecodeError:
            return self.file.path.read_text() or None

    def write(self, item: Any, indent: int = 4, **kwargs: Any) -> None:
        with open(self.file, "w") as file:
            self.writefuncs[self.file.extension](item, file, indent=indent, **kwargs)


class Markup(Format):
    extensions = {"html", "xml"}

    def __init__(self, file: File) -> None:
        super().__init__(file)
        self.io = Default(file)

    @classmethod
    def initialize(cls) -> None:
        import bs4

        cls.module = bs4
        cls.readfuncs.update({"html": Html, "xml": Xml})
        cls.writefuncs.update({extension: open for extension in cls.extensions})

    def read(self, **kwargs: Any) -> Any:
        return self.readfuncs[self.file.extension](self.io.read(),  **kwargs)

    def write(self, item: Any, **kwargs: Any) -> None:
        self.io.write(str(item), **kwargs)


class Default(Format):
    extensions: Set[str] = set()

    def __init__(self, file: File) -> None:
        super().__init__(file=file)

    @classmethod
    def initialize(cls) -> None:
        cls.readfuncs = cls.writefuncs = defaultdict(lambda: open)

    def read(self, **kwargs: Any) -> Optional[Str]:
        try:
            kwargs = kwargs if kwargs else {"encoding": "utf-8"}
            with open(self.file, **kwargs) as filehandle:
                return Str(filehandle.read())
        except UnicodeDecodeError:
            return None

    def write(self, item: Any, append: bool = False, **kwargs: Any) -> None:
        true_kwargs = {**{"mode": "a" if append else "w", "encoding": "utf-8"}, **kwargs}
        with open(self.file, **true_kwargs) as filehandle:
            if item is None:
                pass
            elif isinstance(item, str):
                filehandle.write(item)
            elif isinstance(item, list):
                filehandle.write("\n".join([str(line) for line in item]))
            else:
                filehandle.write(str(item))
