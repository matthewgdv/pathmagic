__all__ = ["File", "Dir", "PathMagic", "PathLike", "Format", "Settings"]

from .dir import Dir
from .file import File
from .pathmagic import PathMagic
from .helper import PathLike
from .formats import Format
from .settings import Settings

Settings.DEFAULT = Settings(if_exists=PathMagic.Enums.IfExists.FAIL, file_class=File, dir_class=Dir)
