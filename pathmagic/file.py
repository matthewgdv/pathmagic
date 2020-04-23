from __future__ import annotations

import os
import shutil
import sys
import zipfile
from typing import Any, Iterator, TYPE_CHECKING, Optional
from types import ModuleType
import pathlib

from maybe import Maybe
from subtypes import Process

from .path import Path, PathLike, Settings
from .formats import FormatHandler, Default

if TYPE_CHECKING:
    from .dir import Dir


class File(Path):
    """
    ORM class for manipulating files in the filesystem.

    Item access can be used to retrieve, set and delete the lines in the file. The len() represents the number of lines, the str() returns the file's path,
    the bool() resolves to true if the file is not empty, and iteration yields one line at a time. Changes to any object property (setting it) will be reflected in the file system.

    The object's File.name, File.stem (name without extension), File.extension, File.parent (as a Dir object), File.path (as a pathlib.Path) are properties that will cause the relevant changes in the
    filesystem when set.
    """

    def __init__(self, path: PathLike, settings: Settings = None) -> None:
        self._path: Optional[pathlib.Path] = None
        self._content: Any = None
        self._parent: Optional[Dir] = None

        self.settings = settings or self.Settings()

        self._set_params(path, move=False)
        self.create()

        self._format_handler = FormatHandler(self)

    def __repr__(self) -> str:
        try:
            return f"{type(self).__name__}(path={repr(self.path)}, lines={len(self) or '?'})"
        except FileNotFoundError:
            return f"{type(self).__name__}(path={repr(self.path)}, deleted=True, lines=?)"

    def __len__(self) -> int:
        if isinstance(self._format_handler.format, Default):
            self.read()

        return 0 if not isinstance(self._content, str) else self._content.count("\n") + 1

    def __bool__(self) -> bool:
        return True if os.path.getsize(self) > 0 else False

    def __iter__(self) -> Iterator[str]:
        return iter(self.content.split("\n"))

    def __getitem__(self, key: int) -> str:
        return str(self.content.split("\n")[key])

    def __setitem__(self, key: int, val: str) -> None:
        aslist = self.content.split("\n")
        aslist[key] = val
        self.write("\n".join(aslist))

    def __delitem__(self, key: int) -> None:
        aslist = self.content.split("\n")
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
    def parent(self) -> Dir:
        """Return or set the File's directory as a Dir object. Implicitly calls that Dir object's 'bind' method."""
        if self._parent is None:
            self._parent = self.settings.dir_class(os.path.dirname(self), settings=self.settings)
        return self._parent

    @parent.setter
    def parent(self, val: Dir) -> None:
        self.settings.dir_class.from_pathlike(val, settings=self.settings)._bind(self, preserve_original=False)

    @property
    def name(self) -> str:
        """Return or set the File's full name, including extension. Implicitly calls the 'rename' method."""
        return self.path.name

    @name.setter
    def name(self, val: str) -> None:
        self.rename(name=val)

    @property
    def stem(self) -> str:
        """Return or set the File's name up to the extension. Implicitly calls the 'rename' method."""
        return self.path.stem

    @stem.setter
    def stem(self, val: str) -> None:
        self.rename(name=val, extension=self.extension)

    @property
    def extension(self) -> str:
        """Return or set the File's extension. Is always saved and returned as lower-cased regardless of how the filename is cased. Implicitly calls the 'rename' method."""
        return self.path.suffix.strip(".").lower()

    @extension.setter
    def extension(self, val: str) -> None:
        if not ((val.startswith(".") and val.count(".") == 1) or val.count(".") == 0):
            raise ValueError(f"Too many '.' in extension name '{val}', or '.' not at start of string. 1 or 0 allowed. If 0, '.' will be set implicitly.")

        self.rename(name=self.stem, extension=val)

    @property
    def content(self) -> Any:
        """
        Return or set the File's content. Implicitly calls the 'read' and 'write' methods on assignment.
        When appending text to large textual files, use the 'append' method rather than '+=' operator on this property to avoid unnecessary I/O.
        """
        return self.read()

    @content.setter
    def content(self, val: Any) -> None:
        self.write(val)

    def read(self, **kwargs: Any) -> Any:
        """
        Return the File's content as a string if it is not encoded, else attempt to return a useful Python object representing the file content (e.g. Pandas DataFrame for tabular files, etc.).
        If provided, **kwargs will be passed on to whichever function will be used to read in the File's content. Call the 'readhelp' method for that function's documentation.
        """
        self._content = self._format_handler.read(**kwargs)
        return self._content

    def read_help(self) -> None:
        """
        Print help documentation for the underlying reader function that is implicitly called when reading from this file type or accessing the 'content' property.
        Any '**kwargs' passed to this File's 'read' method will be passed on to the underlying reader function. Do not resupply this File's path as a kwarg.
        """
        self._format_handler.read_help()

    def write(self, val: Any, **kwargs: Any) -> File:
        """Write to this File object's mapped file, overwriting anything already there. Returns self."""
        self._format_handler.write(item=val, **kwargs)
        return self

    def write_help(self) -> None:
        """
        Print help documentation for the underlying writer function that is implicitly called when writing to this file type or setting to the 'content' property.
        Any '**kwargs' passed to this File's 'write' method will be passed on to the underlying writer function. Do not resupply this File's path as a kwarg.
        """
        self._format_handler.write_help()

    def append(self, val: str) -> File:
        """Write to the end of this File object's mapped file, leaving any existing text intact. Returns self."""
        self._format_handler.append(text=val)
        return self

    def start(self, app: str = None, print_call: bool = False) -> File:
        """Call the default application associated with this File's extension type on its own path. If an application is specified, open it with that instead. Returns self."""
        if app is None:
            os.startfile(self)
        else:
            Process([app, self], print_call=print_call).wait()

        return self

    def rename(self, name: str, extension: str = None) -> File:
        """Rename this File to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns self."""
        self._set_params(self.parent.path.joinpath(f"{name}{self._clean_extension(extension)}"), move=True)
        return self

    def new_rename(self, name: str, extension: str = None) -> File:
        """Rename a new copy of this File in-place to the specified value. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns the copy."""
        return self.new_copy(self.parent.path.joinpath(f"{name}{self._clean_extension(extension)}"))

    def new_copy(self, path: PathLike) -> File:
        """Create a new copy of this File at the specified path. Returns the new File."""
        self.copy(path)
        return self.settings.file_class(path, settings=self.settings)

    def copy(self, path: PathLike) -> File:
        """Create a new copy of this File at the specified path. Returns self."""
        self._validate(path)
        shutil.copyfile(self, os.path.abspath(path))
        return self

    def new_copy_to(self, directory: PathLike) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns the new File."""
        parent = self.settings.dir_class.from_pathlike(directory, settings=self.settings)
        parent._bind(self)
        return parent.files[self.name]

    def copy_to(self, directory: PathLike) -> File:
        """Create a new copy of this File within the specified Dir object. Implicitly calls that Dir's '_bind' method. Returns self."""
        self.new_copy_to(directory)
        return self

    def move(self, path: PathLike) -> File:
        """Move this this File to the specified path. Returns self."""
        self._validate(path)
        self._set_params(path, move=True)
        return self

    def move_to(self, directory: PathLike) -> File:
        """Move this File to the specified path. If a Dir object is supplied, both objects will be acquire references to one another. Returns self."""
        self.settings.dir_class.from_pathlike(directory, settings=self.settings)._bind(self, preserve_original=False)
        return self

    def create(self) -> File:
        """Create this File in the filesystem if it does not exist. This method is called implicitly during instanciation. Returns self."""
        self._prepare_file_if_not_exists(self.path)
        return self

    def delete(self) -> File:
        """Delete this File object's mapped file from the file system. The File object will persist and may still be used, but the content may not be recoverable."""
        os.remove(str(self))
        return self

    def compress(self, name: str = None, **kwargs: Any) -> File:
        """Compress the content of this file into a '.zip' archive of the chosen name, and place it into this File's parent Dir. Then return that zip File. If no name is given, this File's name will be used (plus '.zip' extension)."""
        outfile: File = self.parent.new_file(f"{Maybe(name).else_(self.name)}.zip")
        with zipfile.ZipFile(outfile, mode="w", compression=zipfile.ZIP_DEFLATED, **kwargs) as zipper:
            zipper.write(self.path, self.name)

        return outfile

    @classmethod
    def from_python(cls, settings: Settings = None) -> File:
        return cls(sys.executable, settings=settings)

    @classmethod
    def from_main(cls, settings: Settings = None) -> File:
        """Create a File representing the '__main__' module's path. This method will fail under circumstances that would cause the '__main__' module's path to be undefined, such as from within jupyter notebooks."""
        return cls(sys.modules["__main__"].__file__, settings=settings)

    @classmethod
    def from_resource(cls, package: ModuleType, name: str, extension: str = None, settings: Settings = None) -> File:
        """Create a File representing a non-python resource file within a python package."""
        from .dir import Dir
        return Dir.from_package(package, settings=settings).new_file(name=name, extension=extension)

    def _set_params(self, path: PathLike, move: bool = True) -> None:
        path_obj = pathlib.Path(os.path.abspath(path))

        if move:
            shutil.move(self, path_obj)

        self._path, self._parent = path_obj, self._parent if self._parent == path_obj.parent else None
