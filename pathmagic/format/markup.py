from __future__ import annotations

from pathlib import Path
from typing import Any, TYPE_CHECKING

from subtypes import Html, Xml

from .format import Format

if TYPE_CHECKING:
    from pathmagic.file import File


# TODO: Refactor the interface of the Format class in Python 3.10 once the match statement is available

class Markup(Format):
    extensions = {"html", "xml"}

    def __init__(self, file: File) -> None:
        super().__init__(file)

    @classmethod
    def initialize(cls) -> None:
        import bs4

        cls.module = bs4
        cls.readfuncs.update({"html": Html, "xml": Xml})
        cls.writefuncs.update({extension: Path.write_text for extension in cls.extensions})

    def read(self, **kwargs: Any) -> Any:
        return self.readfuncs[self.file.extension](self.io.read(), **kwargs)

    def write(self, item: Any, **kwargs: Any) -> None:
        self.file.path.write_text(str(item), **kwargs)
