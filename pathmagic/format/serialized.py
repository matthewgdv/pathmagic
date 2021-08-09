from __future__ import annotations


from typing import Any, TYPE_CHECKING

from pathmagic.helper import PathLike

from .format import Format

if TYPE_CHECKING:
    from pathmagic.file import File


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
