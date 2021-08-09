from __future__ import annotations

import tarfile
import zipfile

from typing import Any, TYPE_CHECKING

from .format import Format

if TYPE_CHECKING:
    from pathmagic.dir import Dir


class Compressed(Format):
    extensions = {"zip", "tar"}

    @classmethod
    def initialize(cls) -> None:
        from pathmagic import Dir

        cls.readfuncs.update({"zip": zipfile.ZipFile, "tar": tarfile.TarFile})
        cls.writefuncs.update({"zip": Dir.compress})

    def read(self, **kwargs: Any) -> Dir:
        output = self.file.parent.new_dir(self.file.stem)
        with self.readfuncs[self.file.extension](str(self.file), **kwargs) as filehandle:
            filehandle.extractall(path=output.path)

        return output

    def write(self, item: Dir, **kwargs: Any) -> None:
        item.compress(**kwargs)

    def write_help(self) -> None:
        help({"zip": zipfile.ZipFile.write}[self.file.extension])
