from __future__ import annotations

from .format import Format


class Pdf(Format):
    extensions = {"pdf"}

    @classmethod
    def initialize(cls) -> None:
        import PyPDF2

        cls.module = PyPDF2
        cls.readfuncs.update({"pdf": cls.module.PdfFileReader})
