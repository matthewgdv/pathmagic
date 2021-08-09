from __future__ import annotations

from .format import Format


class Audio(Format):
    extensions = {"mp3", "wav", "ogg", "flv"}

    @classmethod
    def initialize(cls) -> None:
        import pydub

        cls.module = pydub
        cls.readfuncs.update(
            {
                "mp3": cls.module.AudioSegment.from_mp3,
                "wav": cls.module.AudioSegment.from_wav,
                "ogg": cls.module.AudioSegment.from_ogg,
                "flv": cls.module.AudioSegment.from_flv
            }
        )
        cls.writefuncs.update(
            {
                "mp3": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="mp3", **kwargs),
                "wav": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="wav", **kwargs),
                "ogg": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="ogg", **kwargs),
                "flv": lambda *args, **kwargs: cls.module.AudioSegment.export(*args, format="flv", **kwargs)
            }
        )

    def write_help(self) -> None:
        help(self.module.AudioSegment.export)
