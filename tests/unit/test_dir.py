import os
import tempfile
from pathlib import Path

import appdirs
from pathmagic import Dir, File

from tests.conftest import untestable, unnecessary


class TestDir:
    def test___len__(self, temp_dir: Dir):  # synced
        assert len(temp_dir) == 0
        temp_dir.make_dir('temp')
        assert len(temp_dir) == 1

    def test___bool__(self, temp_dir: Dir):  # synced
        assert not temp_dir
        temp_dir.new_file('test', 'json')
        assert temp_dir

    def test___getitem__(self, temp_root: Dir, temp_dir: Dir):  # synced
        assert temp_dir[1] is temp_root

    def test___iter__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        dir, file, = list(temp_root)
        assert dir == temp_dir and file == temp_file

    @untestable
    def test_start(self):  # synced
        assert True

    def test_rename(self, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.rename('renamed')
        new_path = dir.path

        assert (
            not old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent
            and new_path.name == 'renamed'
            and dir == new_path
        )

    def test_new_rename(self, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.new_rename('renamed')
        new_path = dir.path

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent
            and old_path.name == 'testing'
            and new_path.name == 'renamed'
            and dir == new_path
        )

    def test_new_copy(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.new_copy(new_path := (temp_root.path / 'temp' / 'renamed'))

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.name == 'testing'
            and new_path.name == 'renamed'
            and dir == new_path
        )

    def test_copy(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.copy(new_path := (temp_root.path / 'temp' / 'renamed'))

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.name == 'testing'
            and new_path.name == 'renamed'
            and dir == old_path
        )

    def test_new_copy_to(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.new_copy_to(temp_root.path / 'temp')
        new_path = temp_root.path / 'temp' / old_path.name

        assert (
                old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent.parent
                and old_path.name == 'testing'
                and new_path.name == 'testing'
                and dir == new_path
        )

    def test_copy_to(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.copy_to(temp_root.path / 'temp')
        new_path = temp_root.path / 'temp' / old_path.name

        assert (
                old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent.parent
                and old_path.name == 'testing'
                and new_path.name == 'testing'
                and dir == old_path
        )

    def test_move(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.move(new_path := (temp_root.path / 'temp' / 'renamed'))

        assert (
                not old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent.parent
                and old_path.name == 'testing'
                and new_path.name == 'renamed'
                and dir == new_path
        )

    def test_move_to(self, temp_root: Dir, temp_dir: Dir):  # synced
        old_path = temp_dir.path
        dir = temp_dir.move_to(temp_root.path / 'temp')
        new_path = temp_root.path / 'temp' / old_path.name

        assert (
                not old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent.parent
                and old_path.name == 'testing'
                and new_path.name == 'testing'
                and dir == new_path
        )

    def test_create(self, temp_dir: Dir):  # synced
        temp_dir.delete()
        temp_dir.create()
        assert temp_dir.path.exists()

    def test_delete(self, temp_dir: Dir):  # synced
        temp_dir.delete()
        assert not temp_dir.path.exists()

    def test_clear(self, temp_root: Dir, temp_file: File):  # synced
        temp_root.clear()
        assert not temp_file.path.exists()

    def test_make_file(self, temp_dir: Dir):  # synced
        dir = temp_dir.make_file('temp', 'csv')
        assert dir is temp_dir and (dir.path / 'temp.csv').exists()

    def test_new_file(self, temp_dir: Dir):  # synced
        file = temp_dir.new_file('temp', 'csv')
        assert file.parent is temp_dir and file == file.path and file.path.exists()

    def test_make_dir(self, temp_dir: Dir):  # synced
        dir = temp_dir.make_dir('temp')
        assert dir is temp_dir and (dir.path / 'temp').exists()

    def test_new_dir(self, temp_dir: Dir):  # synced
        dir = temp_dir.new_dir('temp')
        assert dir.parent is temp_dir and dir == dir.path and dir.path.exists()

    def test_join_file(self, temp_dir: Dir):  # synced
        new_file = temp_dir.join_file('temp/test.txt')
        assert isinstance(new_file, File) and new_file.parent[1] == temp_dir

    def test_join_dir(self, temp_dir: Dir):  # synced
        new_dir = temp_dir.join_dir('temp/temp')
        assert isinstance(new_dir, Dir) and new_dir.parent[1] == temp_dir

    @untestable
    def test_symlink_to(self):  # synced
        assert True

    def test_seek_files(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        new_file = temp_dir.new_file('test', 'json')
        new_file.path.write_text("[1, 2, 3]")

        assert not list(temp_root.seek_files(name='not_present'))

        files = set(temp_root.seek_files(name='test'))
        assert files == {temp_file, new_file}

        file, = list(temp_root.seek_files(name='testing'))
        assert file == temp_file

        file, = list(temp_root.seek_files(name='test', extensions=['txt']))
        assert file == temp_file

        file, = list(temp_root.seek_files(name='test', content=r"\[1, 2, 3\]"))
        assert file == new_file

        file, = list(temp_root.seek_files(name='test', depth=0))
        assert file == temp_file

    def test_seek_dirs(self, temp_root: Dir, temp_dir: Dir):  # synced
        new_dir = temp_dir.new_dir('test')

        assert not list(temp_root.seek_dirs(name='not_present'))

        files = set(temp_root.seek_dirs(name='test'))
        assert files == {temp_dir, new_dir}

        file, = list(temp_root.seek_dirs(name='testing'))
        assert file == temp_dir

        file, = list(temp_root.seek_dirs(name='test', depth=0))
        assert file == temp_dir

    def test_walk(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        new_file = temp_dir.new_file('test', 'json')
        (root, root_dirs, root_files), (temp, temp_dirs, temp_files) = list(temp_root.walk())

        assert (
            root == temp_root
            and set(root_dirs) == {temp_dir}
            and set(root_files) == {temp_file}
            and temp == temp_dir
            and not set(temp_dirs)
            and set(temp_files) == {new_file}
        )

    def test_compare_files(self, temp_root: Dir, temp_file: File):  # synced
        (only_file, same_file), = list(temp_root.compare_files(temp_root))
        assert only_file == same_file == temp_file

    def test_compare_tree(self):  # synced
        assert True

    @untestable
    def test_compress(self):  # synced
        assert True

    @untestable
    def test_visualize(self):  # synced
        assert True

    def test_from_home(self):  # synced
        assert Dir.from_home() == Path.home()

    @untestable
    def test_from_desktop(self):  # synced
        assert True

    def test_from_cwd(self):  # synced
        assert Dir.from_cwd() == os.getcwd()

    def test_from_root(self):  # synced
        assert Dir.from_root() == Path.cwd().drive + os.sep

    @untestable
    def test_from_main(self):  # synced
        assert True

    @untestable
    def test_from_package(self):  # synced
        assert True

    def test_from_appdata(self, appdata_dir: Dir):  # synced
        assert appdata_dir == appdirs.user_data_dir(appname='testing', appauthor='testing')

    def test_from_temp(self):  # synced
        with Dir.from_temp() as dir:
            assert dir == (Path(tempfile.gettempdir()).resolve() / 'python')

    @unnecessary
    def test__bind(self):  # synced
        assert True

    @unnecessary
    def test__set_params(self):  # synced
        assert True

    @untestable
    def test__visualize_tree(self):  # synced
        assert True
