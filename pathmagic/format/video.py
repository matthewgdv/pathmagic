from __future__ import annotations

from types import MethodType
from typing import Any

from .format import Format


class Video(Format):
    extensions = {"mp4", "mkv", "avi", "gif"}

    @classmethod
    def initialize(cls) -> None:
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import moviepy.editor as edit

        cls.module = edit
        cls.readfuncs.update({extension: edit.VideoFileClip for extension in cls.extensions})

    def read(self, **kwargs: Any) -> Any:
        out = self.readfuncs[self.file.extension](str(self.file), **kwargs)
        out._repr_html_ = MethodType(lambda this: this.ipython_display()._data_and_metadata(), out)
        return out
