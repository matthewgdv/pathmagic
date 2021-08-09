from __future__ import annotations

from typing import Type, TYPE_CHECKING

from .enums import Enums

if TYPE_CHECKING:
    from .file import File
    from .dir import Dir


class Settings:
    """A Settings class for PathMagic objects. Holds the constructors that PathMagic objects will use when they need to instanciate relatives, as well as controlling other aspects of behaviour."""

    DEFAULT: Settings = None

    def __init__(self, if_exists: Enums.IfExists, file_class: Type[File], dir_class: Type[Dir]) -> None:
        self.if_exists, self.file_class, self.dir_class = if_exists, file_class, dir_class

    def __repr__(self) -> str:
        return f"{type(self).__name__}({', '.join([f'{attr}={repr(val)}' for attr, val in self.__dict__.items() if not attr.startswith('_')])})"

    @classmethod
    def from_settings(cls, settings: Settings = None) -> Settings:
        if settings is None:
            return cls.from_settings(cls.DEFAULT)

        return cls(if_exists=settings.if_exists, file_class=settings.file_class, dir_class=settings.dir_class)
