import pytest

from pathmagic import Dir, File


@pytest.fixture()
def temp_root() -> Dir:
    with Dir.from_temp() as temp:
        yield temp


@pytest.fixture()
def temp_dir(temp_root: Dir) -> Dir:
    return temp_root.new_dir('testing')


@pytest.fixture()
def temp_file(temp_root: Dir) -> File:
    return temp_root.new_file('testing', 'txt').write('testing...')


@pytest.fixture()
def appdata_dir() -> Dir:
    appdata_dir = Dir.from_appdata(app_name='testing', app_author='testing')
    yield appdata_dir
    appdata_dir.delete()


untestable = pytest.mark.skip(reason="untestable")
abstract = pytest.mark.skip(reason="abstract")
unnecessary = pytest.mark.skip(reason="unnecessary")
