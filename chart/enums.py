from enum import Enum

class NoteType(Enum):
    TAP = 0
    HOLD = 1
    LONG_HOLD = 2
    DRAG_HEAD = 3
    DRAG_CHILD = 4
    FLICK = 5
    CDRAG_HEAD = 6
    CDRAG_CHILD = 7

class ScanLineDirection(Enum):
    DOWN = -1
    UP = 1

class EventType(Enum):
    SPEED_UP = 0
    SPEED_DOWN = 1

class EventArgs(Enum):
    R = "R"
    G = "G"
    W = "W"