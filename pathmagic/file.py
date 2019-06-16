from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tarfile
import zipfile
from datetime import datetime as dt
from typing import Any, Type, TYPE_CHECKING

from maybe import Maybe
from subtypes import Str

from .basepath import BasePath, PathLike
from .formats import FormatHandler

if TYPE_CHECKING:
    from .dir import Dir


class File(BasePath):
    """
    ORM class for manipulating files in the filesystem.

    Item access can be used to retrieve, set and delete the lines in the file. The len() represents the number of lines, the str() returns the file's path,
    the bool() resolves to true if the file is not empty, and iteration yields one line at a time. Changes to any object property (setting it) will be reflected in the file system.

    The file's name, prename (name without extension), extension, directory (as a Dir object), path (as a string) are properties that will cause the relevant changes in the
    filesystem when set. The safemode attribute prevents overwriting other files with this one when moving this file around the filesystem using its properties and methods.
    """

    def __init__(self, path: PathLike, safemode: bool = True, force_read: bool = False, dirclass: Type[Dir] = None) -> None:
        self._path = self._name = self._prename = self._extension = None  # type: str
        self._contents: Any = None
        path, self.safe, self.force_read, self._format = os.path.realpath(path), safemode, force_read, FormatHandler(self)

        self._dir: Dir = None
        self._set_dir_constructor(dirclass)

        self._prepare_file_if_not_exists(path)
        self._set_params(path)

        self._created = os.path.getctime(self.path)
        self._modified = os.path.getmtime(self.path)

    def __repr__(self) -> str:
        return f"{type(self).__name__}(path={repr(self.path)}, lines={len(self) or '?'})"

    def __len__(self) -> int:
        if self.extension not in self._format.formats and not zipfile.is_zipfile(self.path) and not tarfile.is_tarfile(self.path):
            self._synchronize()

        return 0 if not isinstance(self._contents, str) else self.contents.count("\n") + 1

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
    def path(self) -> str:
        """Return or set the File's full path as a string. Implicitly calls the 'move' method."""
        return self._path

    @path.setter
    def path(self, val: str) -> None:
        self.move(val)

    @property
    def dir(self) -> Dir:
        """Return or set the File's directory as a Dir object. Implicitly calls that Dir object's 'bind' method."""
        from .dir import Dir

        if self._dir is None:
            self._dir = Dir(os.path.dirname(self.path))
        return self._dir

    @dir.setter
    def dir(self, val: Dir) -> None:
        val._bind(self, preserve_original=False)

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

    @property
    def created(self) -> dt:
        """Return the File's created_time. Read-only."""
        return dt.fromtimestamp(self._created)

    @property
    def modified(self) -> dt:
        """Return the File's last_modified_time. Read-only."""
        self._synchronize()
        return dt.fromtimestamp(self._modified)

    def read(self, **kwargs: Any) -> str:
        """
        Return the File's contents as a string if it is not encoded, else attempt to return a useful Python object representing the file contents (e.g. Pandas DataFrame for tabular files, etc.).
        If provided, *args and **kwargs will be passed on to whichever function will be used to read in the File's contents. Call the 'readhelp' method for that function's documentation.
        This method is lazy by default and will usually only perform a true I/O read if the File object's last_modified_time has fallen out of sync with the file's last_modified_time
        in the file system. This may cause errors when other applications programmatically set the file's contents during this object's lifetime without updating the OS file metadata.
        Such issues can be avoided by setting the File's 'force_read' attribute to True, at the expense of additional I/O.
        """
        self._synchronize(**kwargs)
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
            os.startfile(self.path, "open")
        else:
            with subprocess.Popen([app, self.path]):
                pass
        return self

    def opendir(self) -> File:
        """Call the default file system navigator on this File's directory. Returns self."""
        self.dir.open()
        return self

    def rename(self, name: str, extension: str = None) -> File:
        """Rename this File to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns self."""
        self._set_name(f"{name}{('.' + Maybe(extension)).else_('')}")
        return self

    def newrename(self, name: str, extension: str = None) -> File:
        """Rename a new copy of this File in-place to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns the copy."""
        return self.newcopy(os.path.join(self.dir.path, f"{name}{('.' + Maybe(extension)).else_('')}"))

    def newcopy(self, path: str) -> File:
        """Create a new copy of this File at the specified path. Returns the new File."""
        self.copy(path)
        return type(self)(path)

    def copy(self, path: str) -> File:
        """Create a new copy of this File at the specified path. Returns self."""
        path = os.path.realpath(path)

        try:
            self._validate(path)
        except FileExistsError:
            pass
        else:
            shutil.copyfile(self.path, path)

        return self

    def newcopyto(self, directory: Dir) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns the new File."""
        directory._bind(self)
        return directory.files[self.name]

    def copyto(self, directory: Dir) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns self."""
        directory._bind(self)
        return self

    def move(self, path: str) -> File:
        """Move this this File to the specified path. Returns self."""
        self._validate(path)
        self._set_params(path, move=True)
        return self

    def moveto(self, directory: Dir) -> File:
        """Move this File to the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns self."""
        directory._bind(self, preserve_original=False)
        return self

    def setsafemode(self, safemode: bool) -> File:
        """Set this File's 'safe' attribute to the specified boolean value. Returns self and thus allows chaining."""
        self.safe = safemode
        return self

    def delete(self, backup: bool = False) -> None:
        """Delete this File's object's mapped file from the file system. The File object will persist and may still be used."""
        if backup:
            self._synchronize()
        os.remove(self.path)

    def recover(self) -> File:
        """Attempt to reconstruct the file represented by this File object from its attributes after it has been deleted from the file system."""
        self._prepare_file_if_not_exists(self.path)
        self.contents = self.contents
        return self

    @classmethod
    def from_main(cls, *args: Any, **kwargs: Any) -> File:
        return cls(sys.modules['__main__'].__file__, *args, **kwargs)

    def _synchronize(self, **kwargs: Any) -> None:
        real_lmd = os.path.getmtime(self._path)
        if self.force_read or self._contents is None or not self._modified == real_lmd or kwargs:
            self._contents = self._format.read(**kwargs)
            self._modified = real_lmd

    def _set_dir_constructor(self, dirclass: Type[Dir]) -> None:
        from .dir import Dir
        self.dirclass = Maybe(dirclass).else_(Dir)

    def _set_params(self, path: str, move: bool = False) -> None:
        from .dir import Dir

        name = os.path.basename(path)
        new_dirpath = os.path.dirname(path)
        directory = None if self._dir is None else (Dir(new_dirpath) if self.dir.path != new_dirpath else self.dir)

        if move:
            shutil.move(self.path, path)

        self._path, self._dir = path, directory
        self._set_name(name, rename=False)

    def _set_name(self, name: str, rename: bool = True) -> None:
        if name.endswith("."):
            raise ValueError(f"Filename '{name}' may not end with '.'")

        prename = name if not name.count(".") else Str(name).before_last(r"\.")
        extension = Str(name).after_last(r"\.").lower() if name.count(".") else None

        if rename:
            path = os.path.join(os.path.dirname(self.path), name)
            os.rename(self._path, path)
            self._path = path

        self._name, self._prename, self._extension = name, prename, extension
