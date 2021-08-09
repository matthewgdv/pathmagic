from __future__ import annotations

import os
import pathlib

from pathmagic.helper import PathLike

from .format import Format


class Link(Format):
    extensions = {"lnk"}

    @classmethod
    def initialize(cls) -> None:
        import win32com.client as win
        cls.module = win
        cls.readfuncs.update({"lnk": cls._readlink})
        cls.writefuncs.update({"lnk": cls._writelink})

    def _readlink(self, linkpath: PathLike) -> PathLike:
        shell = self.module.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        path = pathlib.Path(shortcut.Targetpath)

        if path.is_file():
            constructor = self.file.settings.file_class
        elif path.is_dir():
            constructor = self.file.settings.dir_class
        else:
            raise RuntimeError(f"Unrecognized path type of shortcut target: '{shortcut.Targetpath}'. Must be file or directory.")

        return constructor(path)

    def _writelink(self, item: PathLike, linkpath: PathLike) -> None:
        shell = self.module.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(os.path.realpath(linkpath))
        shortcut.Targetpath = os.path.realpath(item)
        shortcut.save()
