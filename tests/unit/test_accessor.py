import pytest
from pathmagic import Dir, File
from pathmagic.accessor import Name, AmbiguityError

from tests.conftest import unnecessary, abstract, untestable


class TestAccessor:
    def test___call__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        file_name, = temp_root.files()
        assert file_name == temp_file.name

        dir_name, = temp_root.dirs()
        assert dir_name == temp_dir.name

    def test___len__(self, temp_root: Dir):  # synced
        assert len(temp_root.files) == 0
        temp_root.new_file('test', 'json')
        assert len(temp_root.files) == 1

        assert len(temp_root.dirs) == 0
        temp_root.new_dir('test')
        assert len(temp_root.dirs) == 1

    def test___iter__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert set(temp_root.files) == {temp_file}
        assert set(temp_root.dirs) == {temp_dir}

    def test___contains__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        home = Dir.from_home()

        assert (
            temp_file in temp_root.files
            and temp_dir in temp_root.dirs
            and temp_root not in home.dirs
            and temp_root not in home.files
        )

    @abstract
    def test___getitem__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert True

    @unnecessary
    def test___setitem__(self):  # synced
        assert True

    def test___delitem__(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert temp_dir.path.exists() and temp_file.path.exists()
        del temp_root.files[temp_file.name]
        del temp_root.dirs[temp_dir.name]
        assert not temp_dir.path.exists() and not temp_file.path.exists()

    @untestable
    def test___getattribute__(self):  # synced
        assert True

    @untestable
    def test___getattr__(self, temp_dir: Dir):  # synced
        assert True

    @abstract
    def test__synchronize_(self):  # synced
        assert True

    @untestable
    def test__acquire_(self):  # synced
        assert True


class TestFileAccessor:
    def test___getitem__(self, temp_root: Dir, temp_file: File):  # synced
        assert temp_root.files[temp_file.name] is temp_file

    def test__synchronize_(self, temp_root: Dir):  # synced
        (temp_root.path / 'test.txt').touch()
        assert 'test.txt' not in temp_root.files._items_
        temp_root.files._synchronize_()
        assert 'test.txt' in temp_root.files._items_


class TestDirAccessor:
    def test___getitem__(self, temp_root: Dir, temp_dir: Dir):  # synced
        assert temp_root.dirs[temp_dir.name] is temp_dir

    def test__synchronize_(self, temp_root: Dir):  # synced
        (temp_root.path / 'test').mkdir()
        assert 'test' not in temp_root.dirs._items_
        temp_root.dirs._synchronize_()
        assert 'test' in temp_root.dirs._items_


class TestAmbiguityError:
    pass


class TestName:
    def test_access(self, temp_root: Dir, temp_file: File):  # synced
        with pytest.raises(AmbiguityError):
            Name(clean_name='test', raw_names=['testing.txt', 'testing.json'], accessor=temp_root.files).access()

        assert Name(clean_name='test', raw_names=['testing.txt'], accessor=temp_root.files).access() is temp_file
