from __future__ import annotations

import json
from typing import Any

from subtypes import TranslatableMeta

from .format import Format


class Json(Format):
    extensions = {'json'}

    @classmethod
    def initialize(cls) -> None:
        cls.module, cls.translator = json, TranslatableMeta.translator
        cls.readfuncs.update({'json': json.load})
        cls.writefuncs.update({'json': json.dump})

    def read(self, namespace: bool = True, **kwargs: Any) -> Any:
        try:
            with open(self.file) as file:
                return self.translator(self.readfuncs[self.file.extension](file, **kwargs))
        except self.module.JSONDecodeError:
            return self.file.path.read_text() or None

    def write(self, item: Any, indent: int = 4, **kwargs: Any) -> None:
        with open(self.file, 'w') as file:
            self.writefuncs[self.file.extension](item, file, indent=indent, **kwargs)
