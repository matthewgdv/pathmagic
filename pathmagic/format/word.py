from __future__ import annotations

from .format import Format


class Word(Format):
    extensions = {"docx"}

    @classmethod
    def initialize(cls) -> None:
        import docx
        from docx.document import Document

        cls.module = docx
        cls.readfuncs.update({"docx": cls.module.Document})
        cls.writefuncs.update({"docx": Document.save})
