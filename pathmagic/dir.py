from __future__ import annotations

import inspect
import os
import pathlib
import re
import shutil
import subprocess
import zipfile
from datetime import datetime as dt
from typing import Any, Collection, Dict, Iterator, List, Optional, Tuple, Union, cast
from types import ModuleType

from maybe import Maybe
from subtypes import Str

from .accessor import FileAccessor, DirAccessor, FileDotAccessor, DirDotAccessor
from .basepath import BasePath, PathLike, Settings
from .file import File


class Dir(BasePath):
    """
    ORM class for manipulating directories in the filesystem.

    Item access can be used on the accessor objects bound to the 'files' and 'dirs' attributes, and restrict their output to the corresponding type of path object.
    These accessors can be called to produce a list of the File or Dir names within this Dir object, respectively. Or they can be iterated over to yield the actual objects.

    The len() represents the number of combined files and dirs, the str() returns the Dir's path, the bool() resolves to true if the Dir is not empty, and iteration yields the paths
    of all the contained File and Dir objects, one at a time. Changes to any object property (setting it) will be reflected in the file system.

    The 'if_exists' attribute contols behaviour when copying or moving files into paths with existing file system objects, while using this object's properties and methods. The options
    are listed in this class' 'IfExists' enumeration.
    """

    def __init__(self, path: PathLike = "", settings: Settings = None) -> None:
        self._path = self._name = None  # type: str
        self._dir: Dir = None

        self.settings = Maybe(settings).else_(Settings())
        path = os.path.realpath(path)

        self._prepare_dir_if_not_exists(path)
        self._set_params(path, move=False)

        self._files: Dict[str, Optional[File]] = {item.name: None for item in os.scandir(self.path) if item.is_file()}
        self._dirs: Dict[str, Optional[Dir]] = {item.name: None for item in os.scandir(self.path) if item.is_dir()}
        self.files, self.dirs = FileAccessor(self), DirAccessor(self)

        self.f, self.d = FileDotAccessor(self.files), DirDotAccessor(self.dirs)
        self.f._acquire(list(self._files))
        self.d._acquire(list(self._dirs))

        self._created = os.path.getctime(self.path)
        self._modified = os.path.getmtime(self.path)

    def __repr__(self) -> str:
        try:
            return f"{type(self).__name__}(path={repr(self.path)}, files={len(self.files())}, dirs={len(self.dirs())})"
        except FileNotFoundError:
            return f"{type(self).__name__}(path={repr(self.path)}, deleted=True, files=?, dirs=?)"

    def __call__(self, full_path: bool = False) -> List[str]:
        return sum([accessor(full_path=full_path) for accessor in (self.files, self.dirs)], [])

    def __len__(self) -> int:
        return len(self.files()) + len(self.dirs())

    def __bool__(self) -> bool:
        return True if len(self) else False

    def __iter__(self) -> Dir:
        self.__iter = (pathlike for generator in (iter(self.dirs), iter(self.files)) for pathlike in generator)
        return self

    def __next__(self) -> Union[File, Dir]:
        return next(self.__iter)

    @property
    def path(self) -> str:
        """Return or set the Dir's full path as a string. Implicitly calls the 'move' method."""
        return self._path

    @path.setter
    def path(self, val: str) -> None:
        self.move(val)

    @property
    def dir(self) -> Dir:
        """Return or set the Dir's directory as a Dir object. Implicitly calls that Dir object's '_bind' method."""
        if self._dir is None:
            self._dir = self.settings.dirclass(os.path.dirname(self.path), settings=self.settings)
        return self._dir

    @dir.setter
    def dir(self, val: Dir) -> None:
        self.dirclass(val)._bind(self, preserve_original=False)

    @property
    def name(self) -> str:
        """Return or set the Dir's name. Implicitly calls the rename method."""
        return self._name

    @name.setter
    def name(self, val: str) -> None:
        self.rename(val)

    @property
    def contents(self) -> dict:
        """Return the Dir's contents as a dictionary with two keys, 'files', and 'dirs', which contain a list of the names of the files and dirs in this Dir, respectively. Read-only."""
        return {"files": self.files(), "dirs": self.dirs()}

    @property
    def created(self) -> dt:
        """Return the Dir's created_time. Read-only."""
        return dt.fromtimestamp(self._created)

    @property
    def modified(self) -> dt:
        """Return the Dir's last_modified_time. Read-only."""
        self._modified = os.path.getmtime(self.path)
        return dt.fromtimestamp(self._modified)

    def open(self) -> Dir:
        """Call the default file system navigator on this Dir's path. Returns self."""
        with subprocess.Popen(["explorer", self.path]):
            pass
        return self

    def opendir(self) -> Dir:
        """Call the default file system navigator on this Dir's directory. Returns self."""
        self.dir.open()
        return self

    def rename(self, name: str) -> Dir:
        """Rename this Dir to the specified value. Returns self."""
        newpath = os.path.join(self.dir.path, name)
        os.rename(self._path, newpath)
        self._name, self._path = name, newpath
        return self

    def newrename(self, name: str) -> Dir:
        """Rename a new copy of this Dir in-place to the specified value. Returns the copy."""
        return self.newcopy(os.path.join(self.dir.path, name))

    def newcopy(self, path: PathLike) -> Dir:
        """Create a new copy of this Dir at the specified path. Returns the copy."""
        self.copy(path)
        return self.settings.dirclass(path, settings=self.settings)

    def copy(self, path: PathLike) -> Dir:
        """Create a new copy of this Dir at the specified path. Returns self."""
        path = os.path.realpath(path)

        self._validate(path)
        shutil.copytree(self.path, path)

        return self

    def newcopyto(self, directory: PathLike) -> Dir:
        """Create a new copy of this Dir within the specified path. If passed an existing Dir, both objects will implicitly call acquire references to each other. Otherwise it will instantiate a new Dir first. Returns the copy."""
        parent = self.dirclass.from_pathlike(directory, settings=self.settings)
        parent._bind(self, validate=True)
        return parent.dirs[self.name]

    def copyto(self, directory: PathLike) -> Dir:
        """Create a new copy of this Dir within the specified path. If passed an existing Dir, both objects will implicitly call acquire references to each other. Otherwise it will instantiate a new Dir first. Returns self."""
        self.dirclass.from_pathlike(directory, settings=self.settings)._bind(self, validate=True)
        return self

    def move(self, path: PathLike) -> Dir:
        """Move this this Dir to the specified path. Returns self."""
        path = os.path.realpath(path)
        self._validate(path)
        self._set_params(path)
        return self

    def moveto(self, directory: PathLike) -> Dir:
        """Move this Dir to the specified Dir object. If passed an existing Dir, both objects will implicitly call acquire references to each other. Returns self."""
        self.dirclass.from_pathlike(directory, settings=self.settings)._bind(self, preserve_original=False, validate=True)
        return self

    def delete(self) -> Dir:
        """Delete this Dir object's mapped directory from the file system. The Dir object will persist and may still be used."""
        shutil.rmtree(self._path)
        return self

    def clear(self) -> Dir:
        """Delete all files and directories contained within this Dir."""
        for pathlike in self:
            pathlike.delete()
        return self

    def makefile(self, name: str, extension: str = None) -> Dir:
        """Instantiate a new File with the specified name within this Dir. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns self."""
        newpath = os.path.join(self.path, f"{name}{('.' + Maybe(extension)).else_('')}")
        self._prepare_file_if_not_exists(newpath)
        return self

    def newfile(self, name: str, extension: str = None) -> File:
        """Instantiate a new File with the specified name within this Dir. If 'extension' is specified, it will be appended to 'name' with a dot as a separator. Returns that File."""
        name = f"{name}{('.' + Maybe(extension)).else_('')}"
        self._bind(self.settings.fileclass(os.path.join(self.path, name), settings=self.settings))
        return self._files[name]

    def makedir(self, name: str) -> Dir:
        """Instantiate a new Dir with the specified name within this Dir. Returns self."""
        newpath = os.path.join(self.path, name)
        self._prepare_dir_if_not_exists(newpath)
        return self

    def newdir(self, name: str) -> Dir:
        """Instantiate a new Dir with the specified name within this Dir. Returns that Dir."""
        self._bind(self.settings.dirclass(os.path.join(self.path, name), settings=self.settings))
        return self._dirs[name]

    def joinfile(self, path: PathLike) -> File:
        return self.settings.fileclass(pathlib.Path(self).joinpath(path), settings=self.settings)

    def joindir(self, path: PathLike) -> Dir:
        return self.settings.dirclass(pathlib.Path(self).joinpath(path), settings=self.settings)

    def symlink_to(self, target: PathLike, name: str = None, target_is_directory: bool = True) -> None:
        link = (self.newdir if target_is_directory else self.newfile)(Maybe(name).else_(os.path.basename(target))).delete()
        pathlib.Path(link).symlink_to(target=target, target_is_directory=target_is_directory)

    def seekfiles(self, depth: int = None, name: str = None, dirpath: str = None, contents: str = None, extensions: Collection[str] = None, re_flags: int = 0) -> Iterator[File]:
        """
        Iterate recursively over the File objects within this Dir and all sub-Dirs, returning those that match all the regex patterns provided and have the correct extension.
        If the 'contents' argument is provided, any File with contents that is encoded in any way or is not 'string-like' will be considered invalid and will not be returned.
        Any arguments left as 'None' automatically pass. This means that if no arguments are provided, every single File within this Dir's directory tree is valid to be returned.
        A maximal recursion depth may optionally be specified. At '0' only local Files may be returned, any Files within one level of subdirectories at '1', etc. Fully recursive if left 'None'.
        """

        for file in self.files:
            if (
                (extensions is None or file.extension in extensions)
                and (name is None or Str(file.prename).search(name, flags=re_flags))
                and (dirpath is None or Str(self.path).search(dirpath, flags=re_flags))
                and (contents is None or (len(file) > 0 and Str(file.contents).search(contents, flags=re_flags)))
            ):
                yield file

        if depth is not None:
            if depth <= 0:
                return
            else:
                depth -= 1

        for directory in self.dirs:
            yield from directory.seekfiles(depth=depth, name=name, dirpath=dirpath, contents=contents, extensions=extensions, re_flags=re_flags)

    def seekdirs(self, depth: int = None, name: str = None, dirpath: str = None, contains_filename: str = None, contains_dirname: str = None, re_flags: int = 0) -> Iterator[Dir]:
        """
        Iterate recursively over the Dir objects within this Dir and all sub-Dirs, returning those that match all the regex patterns provided. This Dir will never be returned.
        Any arguments left as 'None' automatically pass. This means that if no arguments are provided, every single Dir within this Dir's directory tree is valid to be returned.
        A maximal recursion depth may optionally be specified. At '0' only local Dirs may be returned, any Dirs within one level of subdirectories at '1', etc. Fully recursive if left 'None'.
        """

        for directory in self.dirs:
            if (
                (name is None or Str(directory.name).search(name, flags=re_flags))
                and (dirpath is None or Str(self.path).search(dirpath, flags=re_flags))
                and (contains_filename is None or any([Str(file.name).search(contains_filename, flags=re_flags) is not None for file in directory.files]))
                and (contains_dirname is None or any([Str(subdir.name).search(contains_dirname, flags=re_flags) is not None for subdir in directory.dirs]))
            ):
                yield directory

        if depth is not None:
            if depth <= 0:
                return
            else:
                depth -= 1

        for directory in self.dirs:
            yield from directory.seekdirs(depth=depth, name=name, dirpath=dirpath, contains_filename=contains_filename, contains_dirname=contains_dirname, re_flags=re_flags)

    def walk(self, depth: int = None) -> Iterator[Tuple[Dir, DirAccessor, FileAccessor]]:
        """Iterate recursively over this Dir and all subdirs, yielding a 3-tuple of: Tuple[directory, directory.dirs, directory.files]."""
        yield self, self.dirs, self.files
        yield from ((directory, directory.dirs, directory.files) for directory in self.seekdirs(depth=depth))

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
        The shape of the tuples is: Tuple[Tuple[self_dir, other_dir], Generator[Tuple[self_file, other_file]]]]
        """
        yield (self, other), self.compare_files(other, include_unmatched=include_unmatched)
        for directory in self.dirs:
            if directory.name in other.dirs():
                yield from directory.compare_tree(other.dirs[directory.name])

        if include_unmatched:
            yield from (((directory, None), iter([])) for directory in self.dirs if directory.name not in other.dirs())
            yield from (((None, directory), iter([])) for directory in other.dirs if directory.name not in self.dirs())

    def compress(self, name: str = None, **kwargs: Any) -> File:
        """Compress the contents of this dir into a '.zip' archive of the chosen name, and place it into this Dir's parent Dir. Then return that zip File. If no name is given, this Dir's name will be used (plus '.zip' extension)."""
        outfile: File = self.dir.newfile(f"{Maybe(name).else_(self.name)}.zip")
        with zipfile.ZipFile(outfile.path, mode="w", compression=zipfile.ZIP_DEFLATED, **kwargs) as zipper:
            for directory, dirs, files in self.walk():
                for path in (item for itemtype in (dirs, files) for item in cast(Iterator, itemtype)):
                    zipper.write(path.path, path.path[len(self.path)+1:])

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
        return cls(pathlib.Path.home(), settings=settings)

    @classmethod
    def from_desktop(cls, settings: Settings = None) -> Dir:
        return cls.from_home(settings=settings).d.desktop

    @classmethod
    def from_package(cls, package: ModuleType, settings: Settings = None) -> Dir:
        loc, = package.__spec__.submodule_search_locations
        return cls(loc, settings=settings)

    def _bind(self, existing_object: Union[File, Dir], preserve_original: bool = True, validate: bool = False) -> None:
        """
        Acquire a reference to the specified File or Dir in this object's 'files' or 'dirs' property, and in return provide that object a reference to this Dir as its 'dir' property.
        The target File or Dir will be copied and placed in this Dir if the 'preserve_original' argument is true, otherwise it will be moved instead.
        """
        if os.path.dirname(existing_object.path) == self.path:
            if validate:
                self._validate(existing_object.path)
            else:
                unbound = existing_object
        else:
            unbound = (existing_object.newcopy if preserve_original else existing_object.move)(os.path.join(self.path, existing_object.name))
        unbound._dir = self

        mro = inspect.getmro(type(unbound))

        if File in mro and Dir in mro:
            raise TypeError(f"Objects to bind must be {File.__name__} or {Dir.__name__} (or some subclass), but may not inherit from both.")
        elif File in mro:
            self._files[unbound.name] = unbound
        elif Dir in mro:
            self._dirs[unbound.name] = unbound
        else:
            raise TypeError(f"Objects to bind must be {File.__name__} or {Dir.__name__} (or some subclass), not {type(existing_object).__name__}")

    def _synchronize_files(self) -> None:
        realfiles = [item.name for item in os.scandir(self.path) if item.is_file()]
        self._files = {name: self._files.get(name) for name in realfiles}
        self.f._acquire(realfiles)

    def _synchronize_dirs(self) -> None:
        realdirs = [item.name for item in os.scandir(self.path) if item.is_dir()]
        self._dirs = {name: self._dirs.get(name) for name in realdirs}
        self.d._acquire(realdirs)

    def _access_files(self, name: str) -> File:
        if name not in self._files:
            self._synchronize_files()
        if name in self._files:
            return Maybe(self._files[name]).else_(self.newfile(name))
        else:
            raise FileNotFoundError(f"File '{name}' not found in '{self}'")

    def _access_dirs(self, name: str) -> Dir:
        if name not in self._dirs:
            self._synchronize_dirs()
        if name in self._dirs:
            return Maybe(self._dirs[name]).else_(self.newdir(name))
        else:
            raise FileNotFoundError(f"Dir '{name}' not found in '{self}'")

    def _set_params(self, path: str, move: bool = True) -> None:
        name, new_dirpath = os.path.basename(path), os.path.dirname(path)
        directory = None if self._dir is None else (self.settings.dirclass(new_dirpath, settings=self.settings) if self.dir.path != new_dirpath else self.dir)

        if move:
            shutil.move(self.path, path)

        self._path, self._name, self._dir = path, name, directory

    def _visualize_tree(self, outlist: List[str], depth: int = None, padding: str = " ",
                        file_inclusion: str = None, file_exclusion: str = None, dir_inclusion: str = None, dir_exclusion: str = None) -> None:

        for filename in self.files():
            if (file_inclusion is None or re.search(file_inclusion, filename) is not None) and (file_exclusion is None or re.search(file_exclusion, filename) is None):
                outlist.append(f"{padding} |")
                outlist.append(f"{padding} +--{filename}")

        dirs = [folder for folder in self.dirs
                if (dir_inclusion is None or re.search(dir_inclusion, folder.name) is not None)
                and (dir_exclusion is None or re.search(dir_exclusion, folder.name) is None)]

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
