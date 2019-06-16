from __future__ import annotations

import os
import io
import tarfile
import zipfile
from abc import ABCMeta
from collections import defaultdict
from types import MethodType
from typing import Any, Callable, Dict, Optional, Set, Type, cast, TYPE_CHECKING

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
        self.read_kwargs = self.write_kwargs = {}  # type: Dict[str, Any]
        self.format: Format = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}(format={type(self.format).__name__ if self.format is not None else None}, file={self.file})"

    def read(self, **kwargs: Any) -> Any:
        self.read_kwargs = kwargs if kwargs else self.read_kwargs
        self._ensure_format()

        return self.format.read(**self.read_kwargs)

    def write(self, item: Any, **kwargs: Any) -> Any:
        self.write_kwargs = kwargs if kwargs else self.write_kwargs
        self._ensure_format()

        return self.format.write(item=item, **self.write_kwargs)

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
        FileFormats.extend_enum(formatter_class.__name__, Enum(formatter_class.__name__, {str(Str(extension).camel_case(pascal=True)): extension for extension in formatter_class.formats}))


class FormatMeta(ABCMeta):
    readfuncs: Dict[str, Callable]
    writefuncs: Dict[str, Callable]

    def __new__(mcs, name: str, bases: Any, namespace: dict) -> FormatMeta:
        cls = cast(FormatMeta, super().__new__(mcs, name, bases, namespace))

        cls.readfuncs, cls.writefuncs = {}, {}

        if bases:
            FormatHandler.add_format(cls)  # type: ignore

        return cls


class Format(metaclass=FormatMeta):
    formats: Set[str] = None
    readfuncs = writefuncs = None  # type: Dict[str, Callable]

    initialized = False
    _module: Any = None

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

    def initialize(self) -> None:
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

    def initialize(self) -> None:
        import PyPDF2

        self.module = PyPDF2
        self.readfuncs.update({"pdf": self.module.PdfFileReader})


class Tabular(Format):
    formats = {"xlsx", "csv"}

    def initialize(self) -> None:
        import pandas as pd

        self.module = pd
        self.readfuncs.update({"xlsx": Frame.from_excel, "csv": Frame.from_csv})
        self.writefuncs.update({"xlsx": Frame.to_excel, "csv": Frame.to_csv})

    def readhelp(self) -> None:
        help({"xlsx": self.module.read_excel, "csv": self.module.read_csv}[self.file.extension])

    def writehelp(self) -> None:
        help({"xlsx": self.module.DataFrame.to_excel, "csv": self.module.DataFrame.to_csv}[self.file.extension])


class Word(Format):
    formats = {"docx"}

    def initialize(self) -> None:
        import docx
        from docx import document

        self.module = docx
        self.readfuncs.update({"docx": self.module.Document})
        self.writefuncs.update({"docx": document.Document.save})


class Image(Format):
    formats = {"png", "jpg", "jpeg"}

    def initialize(self) -> None:
        from PIL import Image

        self.module = Image
        self.readfuncs.update({extension: self.module.open for extension in self.formats})
        self.writefuncs.update({extension: self.module.Image.save for extension in self.formats})

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item.convert("RGB"), self.file.path, **kwargs)


class Music(Format):
    formats = {"mp3", "wav", "ogg", "flv"}

    def initialize(self) -> None:
        import pydub

        self.module = pydub
        self.readfuncs.update(
            {
                "mp3": self.module.AudioSegment.from_mp3,
                "wav": self.module.AudioSegment.from_wav,
                "ogg": self.module.AudioSegment.from_ogg,
                "flv": self.module.AudioSegment.from_flv
            }
        )
        self.writefuncs.update(
            {
                "mp3": lambda *args, **kwargs: self.module.AudioSegment.export(*args, format="mp3", **kwargs),
                "wav": lambda *args, **kwargs: self.module.AudioSegment.export(*args, format="wav", **kwargs),
                "ogg": lambda *args, **kwargs: self.module.AudioSegment.export(*args, format="ogg", **kwargs),
                "flv": lambda *args, **kwargs: self.module.AudioSegment.export(*args, format="flv", **kwargs)
            }
        )

    def writehelp(self) -> None:
        help(self.module.AudioSegment.export)


class Video(Format):
    formats = {"mp4", "mkv", "avi", "gif"}

    def initialize(self) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import moviepy.editor as edit

        self.module = edit
        self.readfuncs.update({extension: edit.VideoFileClip for extension in self.formats})

    def read(self, **kwargs: Any) -> Any:
        out = self.readfuncs[self.file.extension](self.file.path, **kwargs)
        out._repr_html_ = MethodType(lambda this: this.ipython_display()._data_and_metadata(), out)
        return out


class Compressed(Format):
    formats = {"zip", "tar"}

    def initialize(self) -> None:
        self.readfuncs.update({"zip": zipfile.ZipFile, "tar": tarfile.TarFile})
        self.writefuncs.update({"zip": type(self.file.dir).compress})

    def read(self, **kwargs: Any) -> Dir:
        output = self.file.dir.newdir(self.file.prename)
        with self.readfuncs[self.file.extension](self.file.path, **kwargs) as filehandle:
            filehandle.extractall(path=output.path)

        return output

    def write(self, item: Dir, **kwargs: Any) -> None:
        item.compress(**kwargs)

    def writehelp(self) -> None:
        help({"zip": zipfile.ZipFile.write}[self.file.extension])


class Link(Format):
    formats = {"lnk"}

    def initialize(self) -> None:
        self.readfuncs.update({"lnk": self._readlink})
        self.writefuncs.update({"lnk": self._writelink})

    def _readlink(self, linkpath: PathLike) -> PathLike:
        import win32com.client as win

        shell = win.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))

        if os.path.isfile(shortcut.Targetpath):
            constructor = type(self.file)
        elif os.path.isdir(shortcut.Targetpath):
            constructor = type(self.file.dir)
        else:
            raise RuntimeError(f"Unrecognized path type of shortcut target: '{shortcut.Targetpath}'. Must be file or directory.")

        ret = constructor(shortcut.Targetpath)
        return ret

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

    def initialize(self) -> None:
        import dill

        self.module = dill
        self.readfuncs.update({"pkl": self.module.load})
        self.writefuncs.update({"pkl": self.module.dump})

    def read(self, **kwargs: Any) -> Any:
        return self.serializer.deserialize(**kwargs)

    def write(self, item: PathLike, **kwargs: Any) -> None:
        self.serializer.serialize(item, **kwargs)


class MarkUp(Format):
    formats = {"html", "xml"}

    def __init__(self, file: File) -> None:
        self.io = Default(file)

    def initialize(self) -> None:
        import bs4

        self.module = bs4
        self.readfuncs.update({extension: bs4.BeautifulSoup for extension in self.formats})
        self.writefuncs.update({extension: io.TextIOWrapper for extension in self.formats})

    def read(self, **kwargs: Any) -> Any:
        return Markup(self.io.read(), **kwargs)

    def write(self, item: Any, **kwargs: Any) -> None:
        self.io.write(str(item), **kwargs)


class Default(Format):
    formats: Set[str] = {"txt"}
    readfuncs = writefuncs = defaultdict(lambda: io.TextIOWrapper)  # type: ignore

    def __init__(self, file: File) -> None:
        super().__init__(file=file)
        type(self).formats.add(file.extension)

    def initialize(self) -> None:
        pass

    def read(self, **kwargs: Any) -> Optional[str]:
        try:
            with open(self.file, encoding="utf-8", **kwargs) as filehandle:
                return filehandle.read()
        except UnicodeDecodeError:
            return None

    def write(self, item: str, append: bool = False, **kwargs: Any) -> None:
        with open(self.file, "a" if append else "w", encoding="utf-8", **kwargs) as filehandle:
            filehandle.write(str(item))
