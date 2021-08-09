import sys

from pathmagic import Dir, File

from tests.conftest import untestable, unnecessary


class TestFile:
    def test___len__(self, temp_file: File):  # synced
        assert len(temp_file) == 1
        temp_file.append("\nanother test")
        assert len(temp_file) == 2

    def test___bool__(self, temp_file: File):  # synced
        assert temp_file
        temp_file.content = None
        assert not temp_file

    def test___iter__(self, temp_file: File):  # synced
        first_line, = list(temp_file)
        assert first_line == "testing..."

    def test___getitem__(self, temp_file: File):  # synced
        temp_file.write("line1\nline2\nline3")
        assert temp_file[0] == "line1" and temp_file[1] == "line2" and temp_file[2] == "line3"

    def test___setitem__(self, temp_file: File):  # synced
        temp_file.write("line1\nline2\nline3")
        temp_file[1] = "LINE2"
        assert temp_file.read() == "line1\nLINE2\nline3"

    def test___delitem__(self, temp_file: File):  # synced
        temp_file.write("line1\nline2\nline3")
        del temp_file[1]
        assert temp_file.read() == "line1\nline3"

    def test_stem(self, temp_file: File):  # synced
        assert temp_file.stem == 'testing'

        old_path = temp_file.path
        temp_file.stem = 'renamed'
        new_path = temp_file.path

        assert (
                not old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent
                and new_path.read_text() == "testing..."
                and new_path.name == 'renamed.txt'
        )

    def test_extension(self, temp_file: File):  # synced
        assert temp_file.extension == 'txt'

        old_path = temp_file.path
        temp_file.extension = 'json'
        new_path = temp_file.path

        assert (
                not old_path.exists()
                and new_path.exists()
                and old_path.parent == new_path.parent
                and new_path.read_text() == "testing..."
                and new_path.name == 'testing.json'
        )

    def test_content(self, temp_file: File):  # synced
        assert temp_file.content == "testing..."

        NEW_CONTENT = "testing123..."
        temp_file.content = NEW_CONTENT

        assert temp_file.path.read_text() == NEW_CONTENT

    def test_read(self, temp_file: File):  # synced
        assert temp_file.read() == 'testing...'

    @untestable
    def test_read_help(self):  # synced
        assert True

    def test_write(self, temp_file: File):  # synced
        NEW_CONTENT = "testing123..."
        temp_file.write(NEW_CONTENT)
        assert temp_file.read() == NEW_CONTENT

    @untestable
    def test_write_help(self):  # synced
        assert True

    def test_append(self, temp_file: File):  # synced
        temp_file.append("\ntesting123...")
        assert temp_file.read() == "testing...\ntesting123..."

    @untestable
    def test_start(self):  # synced
        assert True

    def test_rename(self, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.rename('renamed', 'json')
        new_path = file.path

        assert (
            not old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent
            and new_path.read_text() == "testing..."
            and new_path.name == 'renamed.json'
            and file == new_path
        )

    def test_new_rename(self, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.new_rename('renamed', 'json')
        new_path = file.path

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent
            and old_path.read_text() == "testing..."
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'renamed.json'
            and file == new_path
        )

    def test_new_copy(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.new_copy(new_path := (temp_root.path / 'temp' / 'renamed.json'))

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.read_text() == "testing..."
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'renamed.json'
            and file == new_path
        )

    def test_copy(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.copy(new_path := (temp_root.path / 'temp' / 'renamed.json'))

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.read_text() == "testing..."
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'renamed.json'
            and file == old_path
        )

    def test_new_copy_to(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.new_copy_to(temp := (temp_root.path / 'temp'))
        new_path = temp / old_path.name

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.read_text() == "testing..."
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'testing.txt'
            and file == new_path
        )

    def test_copy_to(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.copy_to(temp := (temp_root.path / 'temp'))
        new_path = temp / old_path.name

        assert (
            old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and old_path.read_text() == "testing..."
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'testing.txt'
            and file == old_path
        )

    def test_move(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.move(new_path := (temp_root.path / 'temp' / 'renamed.json'))

        assert (
            not old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'renamed.json'
            and file == new_path
        )

    def test_move_to(self, temp_root: Dir, temp_file: File):  # synced
        old_path = temp_file.path
        file = temp_file.move_to(temp := (temp_root.path / 'temp'))
        new_path = temp / old_path.name

        assert (
            not old_path.exists()
            and new_path.exists()
            and old_path.parent == new_path.parent.parent
            and new_path.read_text() == "testing..."
            and old_path.name == 'testing.txt'
            and new_path.name == 'testing.txt'
            and file == new_path
        )

    def test_create(self, temp_file: File):  # synced
        temp_file.delete()
        temp_file.create()
        assert temp_file.path.exists()

    def test_delete(self, temp_file: File):  # synced
        temp_file.delete()
        assert not temp_file.path.exists()

    @untestable
    def test_compress(self):  # synced
        assert True

    def test_from_python(self):  # synced
        assert File.from_python() == sys.executable

    @untestable
    def test_from_main(self):  # synced
        assert True

    @untestable
    def test_from_resource(self):  # synced
        assert True

    @unnecessary
    def test__set_params(self):  # synced
        assert True
