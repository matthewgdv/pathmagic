from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from typing import Any, TYPE_CHECKING
from types import ModuleType
import pathlib

from maybe import Maybe

from .basepath import BasePath, PathLike, Settings
from .formats import FormatHandler

if TYPE_CHECKING:
    from .dir import Dir


class File(BasePath):
    """
    ORM class for manipulating files in the filesystem.

    Item access can be used to retrieve, set and delete the lines in the file. The len() represents the number of lines, the str() returns the file's path,
    the bool() resolves to true if the file is not empty, and iteration yields one line at a time. Changes to any object property (setting it) will be reflected in the file system.

    The file's name, prename (name without extension), extension, directory (as a Dir object), path (as a string) are properties that will cause the relevant changes in the
    filesystem when set. The 'if_exists' contols behaviour when copying or moving files into paths with existing file system objects, while using this object's properties and methods.
    The options are listed in this class' 'IfExists' enumeration.
    """

    def __init__(self, path: PathLike, settings: Settings = None) -> None:
        self._name = self._prename = self._extension = None  # type: str
        self._path: pathlib.Path = None
        self._contents: Any = None
        self._dir: Dir = None

        self._format = FormatHandler(self)
        self.settings = Maybe(settings).else_(self._get_settings())

        self._prepare_file_if_not_exists(path)
        self._set_params(path, move=False)

    def __repr__(self) -> str:
        try:
            return f"{type(self).__name__}(path={repr(self.path)}, lines={len(self) or '?'})"
        except FileNotFoundError:
            return f"{type(self).__name__}(path={repr(self.path)}, deleted=True, lines=?)"

    def __len__(self) -> int:
        if self.extension not in self._format.formats and not zipfile.is_zipfile(self.path) and not tarfile.is_tarfile(self.path):
            self.read()

        return 0 if not isinstance(self._contents, str) else self._contents.count("\n") + 1

    def __bool__(self) -> bool:
        return True if os.path.getsize(self) > 0 else False

    def __iter__(self) -> File:
        self.__iter = iter(self.contents.split("\n"))
        return self

    def __next__(self) -> str:
        return next(self.__iter)

    def __getitem__(self, key: int) -> str:
        return self.contents.split("\n")[key]

    def __setitem__(self, key: int, val: str) -> None:
        aslist = self.contents.split("\n")
        aslist[key] = val
        self.write("\n".join(aslist))

    def __delitem__(self, key: int) -> None:
        aslist = self.contents.split("\n")
        del aslist[key]
        self.write("\n".join(aslist))

    @property
    def path(self) -> pathlib.Path:
        """Return or set the File's full path as a string. Implicitly calls the 'move' method."""
        return self._path

    @path.setter
    def path(self, val: PathLike) -> None:
        self.move(val)

    @property
    def dir(self) -> Dir:
        """Return or set the File's directory as a Dir object. Implicitly calls that Dir object's 'bind' method."""
        if self._dir is None:
            self._dir = self.settings.dirclass(os.path.dirname(self), settings=self.settings)
        return self._dir

    @dir.setter
    def dir(self, val: Dir) -> None:
        self.settings.dirclass.from_pathlike(val, settings=self.settings)._bind(self, preserve_original=False)

    @property
    def name(self) -> str:
        """Return or set the File's full name, including extension. Implicitly calls the 'rename' method."""
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        self.rename(val)

    @property
    def prename(self) -> str:
        """Return or set the File's name up to the extension. Implicitly calls the 'rename' method."""
        return self._prename

    @prename.setter
    def prename(self, val: str) -> None:
        self.rename(f"{val}{f'.{self.extension}' if self.extension else ''}")

    @property
    def extension(self) -> str:
        """Return or set the File's extension. Is always saved and returned as lower-cased regardless of how the filename is cased. Implicitly calls the 'rename' method."""
        return self._extension

    @extension.setter
    def extension(self, val: str) -> None:
        if not ((val.startswith(".") and val.count(".") == 1) or val.count(".") == 0):
            raise ValueError(f"Too many '.' in extension name '{val}', or '.' not at start of string. 1 or 0 allowed. If 0, '.' will be set implicitly.")
        self.rename(f"{self.prename}{val if val.startswith('.') else f'.{val}'}")

    @property
    def contents(self) -> Any:
        """
        Return or set the File's contents. Implicitly calls the 'read' and 'write' methods on assignment.
        When appending text to large textual files, use the 'append' method rather than '+=' operator on this property to avoid unnecessary I/O.
        """
        return self.read()

    @contents.setter
    def contents(self, val: Any) -> None:
        self.write(val)

    def read(self, **kwargs: Any) -> str:
        """
        Return the File's contents as a string if it is not encoded, else attempt to return a useful Python object representing the file contents (e.g. Pandas DataFrame for tabular files, etc.).
        If provided, **kwargs will be passed on to whichever function will be used to read in the File's contents. Call the 'readhelp' method for that function's documentation.
        """
        self._contents = self._format.read(**kwargs)
        return self._contents

    def readhelp(self) -> None:
        """
        Print help documentation for the underlying reader function that is implicitly called when reading from this file type or accessing the 'contents' property.
        Any '**kwargs' passed to this File's 'read' method will be passed on to the underlying reader function. Do not resupply this File's path as a kwarg.
        """
        self._format.readhelp()

    def write(self, val: Any, **kwargs: Any) -> File:
        """Write to this File object's mapped file, overwriting anything already there. Returns self."""
        self._format.write(item=val)
        return self

    def writehelp(self) -> None:
        """
        Print help documentation for the underlying writer function that is implicitly called when writing to this file type or setting to the 'contents' property.
        Any '**kwargs' passed to this File's 'write' method will be passed on to the underlying writer function. Do not resupply this File's path as a kwarg.
        """
        self._format.writehelp()

    def append(self, val: str) -> File:
        """Write to the end of this File object's mapped file, leaving any existing text intact. Returns self."""
        self._format.append(text=val)
        return self

    def open(self, app: str = None) -> File:
        """Call the default application associated with this File's extension type on its own path. If an application is specified, open it with that instead. Returns self."""
        if app is None:
            os.startfile(self, "open")
        else:
            with subprocess.Popen([app, str(self)]):
                pass
        return self

    def opendir(self) -> File:
        """Call the default file system navigator on this File's directory. Returns self."""
        self.dir.open()
        return self

    def rename(self, name: str, extension: str = None) -> File:
        """Rename this File to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns self."""
        self._set_params(self.dir.path.joinpath(f"{name}{('.' + Maybe(extension)).else_('')}"))
        return self

    def newrename(self, name: str, extension: str = None) -> File:
        """Rename a new copy of this File in-place to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns the copy."""
        return self.newcopy(self.dir.path.joinpath(f"{name}{('.' + Maybe(extension)).else_('')}"))

    def newcopy(self, path: PathLike) -> File:
        """Create a new copy of this File at the specified path. Returns the new File."""
        self.copy(path)
        return self.settings.fileclass(path, settings=self.settings)

    def copy(self, path: PathLike) -> File:
        """Create a new copy of this File at the specified path. Returns self."""
        self._validate(path)
        shutil.copyfile(self, os.path.abspath(path))
        return self

    def newcopyto(self, directory: Dir) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns the new File."""
        parent = self.settings.dirclass.from_pathlike(directory, settings=self.settings)
        parent._bind(self)
        return parent.files[self.name]

    def copyto(self, directory: Dir) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns self."""
        self.newcopyto(directory)
        return self

    def move(self, path: PathLike) -> File:
        """Move this this File to the specified path. Returns self."""
        self._validate(path)
        self._set_params(path)
        return self

    def moveto(self, directory: Dir) -> File:
        """Move this File to the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns self."""
        self.dirclass.from_pathlike(directory, settings=self.settings)._bind(self, preserve_original=False)
        return self

    def delete(self, backup: bool = False) -> File:
        """Delete this File's object's mapped file from the file system. The File object will persist and may still be used."""
        if backup:
            self.read()

        os.remove(self)
        return self

    def recover(self) -> File:
        """Attempt to reconstruct the file represented by this File object from its attributes after it has been deleted from the file system."""
        self._prepare_file_if_not_exists(self)
        self.contents = self._contents
        return self

    @classmethod
    def from_main(cls, settings: Settings = None) -> File:
        return cls(sys.modules["__main__"].__file__, settings=settings)

    @classmethod
    def from_resource(cls, package: ModuleType, name: str, extension: str = None, settings: Settings = None) -> File:
        from .dir import Dir
        return Dir.from_package(package, settings=settings).newfile(name=name, extension=extension)

    def _set_params(self, path: PathLike, move: bool = True) -> None:
        path_obj = pathlib.Path(os.path.abspath(path))

        name, new_dirpath = os.path.basename(path_obj), os.path.dirname(path_obj)
        prename, extension = os.path.splitext(name)
        directory = None if self._dir is None else (self.settings.dirclass(new_dirpath, settings=self.settings) if self.dir != new_dirpath else self.dir)

        if move:
            shutil.move(self, path_obj)

        self._path, self._dir, self._name, self._prename, self._extension = path_obj, directory, name, prename, extension.strip(".").lower()
