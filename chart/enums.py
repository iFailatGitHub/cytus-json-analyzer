from enum import Enum

class NoteType(Enum):
    tap = 0
    hold = 1
    long_hold = 2
    drag_head = 3
    drag_child = 4
    flick = 5
    cdrag_head = 6
    cdrag_child = 7

class ScanLineDirection(Enum):
    down = -1
    up = 1

class EventType(Enum):
    speed_up = 0
    speed_down = 1

class EventArgs(Enum):
    R = "R"
    G = "G"
    W = "W"
    NONE = "" # deep dive more like deep shit
    WHAT = "???" # rayark i will kill you personally
