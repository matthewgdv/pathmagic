from subtypes import Enum


class Enums:
    class IfExists(Enum):
        FAIL = ALLOW = TRASH = Enum.Auto()
