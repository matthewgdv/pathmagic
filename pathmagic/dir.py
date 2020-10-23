from __future__ import annotations

from contextlib import contextmanager
import os
import sys
import pathlib
import shutil
import zipfile
from tempfile import gettempdir
from typing import Any, Collection, Dict, Iterator, List, Optional, Tuple, Union, cast
from types import ModuleType

from appdirs import user_data_dir, site_data_dir

from maybe import Maybe
from subtypes import Str

from .accessor import FileAccessor, DirAccessor, FileDotAccessor, DirDotAccessor
from .path import Path, PathLike, Settings, is_running_in_ipython
from .file import File


class Dir(Path):
    """
    ORM class for manipulating directories in the filesystem.

    Item access can be used on the accessor objects bound to the 'files' and 'dirs' attributes, and restrict their output to the corresponding type of path object.
    These accessors can be called to produce a list of the File or Dir names within this Dir object, respectively. Or they can be iterated over to yield the actual objects.

    The len() represents the number of combined files and dirs, the str() returns the Dir's path, the bool() resolves to true if the Dir is not empty, and iteration yields the paths
    of all the contained File and Dir objects, one at a time. Changes to any object property (setting it) will be reflected in the file system.
    """

    def __init__(self, path: PathLike = "", settings: Settings = None) -> None:
        self._path: Optional[pathlib.Path] = None
        self._parent: Optional[Dir] = None
        self._files: dict[str, Optional[File]] = {}
        self._dirs: dict[str, Optional[Dir]] = {}
        self._cwd_stack = []
        self._forbidden = False

        self.settings = settings or self.Settings()

        self._set_params(path, move=False)
        self.create()

        self.files, self.dirs = FileAccessor(self), DirAccessor(self)
        self.f, self.d = FileDotAccessor(self.files), DirDotAccessor(self.dirs)
        self._synchronize_files(), self._synchronize_dirs()

    def __repr__(self) -> str:
        try:
            if not self._forbidden:
                return f"{type(self).__name__}(path={repr(self.path)}, files={len(self.files)}, dirs={len(self.dirs)})"
            else:
                return f"{type(self).__name__}(path={repr(self.path)}, forbidden=True)"
        except FileNotFoundError:
            return f"{type(self).__name__}(path={repr(self.path)}, deleted=True)"

    def __call__(self, full_path: bool = False) -> list[str]:
        return sum([accessor(full_path=full_path) for accessor in (self.files, self.dirs)], [])

    def __len__(self) -> int:
        return len(self.files()) + len(self.dirs())

    def __bool__(self) -> bool:
        return True if len(self) else False

    def __getitem__(self, levels: int) -> Dir:
        ret = self
        for level in range(levels):
            ret = ret.parent
        return ret

    def __iter__(self) -> Iterator[Union[File, Dir]]:
        return (pathlike for generator in (iter(self.dirs), iter(self.files)) for pathlike in generator)

    def __enter__(self) -> Dir:
        self._cwd_stack.append(os.getcwd())
        os.chdir(str(self))
        return self

    def __exit__(self, ex_type: Any, ex_value: Any, ex_traceback: Any) -> None:
        os.chdir(self._cwd_stack.pop(-1))

    @property
    def path(self) -> pathlib.Path:
        """Return or set the Dir's full path as a string. Implicitly calls the 'move' method when set."""
        return self._path

    @path.setter
    def path(self, val: PathLike) -> None:
        self.move(val)

    @property
    def parent(self) -> Dir:
        """Return or set the Dir's parent directory as a Dir object."""
        if self._parent is None:
            self._parent = self.settings.dir_class(os.path.dirname(str(self.path)), settings=self.settings)
        return self._parent

    @parent.setter
    def parent(self, val: Dir) -> None:
        self.settings.dir_class.from_pathlike(val)._bind(self, preserve_original=False)

    @property
    def name(self) -> str:
        """Return or set the Dir's name. Implicitly calls the 'rename' method when set."""
        return self.path.name

    @name.setter
    def name(self, val: str) -> None:
        self.rename(val)

    def start(self) -> Dir:
        """Call the default file system navigator on this Dir's path. Returns self."""
        os.startfile(self)
        return self

    def rename(self, name: str) -> Dir:
        """Rename this Dir to the specified value. Returns self."""
        self._set_params(str(self.parent.path.joinpath(name)))
        return self

    def new_rename(self, name: str) -> Dir:
        """Rename a new copy of this Dir in-place to the specified value. Returns the copy."""
        return self.new_copy(self.parent.path.joinpath(name))

    def new_copy(self, path: PathLike) -> Dir:
        """Create a new copy of this Dir at the specified path. Returns the copy."""
        self.copy(path)
        return self.settings.dir_class(path, settings=self.settings)

    def copy(self, path: PathLike) -> Dir:
        """Create a new copy of this Dir at the specified path. Returns self."""
        self._validate(path)
        shutil.copytree(self, os.path.abspath(path))
        return self

    def new_copy_to(self, directory: PathLike) -> Dir:
        """Create a new copy of this Dir within the specified path. If passed a Dir object, both objects will acquire references to each other. Returns the copy."""
        parent = self.settings.dir_class.from_pathlike(directory, settings=self.settings)
        parent._bind(self, preserve_original=True)
        return parent.dirs[self.name]

    def copy_to(self, directory: PathLike) -> Dir:
        """Create a new copy of this Dir within the specified path. If passed a Dir object, both objects will acquire references to each other. Returns self."""
        self.new_copy_to(directory)
        return self

    def move(self, path: PathLike) -> Dir:
        """Move this this Dir to the specified path. Returns self."""
        self._validate(path)
        self._set_params(path)
        return self

    def move_to(self, directory: PathLike) -> Dir:
        """Move this Dir to the specified path. If passed a Dir object, both objects will acquire references to each other. Returns self."""
        self.settings.dir_class.from_pathlike(directory, settings=self.settings)._bind(self, preserve_original=False)
        return self

    def create(self) -> Dir:
        """Create this Dir in the filesystem if it does not exist. This method is called implicitly during instanciation. Returns self."""
        self._prepare_dir_if_not_exists(self.path)
        return self

    def delete(self) -> Dir:
        """Delete this Dir object's mapped directory from the file system. The Dir object will persist and may still be used, but the content will not be recoverable."""
        shutil.rmtree(self, ignore_errors=True)
        return self

    def clear(self) -> Dir:
        """Delete all files and directories contained within this Dir."""
        for pathlike in self:
            pathlike.delete()

        self._synchronize_files()
        self._synchronize_dirs()

        return self

    def make_file(self, name: str, extension: str = None) -> Dir:
        """Instantiate a new File with the specified name within this Dir. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns self."""
        newpath = self.path.joinpath(f"{name}{('.' + Maybe(extension)).else_('')}")
        self._prepare_file_if_not_exists(newpath)
        return self

    def new_file(self, name: str, extension: str = None) -> File:
        """Instantiate a new File with the specified name within this Dir. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns that File."""
        name = f"{name}{('.' + Maybe(extension)).else_('')}"
        self._bind(self.settings.file_class(self.path.joinpath(name), settings=self.settings), preserve_original=True)
        return self._files[name]

    def make_dir(self, name: str) -> Dir:
        """Instantiate a new Dir with the specified name within this Dir. Returns self."""
        newpath = self.path.joinpath(name)
        self._prepare_dir_if_not_exists(newpath)
        return self

    def new_dir(self, name: str) -> Dir:
        """Instantiate a new Dir with the specified name within this Dir. Returns that Dir."""
        self._bind(self.settings.dir_class(self.path.joinpath(name), settings=self.settings), preserve_original=True)
        return self._dirs[name]

    def join_file(self, path: PathLike) -> File:
        """Join this path to a relative path ending in a file and return that path as a File object."""
        clean = os.fspath(path).strip("\\").strip("/")
        return self.settings.file_class(self.path.joinpath(clean), settings=self.settings)

    def join_dir(self, path: PathLike) -> Dir:
        """Join this path to a relative path ending in a folder and return that path as a Dir object."""
        clean = os.fspath(path).strip("\\").strip("/")
        return self.settings.dir_class(self.path.joinpath(clean), settings=self.settings)

    def symlink_to(self, target: PathLike, name: str = None) -> None:
        """Create a symlink to the given target. If the name of the symlink is not given, the basename of the target will be used. """
        pathlib.Path(self).joinpath(Maybe(name).else_(os.path.basename(target))).symlink_to(target=target, target_is_directory=os.path.isdir(target))

    def seek_files(self, depth: int = None, name: str = None, parent_path: str = None, content: str = None, extensions: Collection[str] = None, re_flags: int = 0) -> Iterator[File]:
        """
        Iterate recursively over the File objects within this Dir and all sub-Dirs, returning those that match all the regex patterns provided and have the correct extension.
        If the 'content' argument is provided, any File with content that is encoded in any way or is not 'string-like' will be considered invalid and will not be returned.
        Any arguments left as 'None' automatically pass. This means that if no arguments are provided, every single File within this Dir's directory tree is valid to be returned.
        A maximal recursion depth may optionally be specified. At '0' only local Files may be returned, any Files within one level of subdirectories at '1', etc. Fully recursive if left 'None'.
        """

        if not (parent_path is None or Str(self).re.search(parent_path, flags=re_flags)):
            return

        for file in self.files:
            if (
                (extensions is None or file.extension in extensions)
                and (name is None or Str(file.stem).re.search(name, flags=re_flags))
                and (content is None or (len(file) > 0 and Str(file.content).re.search(content, flags=re_flags)))
            ):
                yield file

        if depth is not None:
            if depth <= 0:
                return
            else:
                depth -= 1

        for directory in self.dirs:
            yield from directory.seek_files(depth=depth, name=name, parent_path=parent_path, content=content, extensions=extensions, re_flags=re_flags)

    def seek_dirs(self, depth: int = None, name: str = None, parent_path: str = None, contains_filename: str = None, contains_dirname: str = None, re_flags: int = 0) -> Iterator[Dir]:
        """
        Iterate recursively over the Dir objects within this Dir and all sub-Dirs, returning those that match all the regex patterns provided. This Dir will never be returned.
        Any arguments left as 'None' automatically pass. This means that if no arguments are provided, every single Dir within this Dir's directory tree is valid to be returned.
        A maximal recursion depth may optionally be specified. At '0' only local Dirs may be returned, any Dirs within one level of subdirectories at '1', etc. Fully recursive if left 'None'.
        """

        if not (parent_path is None or Str(self).re.search(parent_path, flags=re_flags)):
            return

        for directory in self.dirs:
            if (
                (name is None or Str(directory.name).re.search(name, flags=re_flags))
                and (contains_filename is None or any([Str(file.name).re.search(contains_filename, flags=re_flags) is not None for file in directory.files]))
                and (contains_dirname is None or any([Str(subdir.name).re.search(contains_dirname, flags=re_flags) is not None for subdir in directory.dirs]))
            ):
                yield directory

        if depth is not None:
            if depth <= 0:
                return
            else:
                depth -= 1

        for directory in self.dirs:
            yield from directory.seek_dirs(depth=depth, name=name, parent_path=parent_path, contains_filename=contains_filename, contains_dirname=contains_dirname, re_flags=re_flags)

    def walk(self, depth: int = None) -> Iterator[Tuple[Dir, DirAccessor, FileAccessor]]:
        """Iterate recursively over this Dir and all subdirs, yielding a 3-tuple of: Tuple[directory, directory.dirs, directory.files]."""
        yield self, self.dirs, self.files
        yield from ((directory, directory.dirs, directory.files) for directory in self.seek_dirs(depth=depth))

    def compare_files(self, other: Dir, include_unmatched: bool = False) -> Iterator[Tuple[File, File]]:
        """Yield 2-tuples of all files with matching names and extensions within this Dir, and some 'other' Dir."""
        yield from ((file, other.files[file.name]) for file in self.files if file.name in other.files())

        if include_unmatched:
            yield from ((file, None) for file in self.files if file.name not in other.files())
            yield from ((None, file) for file in other.files if file.name not in self.files())

    def compare_tree(self, other: Dir, include_unmatched: bool = False) -> Iterator[Tuple[Tuple[Dir, Dir], Iterator[Tuple[File, File]]]]:
        """
        Yield a 2-tuple containing a 2-tuple of this dir and some 'other' Dir, and a generator yielding 2-tuples of all files with common names within these two Dirs.
        Then recursively traverse the directory tree of this Dir, yielding similar 2-tuples, so long as the 'other' Dir has a matching directory structure.
        The shape of the tuples is: Tuple[Tuple[self_parent, other_parent], Generator[Tuple[self_file, other_file]]]]
        """
        yield (self, other), self.compare_files(other, include_unmatched=include_unmatched)
        for directory in self.dirs:
            if directory.name in other.dirs():
                yield from directory.compare_tree(other.dirs[directory.name])

        if include_unmatched:
            yield from (((directory, None), iter([])) for directory in self.dirs if directory.name not in other.dirs())
            yield from (((None, directory), iter([])) for directory in other.dirs if directory.name not in self.dirs())

    def compress(self, name: str = None, **kwargs: Any) -> File:
        """Compress the content of this dir into a '.zip' archive of the chosen name, and place it into this Dir's parent Dir. Then return that zip File. If no name is given, this Dir's name will be used (plus '.zip' extension)."""
        outfile: File = self.parent.new_file(f"{Maybe(name).else_(self.name)}.zip")
        with zipfile.ZipFile(outfile, mode="w", compression=zipfile.ZIP_DEFLATED, **kwargs) as zipper:
            for directory, dirs, files in self.walk():
                for path in (item for itemtype in (dirs, files) for item in cast(Iterator, itemtype)):
                    zipper.write(path, str(Str(path).slice.after(Str(self.parent).re.escape())))

        return outfile

    def visualize(self, depth: int = 0, printing: bool = True, file_inclusion: str = None, file_exclusion: str = None,
                  dir_inclusion: str = None, dir_exclusion: str = None) -> Optional[str]:

        outlist = [f"+--{self.name}/"]
        self._visualize_tree(outlist=outlist, depth=depth, file_inclusion=file_inclusion, file_exclusion=file_exclusion, dir_inclusion=dir_inclusion, dir_exclusion=dir_exclusion)
        ascii_tree = "\n".join(outlist)
        if printing:
            print(ascii_tree)
            return None
        else:
            return ascii_tree

    @classmethod
    def from_home(cls, settings: Settings = None) -> Dir:
        """Create a Dir representing the HOME path."""
        return cls(pathlib.Path.home(), settings=settings)

    @classmethod
    def from_desktop(cls, settings: Settings = None) -> Dir:
        """Create a Dir representing the desktop, which must be named 'Desktop' (case-sensitive) and exist within the HOME directory."""
        return cls.from_home(settings=settings).dirs["Desktop"]

    @classmethod
    def from_cwd(cls, settings: Settings = None) -> Dir:
        """Create a Dir representing the current working directory."""
        return cls(os.getcwd(), settings=settings)

    @classmethod
    def from_root(cls, settings: Settings = None) -> Dir:
        """Create a Dir representing the root of the current drive."""
        return cls(pathlib.Path.cwd().drive + os.sep, settings=settings)

    @classmethod
    def from_main(cls, settings: Settings = None) -> Dir:
        """Create a Dir representing the parent of the '__main__' module's path. This method will fail in circumstances where the '__file__' attribute of the '__main__' module is undefined."""
        return cls(File.from_main().parent, settings=settings) if not is_running_in_ipython() else cls(sys.modules["__main__"]._dh[0], settings=settings)

    @classmethod
    def from_package(cls, package: ModuleType, settings: Settings = None) -> Dir:
        """Create a Dir representing a python package."""
        loc, = package.__spec__.submodule_search_locations
        return cls(loc, settings=settings)

    @classmethod
    def from_appdata(cls, app_name: str = None, app_author: str = None, version: str = None, roaming: bool = False, systemwide: bool = False, settings: Settings = None) -> Dir:
        """Create a Dir within an application data storage location appropriate to the operating system in use."""

        try:
            if systemwide:
                return cls(site_data_dir(appname=app_name, appauthor=app_author, version=version), settings=settings)
            else:
                return cls(user_data_dir(appname=app_name, appauthor=app_author, version=version, roaming=roaming), settings=settings)
        except PermissionError:
            root = cls(os.environ["APPDATA"], settings=settings)

            if not app_name:
                return root
            else:
                app_folder = root.new_dir(app_author).new_dir(app_name) if app_author else root.new_dir(app_name)
                return app_folder if not version else app_folder.new_dir(version)

    @classmethod
    @contextmanager
    def temp(cls, settings: Settings = None) -> Dir:
        temp_dir = cls(path=gettempdir(), settings=settings).new_dir("pythontemp").clear()
        try:
            yield temp_dir
        finally:
            try:
                temp_dir.delete()
            except FileNotFoundError:
                pass

    def _bind(self, existing_object: Union[File, Dir], preserve_original: bool = True) -> None:
        """
        Acquire a reference to the specified File or Dir in this object's 'files' or 'dirs' property, and in return provide that object a reference to this Dir as its 'parent' property.
        The target File or Dir will be copied and placed in this Dir if the 'preserve_original' argument is true, otherwise it will be moved instead.
        """
        pathlike = existing_object if self == os.path.dirname(existing_object) else (existing_object.new_copy if preserve_original else existing_object.move)(self.path.joinpath(existing_object.name))
        pathlike._parent = self

        if issubclass(type(pathlike), File) and issubclass(type(pathlike), Dir):
            raise TypeError(f"Objects to bind must be {File.__name__} or {Dir.__name__} (or some subclass), but may not inherit from both.")
        elif issubclass(type(pathlike), File):
            self._files[pathlike.name] = pathlike
        elif issubclass(type(pathlike), Dir):
            self._dirs[pathlike.name] = pathlike
        else:
            raise TypeError(f"Objects to bind must be {File.__name__} or {Dir.__name__} (or some subclass), not {type(existing_object).__name__}")

    def _synchronize_files(self) -> None:
        try:
            real_files = [item.name for item in os.scandir(self) if item.is_file()]
            new_files = {name: self._files.get(name) for name in real_files}
            self._files.clear()
            self._files.update(new_files)
            self.f._acquire(real_files)
        except PermissionError:
            self._forbidden = True

    def _synchronize_dirs(self) -> None:
        try:
            real_dirs = [item.name for item in os.scandir(self) if item.is_dir()]
            new_dirs = {name: self._dirs.get(name) for name in real_dirs}
            self._dirs.clear()
            self._dirs.update(new_dirs)
            self.d._acquire(real_dirs)
        except PermissionError:
            self._forbidden = True

    def _access_files(self, name: str) -> File:
        if name not in self._files:
            self._synchronize_files()
        if name in self._files:
            file = self._files[name]
            return file if file is not None else self.new_file(name)
        else:
            raise FileNotFoundError(f"File '{name}' not found in '{self}'")

    def _access_dirs(self, name: str) -> Dir:
        if name not in self._dirs:
            self._synchronize_dirs()
        if name in self._dirs:
            folder = self._dirs[name]
            return folder if folder is not None else self.new_dir(name)
        else:
            raise FileNotFoundError(f"Dir '{name}' not found in '{self}'")

    def _set_params(self, path: str, move: bool = True) -> None:
        path_obj = pathlib.Path(os.path.abspath(path))

        if move:
            shutil.move(self, path_obj)

        self._path, self._parent = path_obj, self._parent if self._parent == path_obj.parent else None

    def _visualize_tree(self, outlist: list[str], depth: int = None, padding: str = " ",
                        file_inclusion: str = None, file_exclusion: str = None, dir_inclusion: str = None, dir_exclusion: str = None) -> None:

        for filename in self.files():
            if (file_inclusion is None or Str(filename).re.search(file_inclusion) is not None) and (file_exclusion is None or Str(filename).re.search(file_exclusion) is None):
                outlist.append(f"{padding} |")
                outlist.append(f"{padding} +--{filename}")

        dirs = [folder for folder in self.dirs
                if (dir_inclusion is None or Str(folder.name).re.search(dir_inclusion) is not None)
                and (dir_exclusion is None or Str(folder.name).re.search(dir_exclusion) is None)]

        if depth is not None:
            if depth <= 0:
                for folder in dirs:
                    outlist.append(f"{padding} |")
                    outlist.append(f"{padding} +--{folder.name}/")
                return
            else:
                depth -= 1

        if len(dirs) > 0:
            for index, folder in enumerate(dirs):
                outlist.append(f"{padding} |")
                outlist.append(f"{padding} +--{folder.name}/")
                folder._visualize_tree(outlist=outlist, depth=depth, padding=f"{padding} {'|' if not index + 1 == len(dirs) else ''}",
                                       file_inclusion=file_inclusion, file_exclusion=file_exclusion, dir_inclusion=dir_inclusion, dir_exclusion=dir_exclusion)
