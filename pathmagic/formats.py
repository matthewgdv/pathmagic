from __future__ import annotations

import os
import tarfile
import zipfile
from abc import ABCMeta
from collections import defaultdict
from types import MethodType
from typing import Any, Callable, Dict, Optional, Set, Type, TYPE_CHECKING
import pathlib

from maybe import Maybe
from subtypes import Enum, Str, Markup, Frame

from .basepath import PathLike

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


class FileFormats(Enum):
    pass


class FormatHandler:
    formats: Set[str] = set()
    mappings: Dict[str, Type[Format]] = {}

    def __init__(self, file: File):
        self.file = file
        self.format: Format = None

        if self.file.extension not in self.formats:
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

    def readhelp(self) -> None:
        self._ensure_format()
        self.format.readhelp()

    def writehelp(self) -> None:
        self._ensure_format()
        self.format.writehelp()

    def _ensure_format(self) -> None:
        if self.format is None or self.file.extension not in self.format.formats:
            try:
                self.format = self.mappings.get(self.file.extension, Default)(self.file)
            except ImportError as ex:
                raise ImportError(f"Import failed: {ex}. Please ensure this module is available in order to read or write to '{self.file.extension}' files.")

    @classmethod
    def add_format(cls, formatter_class: Type[Format]) -> None:
        cls.formats.update(Maybe(formatter_class.formats).else_(set()))
        cls.mappings.update({extension: formatter_class for extension in Maybe(formatter_class.formats).else_({})})
        FileFormats.extend_enum(formatter_class.__name__, Enum(formatter_class.__name__, {str(Str(extension).case.constant): extension for extension in formatter_class.formats}))


class FormatMeta(ABCMeta):
    def __new__(mcs, name: str, bases: Any, namespace: dict) -> Type[Format]:
        cls: Type[Format] = super().__new__(mcs, name, bases, namespace)

        cls.readfuncs, cls.writefuncs = {}, {}

        if cls.formats:
            FormatHandler.add_format(cls)

        return cls


class Format(metaclass=FormatMeta):
    formats: Set[str] = None
    readfuncs = writefuncs = None  # type: Dict[str, Callable]

    initialized = False
    module: Any = None

    def __init__(self, file: File):
        self.file = file

        if not type(self).initialized:
            self.initialize()
            type(self).initialized = True

    @property
    def module(self) -> Any:
        return type(self)._module

    @module.setter
    def module(self, val: Any) -> None:
        type(self)._module = val

    @classmethod
    def initialize(cls) -> None:
        raise RuntimeError("Must provide an implementation of Format.initialize(), which will only be called the first time the Format is instanciated. This method should import expensive modules (if needed) and update the Format.readfuncs and Format.writefuncs dictionaries.")

    def read(self, **kwargs: Any) -> Any:
        return self.readfuncs[self.file.extension](self.file.path, **kwargs)

    def readhelp(self) -> None:
        help(self.readfuncs[self.file.extension])

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item, self.file.path, **kwargs)

    def writehelp(self) -> None:
        help(self.writefuncs[self.file.extension])


class Pdf(Format):
    formats = {"pdf"}

    @classmethod
    def initialize(cls) -> None:
        import PyPDF2

        cls.module = PyPDF2
        cls.readfuncs.update({"pdf": cls.module.PdfFileReader})


class Tabular(Format):
    formats = {"xlsx", "csv"}

    @classmethod
    def initialize(cls) -> None:
        import pandas as pd

        cls.module = pd
        cls.readfuncs.update({"xlsx": Frame.from_excel, "csv": Frame.from_csv})
        cls.writefuncs.update({"xlsx": Frame.to_excel, "csv": Frame.to_csv})

    def readhelp(self) -> None:
        help({"xlsx": self.module.read_excel, "csv": self.module.read_csv}[self.file.extension])

    def writehelp(self) -> None:
        help({"xlsx": self.module.DataFrame.to_excel, "csv": self.module.DataFrame.to_csv}[self.file.extension])


class Word(Format):
    formats = {"docx"}

    @classmethod
    def initialize(cls) -> None:
        import docx
        from docx import document

        cls.module = docx
        cls.readfuncs.update({"docx": cls.module.Document})
        cls.writefuncs.update({"docx": document.Document.save})


class Image(Format):
    formats = {"png", "jpg", "jpeg"}

    @classmethod
    def initialize(cls) -> None:
        from PIL import Image

        cls.module = Image
        cls.readfuncs.update({extension: cls.module.open for extension in cls.formats})
        cls.writefuncs.update({extension: cls.module.Image.save for extension in cls.formats})

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item.convert("RGB"), self.file.path, **kwargs)


class Audio(Format):
    formats = {"mp3", "wav", "ogg", "flv"}

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

    def writehelp(self) -> None:
        help(self.module.AudioSegment.export)


class Video(Format):
    formats = {"mp4", "mkv", "avi", "gif"}

    @classmethod
    def initialize(cls) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import moviepy.editor as edit

        cls.module = edit
        cls.readfuncs.update({extension: edit.VideoFileClip for extension in cls.formats})

    def read(self, **kwargs: Any) -> Any:
        out = self.readfuncs[self.file.extension](self.file.path, **kwargs)
        out._repr_html_ = MethodType(lambda this: this.ipython_display()._data_and_metadata(), out)
        return out


class Compressed(Format):
    formats = {"zip", "tar"}

    @classmethod
    def initialize(cls) -> None:
        from pathmagic import Dir

        cls.readfuncs.update({"zip": zipfile.ZipFile, "tar": tarfile.TarFile})
        cls.writefuncs.update({"zip": Dir.compress})

    def read(self, **kwargs: Any) -> Dir:
        output = self.file.dir.newdir(self.file.prename)
        with self.readfuncs[self.file.extension](str(self.file), **kwargs) as filehandle:
            filehandle.extractall(path=output.path)

        return output

    def write(self, item: Dir, **kwargs: Any) -> None:
        item.compress(**kwargs)

    def writehelp(self) -> None:
        help({"zip": zipfile.ZipFile.write}[self.file.extension])


class Link(Format):
    formats = {"lnk"}

    @classmethod
    def initialize(cls) -> None:
        cls.readfuncs.update({"lnk": cls._readlink})
        cls.writefuncs.update({"lnk": cls._writelink})

    def _readlink(self, linkpath: PathLike) -> PathLike:
        import win32com.client as win

        shell = win.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        path = pathlib.Path(shortcut.Targetpath)

        if path.is_file():
            constructor = self.file.settings.fileclass
        elif path.is_dir():
            constructor = self.file.settings.dirclass
        else:
            raise RuntimeError(f"Unrecognized path type of shortcut target: '{shortcut.Targetpath}'. Must be file or directory.")

        return constructor(path)

    @staticmethod
    def _writelink(item: PathLike, linkpath: PathLike) -> None:
        import win32com.client as win

        shell = win.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        shortcut.Targetpath = os.path.realpath(item)
        shortcut.save()


class Serialized(Format):
    formats = {"pkl"}

    def __init__(self, file: File) -> None:
        from miscutils import Serializer

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
    formats = {"json"}

    @classmethod
    def initialize(cls) -> None:
        import json

        cls.module = json
        cls.namespace_cls = cls._try_get_namespace_cls()
        cls.readfuncs.update({"json": cls.module.load})
        cls.writefuncs.update({"json": cls.module.dump})

    def read(self, **kwargs) -> Any:
        try:
            with open(self.file) as file:
                ret = self.readfuncs[self.file.extension](file)
                return self.namespace_cls(ret) if self.namespace_cls is not None and isinstance(ret, dict) else ret
        except self.module.JSONDecodeError:
            return self.file.path.read_text() or None

    def write(self, item: Any, indent: int = 4, **kwargs) -> None:
        if self.namespace_cls is not None and isinstance(item, self.namespace_cls):
            item = item.to_dict()

        with open(self.file, "w") as file:
            self.writefuncs[self.file.extension](item, file, indent=indent)

    @staticmethod
    def _try_get_namespace_cls() -> Any:
        try:
            from miscutils import NameSpace
            return NameSpace
        except ImportError:
            return lambda val: val


class MarkUp(Format):
    formats = {"html", "xml"}

    def __init__(self, file: File) -> None:
        super().__init__(file)
        self.io = Default(file)

    @classmethod
    def initialize(cls) -> None:
        import bs4

        cls.module = bs4
        cls.readfuncs.update({extension: bs4.BeautifulSoup for extension in cls.formats})
        cls.writefuncs.update({extension: open for extension in cls.formats})

    def read(self, **kwargs: Any) -> Any:
        return Markup(self.io.read(), **kwargs)

    def write(self, item: Any, **kwargs: Any) -> None:
        self.io.write(str(item), **kwargs)


class Default(Format):
    formats: Set[str] = {}

    def __init__(self, file: File) -> None:
        super().__init__(file=file)

    @classmethod
    def initialize(cls) -> None:
        cls.readfuncs = cls.writefuncs = defaultdict(lambda: open)  # type: ignore

    def read(self, **kwargs: Any) -> Optional[str]:
        try:
            kwargs = kwargs if kwargs else {"encoding": "utf-8"}
            with open(self.file, **kwargs) as filehandle:
                return filehandle.read()
        except UnicodeDecodeError:
            return None

    def write(self, item: str, append: bool = False, **kwargs: Any) -> None:
        kwargs = kwargs if kwargs else {"mode": "a" if append else "w", "encoding": "utf-8"}
        with open(self.file, **kwargs) as filehandle:
            filehandle.write(str(item))
