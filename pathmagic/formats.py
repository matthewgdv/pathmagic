from __future__ import annotations

import json
import tarfile
import zipfile
from abc import ABCMeta
from types import MethodType
from typing import Any, Callable, TYPE_CHECKING

from subtypes import Str, Html, Xml, TranslatableMeta

from .pathmagic import PathLike

if TYPE_CHECKING:
    from .dir import Dir
    from .file import File


class FormatMeta(ABCMeta):
    extensions: dict[str, type[Format]] = {}

    def __new__(mcs, name: str, bases: Any, namespace: dict) -> type[Format]:
        cls: type[Format] = super().__new__(mcs, name, bases, namespace)

        if cls.extensions:
            mcs.extensions.update({extension: cls for extension in cls.extensions})

        return cls


class Format(metaclass=FormatMeta):
    """
    An abstract base class representing a file format. At minimum, descendants must provide set of file extensions as the 'Format.extensions' and an implementation for the
    'Format.reader' and 'Format.writer' properties.
    """
    extensions: set[str] = None

    def __init__(self, file: File):
        self.file = file

    @property
    def reader(self) -> Callable:
        raise NotImplementedError

    def read(self, **kwargs: Any) -> Any:
        return self.reader(str(self.file), **kwargs)

    def read_help(self) -> None:
        help(self.reader)

    @property
    def writer(self) -> Callable:
        raise NotImplementedError

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writer(item, str(self.file), **kwargs)

    def write_help(self) -> None:
        help(self.writer)


class Pdf(Format):
    extensions = {"pdf"}

    @property
    def reader(self) -> Callable:
        import PyPDF2

        return PyPDF2.PdfFileReader


class Tabular(Format):
    extensions = {"xlsx", "csv"}

    @property
    def reader(self) -> Callable:
        from sqlhandler import Frame

        return {
            'xlsx': Frame.from_excel,
            'csv': Frame.from_csv,
        }[self.file.extension]

    @property
    def writer(self) -> Callable:
        from sqlhandler import Frame

        return {
            'xlsx': Frame.to_excel,
            'csv': Frame.to_excel,
        }[self.file.extension]


class Word(Format):
    extensions = {"docx"}

    @property
    def reader(self) -> Callable:
        from docx.document import Document

        return Document

    @property
    def writer(self) -> Callable:
        from docx.document import Document

        return Document.save


class Image(Format):
    extensions = {"png", "jpg", "jpeg"}

    @property
    def reader(self) -> Callable:
        from PIL import Image

        return Image.open

    @property
    def writer(self) -> Callable:
        from PIL import Image

        return Image.save

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writer(item.convert('RGB'), str(self.file), **kwargs)


class Audio(Format):
    extensions = {'mp3', 'wav', 'ogg', 'flv'}

    @property
    def reader(self) -> Callable:
        import pydub

        return {
            'mp3': pydub.AudioSegment.from_mp3,
            'wav': pydub.AudioSegment.from_wav,
            'ogg': pydub.AudioSegment.from_ogg,
            'flv': pydub.AudioSegment.from_flv
        }[self.file.extension]

    @property
    def writer(self) -> Callable:
        import pydub

        return pydub.AudioSegment.export

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writer(item, str(self.file), format=self.file.extension, **kwargs)


class Video(Format):
    extensions = {'mp4', 'mkv', 'avi', 'gif'}

    @property
    def reader(self) -> Callable:
        from moviepy.editor import VideoFileClip

        return VideoFileClip

    def read(self, **kwargs: Any) -> Any:
        out = super().read(**kwargs)
        out._repr_html_ = MethodType(lambda this: this.ipython_display()._data_and_metadata(), out)

        return out


class Compressed(Format):
    extensions = {'zip', 'tar'}

    @property
    def reader(self) -> Callable:
        return {
            'zip': zipfile.ZipFile,
            'tar': tarfile.TarFile,
        }[self.file.extension]

    @property
    def writer(self) -> Callable:
        from pathmagic import Dir

        return Dir.compress

    def read(self, **kwargs: Any) -> Dir:
        output = self.file.parent.new_dir(self.file.stem)

        with super().read(**kwargs) as stream:
            stream.extractall(path=output.path)

        return output

    def write(self, item: Dir, **kwargs: Any) -> None:
        self.writer(item, **kwargs)


class Pickle(Format):
    extensions = {'pkl', 'pickle'}

    def __init__(self, file: File) -> None:
        from iotools import Serializer

        super().__init__(file=file)
        self.serializer = Serializer(file)

    @property
    def reader(self) -> Callable:
        import dill

        return dill.load

    @property
    def writer(self) -> Callable:
        import dill

        return dill.dump

    def read(self, **kwargs: Any) -> Any:
        return self.serializer.deserialize(**kwargs)

    def write(self, item: PathLike, **kwargs: Any) -> None:
        self.serializer.serialize(item, **kwargs)


class Json(Format):
    extensions = {'json'}

    def __init__(self, file: File) -> None:
        super().__init__(file=file)
        self.translator = TranslatableMeta.translator

    @property
    def reader(self) -> Callable:
        return json.load

    @property
    def writer(self) -> Callable:
        return json.dump

    def read(self, namespace: bool = True, **kwargs: Any) -> Any:
        with open(self.file) as file:
            return self.translator(self.reader(file, **kwargs))

    def write(self, item: Any, **kwargs: Any) -> None:
        kwargs = {'indent': 4} | kwargs

        with open(self.file, 'w') as file:
            self.writer(item, file, **kwargs)


class Markup(Format):
    extensions = {'html', 'xml'}

    def __init__(self, file: File) -> None:
        super().__init__(file)
        self.io = Default(file)

    @property
    def reader(self) -> Callable:
        return {
            'html': Html,
            'xml': Xml,
        }[self.file.extension]

    @property
    def writer(self) -> Callable:
        return open

    def read(self, **kwargs: Any) -> Any:
        return self.reader(self.io.read(), **kwargs)

    def write(self, item: Any, **kwargs: Any) -> None:
        self.io.write(str(item), **kwargs)


class Default(Format):
    extensions: set[str] = set()

    def read(self, **kwargs: Any) -> Str:
        kwargs = {'encoding': 'utf-8'} | kwargs

        with open(self.file, **kwargs) as stream:
            return Str(stream.read())

    def write(self, item: Any, append: bool = False, **kwargs: Any) -> None:
        if item is None:
            return

        kwargs = {'mode': 'a' if append else 'w', 'encoding': 'utf-8'} | kwargs

        with open(self.file, **kwargs) as stream:
            if isinstance(item, str):
                stream.write(item)
            elif isinstance(item, list):
                stream.write('\n'.join(str(line) for line in item))
            else:
                stream.write(str(item))
