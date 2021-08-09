# import pytest

from pathmagic import Dir, File
from pathmagic.settings import Settings
from pathmagic.pathmagic import PathMagic


class TestSettings:
    def test_from_settings(self):  # synced
        template_settings = Settings(if_exists=PathMagic.Enums.IfExists.FAIL, file_class=File, dir_class=Dir)
        new_settings = Settings.from_settings(template_settings)

        assert (
            template_settings.if_exists == new_settings.if_exists
            and template_settings.file_class == new_settings.file_class
            and template_settings.dir_class == new_settings.dir_class
        )
