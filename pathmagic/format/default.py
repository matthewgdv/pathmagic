from __future__ import annotations

from collections import defaultdict

from typing import Any, Optional, Set, TYPE_CHECKING

from subtypes import Str

from .format import Format

if TYPE_CHECKING:
    from pathmagic.file import File


class Default(Format):
    extensions: Set[str] = set()

    def __init__(self, file: File) -> None:
        super().__init__(file=file)

    @classmethod
    def initialize(cls) -> None:
        cls.readfuncs = cls.writefuncs = defaultdict(lambda: open)

    def read(self, **kwargs: Any) -> Optional[Str]:
        try:
            true_kwargs = {'encoding': "utf-8"} | kwargs
            with open(self.file, mode='r') as file_handle:
                return Str(file_handle.read())
        except UnicodeDecodeError:
            return None

    def write(self, item: Any, append: bool = False, **kwargs: Any) -> None:
        true_kwargs = {'encoding': "utf-8"} | kwargs | {'mode': 'a' if append else 'w'}

        with open(self.file, **true_kwargs) as file_handle:
            if item is None:
                pass
            elif isinstance(item, str):
                file_handle.write(item)
            elif isinstance(item, list):
                file_handle.write("\n".join([str(line) for line in item]))
            else:
                file_handle.write(str(item))
