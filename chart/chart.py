from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Union

from .enums import EventArgs, EventType, NoteType, ScanLineDirection
from .type_helper import (from_bool, from_float, from_int, from_list,
                          to_class, to_enum, to_float)

@dataclass
class Event:
    evt_type: EventType
    evt_args: EventArgs

    @staticmethod
    def from_dict(obj: Any) -> 'Event':
        assert isinstance(obj, dict)
        evt_type = EventType(obj.get("type"))
        evt_args = EventArgs(obj.get("args"))
        return Event(evt_type, evt_args)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = to_enum(EventType, self.evt_type)
        result["args"] = to_enum(EventArgs, self.evt_args)
        return result


@dataclass
class EventOrder:
    tick: int
    event_list: List[Event]

    @staticmethod
    def from_dict(obj: Any) -> 'EventOrder':
        assert isinstance(obj, dict)
        tick = from_int(obj.get("tick"))
        event_list = from_list(Event.from_dict, obj.get("event_list"))
        return EventOrder(tick, event_list)

    def to_dict(self) -> dict:
        result: dict = {}
        result["tick"] = from_int(self.tick)
        result["event_list"] = from_list(lambda x: to_class(Event, x), self.event_list)
        return result


@dataclass
class Note:
    page_index: int
    note_type: NoteType
    note_id: int
    tick: int
    x: float
    has_sibling: bool
    hold_tick: int
    next_id: int
    is_forward: bool

    @staticmethod
    def from_dict(obj: Any) -> 'Note':
        assert isinstance(obj, dict)
        page_index = from_int(obj.get("page_index"))
        note_type = NoteType(obj.get("type"))
        note_id = from_int(obj.get("id"))
        tick = from_int(obj.get("tick"))
        x = from_float(obj.get("x"))
        has_sibling = from_bool(obj.get("has_sibling"))
        hold_tick = from_int(obj.get("hold_tick"))
        next_id = from_int(obj.get("next_id"))
        is_forward = from_bool(obj.get("is_forward"))
        return Note(page_index, note_type, note_id, tick, x, has_sibling, hold_tick, next_id, is_forward)

    def to_dict(self) -> dict:
        result: dict = {}
        result["page_index"] = from_int(self.page_index)
        result["type"] = to_enum(NoteType, self.note_type)
        result["id"] = from_int(self.note_id)
        result["tick"] = from_int(self.tick)
        result["x"] = to_float(self.x)
        result["has_sibling"] = from_bool(self.has_sibling)
        result["hold_tick"] = from_int(self.hold_tick)
        result["next_id"] = from_int(self.next_id)
        result["is_forward"] = from_bool(self.is_forward)
        return result


@dataclass
class Tempo:
    tick: int
    value: int

    def __post_init__(self):
        self.bpm = 6e7 / self.value

    @staticmethod
    def from_dict(obj: Any) -> 'Tempo':
        assert isinstance(obj, dict)
        tick = from_int(obj.get("tick"))
        value = from_int(obj.get("value"))
        return Tempo(tick, value)

    def to_dict(self) -> dict:
        result: dict = {}
        result["tick"] = from_int(self.tick)
        result["value"] = from_int(self.value)
        return result


@dataclass
class Page:
    start_tick: int
    end_tick: int
    scan_line_direction: ScanLineDirection

    def __post_init__(self):
        self.ticks = self.end_tick - self.start_tick

    @staticmethod
    def from_dict(obj: Any) -> 'Page':
        assert isinstance(obj, dict)
        start_tick = from_int(obj.get("start_tick"))
        end_tick = from_int(obj.get("end_tick"))
        scan_line_direction = ScanLineDirection(obj.get("scan_line_direction"))
        return Page(start_tick, end_tick, scan_line_direction)

    def to_dict(self) -> dict:
        result: dict = {}
        result["start_tick"] = from_int(self.start_tick)
        result["end_tick"] = from_int(self.end_tick)
        result["scan_line_direction"] = to_enum(ScanLineDirection,
                                                self.scan_line_direction)
        return result

    def in_page(self, item: Union[Note, Tempo]) -> bool:
        return self.start_tick <= item.tick and item.tick < self.end_tick


@dataclass
class Chart:
    format_version: int
    time_base: int
    start_offset_time: int
    page_list: List[Page]
    tempo_list: List[Tempo]
    event_order_list: List[EventOrder]
    note_list: List[Note]

    @staticmethod
    def from_dict(obj: Any) -> 'Chart':
        assert isinstance(obj, dict)
        format_version = from_int(obj.get("format_version"))
        time_base = from_int(obj.get("time_base"))
        start_offset_time = from_float(obj.get("start_offset_time"))
        page_list = from_list(Page.from_dict, obj.get("page_list"))
        tempo_list = from_list(Tempo.from_dict, obj.get("tempo_list"))
        event_order_list = from_list(EventOrder.from_dict, obj.get("event_order_list"))
        note_list = from_list(Note.from_dict, obj.get("note_list"))
        return Chart(format_version, time_base, start_offset_time, page_list, tempo_list, event_order_list, note_list)

    def to_dict(self) -> dict:
        result: dict = {}
        result["format_version"] = from_int(self.format_version)
        result["time_base"] = from_int(self.time_base)
        result["start_offset_time"] = to_float(self.start_offset_time)
        result["page_list"] = from_list(lambda x: to_class(Page, x), self.page_list)
        result["tempo_list"] = from_list(lambda x: to_class(Tempo, x), self.tempo_list)
        result["event_order_list"] = from_list(lambda x: to_class(EventOrder, x), self.event_order_list)
        result["note_list"] = from_list(lambda x: to_class(Note, x), self.note_list)
        return result


def chart_from_dict(s: Any) -> Chart:
    return Chart.from_dict(s)


def chart_to_dict(x: Chart) -> Any:
    return to_class(Chart, x)
