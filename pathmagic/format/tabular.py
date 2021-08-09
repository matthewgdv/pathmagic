from __future__ import annotations

from .format import Format


class Tabular(Format):
    extensions = {"xlsx", "csv"}

    @classmethod
    def initialize(cls) -> None:
        import pandas as pd
        from sqlhandler import Frame

        cls.module = pd
        cls.readfuncs.update({"xlsx": Frame.from_excel, "csv": Frame.from_csv})
        cls.writefuncs.update({"xlsx": Frame.to_excel, "csv": Frame.to_csv})

    def read_help(self) -> None:
        help({"xlsx": self.module.read_excel, "csv": self.module.read_csv}[self.file.extension])

    def write_help(self) -> None:
        help({"xlsx": self.module.DataFrame.to_excel, "csv": self.module.DataFrame.to_csv}[self.file.extension])
