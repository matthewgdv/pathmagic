from __future__ import annotations

from typing import Any

from .format import Format


class Image(Format):
    extensions = {'png', 'jpg', 'jpeg'}

    @classmethod
    def initialize(cls) -> None:
        from PIL import Image

        cls.module = Image
        cls.readfuncs.update({extension: cls.module.open for extension in cls.extensions})
        cls.writefuncs.update({extension: cls.module.Image.save for extension in cls.extensions})

    def write(self, item: Any, **kwargs: Any) -> None:
        self.writefuncs[self.file.extension](item.convert("RGB"), str(self.file), **kwargs)
