import os
from pathlib import Path

from pathmagic import Dir, File

from tests.conftest import abstract


class TestPathMagic:
    class TestEnums:
        class TestIfExists:
            pass

    def test___str__(self, temp_file: File):  # synced
        assert str(temp_file) == os.fspath(temp_file)

    def test___fspath__(self, temp_file: File):  # synced
        assert os.fspath(temp_file) == os.fspath(temp_file.path)

    def test___hash__(self, temp_file: File):  # synced
        assert hash(temp_file) == id(temp_file)

    def test___eq__(self, temp_file: File):  # synced
        assert temp_file == temp_file.path and temp_file == str(temp_file)

    def test___ne__(self, temp_dir: Dir, temp_file: File):  # synced
        assert temp_dir != temp_file.path and temp_dir != str(temp_file)

    def test___lt__(self, temp_root: Dir, temp_file: File):  # synced
        assert temp_file < temp_root and not temp_root < temp_root

    def test___le__(self, temp_root: Dir, temp_file: File):  # synced
        assert temp_file <= temp_root <= temp_root

    def test___gt__(self, temp_root: Dir, temp_file: File):  # synced
        assert temp_root > temp_file and not temp_root > temp_root

    def test___ge__(self, temp_root: Dir, temp_file: File):  # synced
        assert temp_root >= temp_root >= temp_file

    def test_path(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert isinstance(temp_dir.path, Path) and isinstance(temp_file.path, Path)

        (temp := (temp_root.path / 'temp')).mkdir()

        old_dir_path = temp_dir.path
        temp_dir.path = temp / 'test'
        new_dir_path = temp_dir.path

        assert (
            not old_dir_path.exists()
            and new_dir_path.exists()
            and old_dir_path.parent == new_dir_path.parent.parent
            and new_dir_path.name == 'test'
        )

        old_file_path = temp_file.path
        temp_file.path = temp / 'renamed.json'
        new_file_path = temp_file.path

        assert (
            not old_file_path.exists()
            and new_file_path.exists()
            and old_file_path.parent == new_file_path.parent.parent
            and new_file_path.read_text() == "testing..."
            and new_file_path.name == 'renamed.json'
        )

    def test_parent(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert temp_root is temp_dir.parent and temp_root is temp_file.parent

        (temp := (temp_root.path / 'temp')).mkdir()

        old_dir_path = temp_dir.path
        temp_dir.parent = temp
        new_dir_path = temp_dir.path

        assert (
            not old_dir_path.exists()
            and new_dir_path.exists()
            and old_dir_path.parent == new_dir_path.parent.parent
            and new_dir_path.name == 'testing'
        )

        old_file_path = temp_file.path
        temp_file.parent = temp
        new_file_path = temp_file.path

        assert (
            not old_file_path.exists()
            and new_file_path.exists()
            and old_file_path.parent == new_file_path.parent.parent
            and new_file_path.read_text() == "testing..."
            and new_file_path.name == 'testing.txt'
        )

    def test_name(self, temp_root: Dir, temp_dir: Dir, temp_file: File):  # synced
        assert temp_dir.name == temp_dir.path.name and temp_file.name == temp_file.path.name

        old_dir_path = temp_dir.path
        temp_dir.name = 'renamed'
        new_dir_path = temp_dir.path

        assert (
            not old_dir_path.exists()
            and new_dir_path.exists()
            and old_dir_path.parent == new_dir_path.parent
            and new_dir_path.name == 'renamed'
        )

        old_file_path = temp_file.path
        temp_file.name = 'renamed.json'
        new_file_path = temp_file.path

        assert (
            not old_file_path.exists()
            and new_file_path.exists()
            and old_file_path.parent == new_file_path.parent
            and new_file_path.read_text() == "testing..."
            and new_file_path.name == 'renamed.json'
        )

    def test_stat(self, temp_file: File):  # synced
        assert isinstance(temp_file.stat, os.stat_result)

    @abstract
    def test_create(self):  # synced
        assert True

    @abstract
    def test_rename(self):  # synced
        assert True

    @abstract
    def test_move(self):  # synced
        assert True

    def test_trash(self, temp_file: File):  # synced
        temp_file.trash()
        assert not temp_file.path.exists()

    @abstract
    def test_delete(self, temp_file: File):  # synced
        assert True

    def test_from_pathlike(self, temp_file: File):  # synced
        assert File.from_pathlike(temp_file) is temp_file and temp_file == File.from_pathlike(str(temp_file))

    def test__validate(self):  # synced
        assert True

    def test__prepare_dir_if_not_exists(self, temp_dir: Dir):  # synced
        new_path = temp_dir.path / 'temp'
        temp_dir._prepare_dir_if_not_exists(new_path)
        temp_dir._prepare_dir_if_not_exists(new_path)  # test idempotency
        assert new_path.exists()

    def test__prepare_file_if_not_exists(self, temp_dir: Dir):  # synced
        new_path = temp_dir.path / 'temp.txt'
        temp_dir._prepare_file_if_not_exists(new_path)
        temp_dir._prepare_file_if_not_exists(new_path)  # test idempotency
        assert new_path.exists()

    def test__parse_filename_args(self, temp_dir: Dir):  # synced
        assert temp_dir._parse_filename_args('hi', 'txt').name == 'hi.txt'
        assert temp_dir._parse_filename_args('hi.txt').name == 'hi.txt'
