# import pytest

from pathmagic.helper import is_special, clean_filename

from tests.conftest import untestable


@untestable
def test_is_running_in_ipython():  # synced
    assert True


def test_is_special():  # synced
    assert is_special('_parent_') and is_special('__module__') and not is_special('_private')


def test_clean_filename():  # synced
    assert clean_filename('Raw.TXT') == 'Raw.txt'
