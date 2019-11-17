import json
import math
import os
from collections import OrderedDict
from enum import Enum
from itertools import tee
from typing import Any, Dict, List, Tuple, TypeVar

from mutagen.mp3 import MP3

from chart import Chart, EventType, LevelInfo, NoteType

EnumT = TypeVar("EnumT", bound=Enum)

NOTE_CATEGORIES: Dict[str, List[NoteType]] = {
    category: [nt for nt in NoteType if category in nt.name]
    for category in ["hold", "drag_head", "drag_child", "drag", "cdrag"]
}

MINIMUM_GOOD_NOTES = [NoteType.tap, *NOTE_CATEGORIES["hold"], NoteType.cdrag_head]
MINIMIUM_GREAT_NOTES = [NoteType.flick]

def make_dict(enum: EnumT) -> Dict[EnumT, int]:
    return {item: 0 for item in enum}

def truncate(num: float, decimals: int) -> float:
    base = 10 ** decimals
    return math.floor(num * base) / base

class Analyzer:
    def __init__(self, folder: str, chart_id: str):
        self.__open_files(folder, chart_id)

        self.note_counts: Dict[NoteType, int] = make_dict(NoteType)
        self.note_rates: Dict[NoteType, int] = make_dict(NoteType)
        self.speed_changes: Dict[EventType, int] = make_dict(EventType)
        self.scan_line_stats: Dict[str, Dict[str, float]] = {
            "min": {"base": -1, "ticks": -1, "bpm": float("inf")},
            "mode": {"base": -1, "ticks": -1, "bpm": -1},
            "max": {"base": -1, "ticks": -1, "bpm": float("-inf")}
        }
        self.subtotals: Dict[str, int] = {
            "hold": 0,
            "drag_head": 0,
            "drag_child": 0,
            "cdrag": 0,
            "drag": 0,
            "total_drag": 0,
        }
        self.min_scores: Dict[str, float] = {
            "fc_score": 1000000,
            "fc_tp": 100.00,
            "mm_tp": 100.00
        }

    def __open_files(self, folder: str, chart_id: str):
        level_json_path = os.path.join(folder, chart_id, "level.json")
        try:
            with open(level_json_path, encoding="utf8") as level_json_file:
                self.level_info = LevelInfo.from_dict(
                    json.load(level_json_file), folder)

                if not self.level_info.are_paths_valid():
                    raise OSError(
                        "One of the paths in the level.json is invalid"
                    )
        except Exception as err:
            raise Exception(
                f"There's something wrong with {chart_id}'s level.json"
            ) from err

        self.chart_info = self.level_info.charts[-1]
        try:
            with open(self.level_info.paths["charts"][-1], encoding="utf8") as \
                    chart_path:
                self.chart = Chart.from_dict(json.load(chart_path))
        except Exception as err:
            raise Exception(
                f"There's something wrong with {chart_id}'s "
                f"{self.chart_info.name} chart."
            ) from err

    def start(self):
        self.music_length = math.ceil(
            MP3(self.level_info.paths["music"]).info.length)
        self._get_scan_line_stats()
        self._get_note_counts()
        self._get_min_scores()

    def get_stats_as_json(self) -> dict:
        append_total = ("hold", "drag_head", "drag_child")
        ret = OrderedDict()
        meta = self.level_info.to_dict()
        ret = {
            key: meta[key] for key in 
            ("title", "artist", "illustrator", "charter")
        }
        ret["length"] = self.music_length
        ret["diff"] = self.chart_info.name
        ret["level"] = self.chart_info.difficulty

        ret.update(self._convert_enum_key(self.speed_changes))
        ret.update({"speed_changes": sum(self.speed_changes.values())})

        for stat_type, stats in self.scan_line_stats.items():
            for key, val in stats.items():
                ret_key = (f"{stat_type}_bpm_{key}" if key != "bpm" 
                           else f"{stat_type}_bpm")
                ret[ret_key] = val

        for stat_type in ("notes", "rate"):
            note_stats = (self.note_counts if stat_type == "notes"
                          else self.note_rates)
            for key, val in note_stats.items():
                ret[f"{key.name}_{stat_type}"] = val
            
            subtotal_stats = (self.subtotals if stat_type == "notes"
                              else self.subtotal_rates)
            for key, val in subtotal_stats.items():
                ret_key = f"{key}_{stat_type}"
                ret_key = f"total_{ret_key}" if key in append_total else ret_key
                ret[ret_key] = val

            if stat_type == "notes":
                ret["avg_taps"] = self.avg_taps
                ret["total_notes"] = self.total_notes

        ret.update({
            "avg_taps_per_sec": self.avg_taps_per_sec,
            "notes_per_sec": self.notes_per_sec,
        })

        for key, val in self.min_scores.items():
            ret[f"min_{key}"] = val

        return ret

    def _get_scan_line_stats(self):
        scan_line_speeds = self._get_scan_line_speeds()
        scan_line_counts = dict()
        mode_count = 0
        prev_speed = scan_line_speeds[0]
        prev_speed_change = None

        for speed in scan_line_speeds:
            if speed["bpm"] > self.scan_line_stats["max"]["bpm"]:
                self.scan_line_stats["max"] = speed
            if speed["bpm"] < self.scan_line_stats["min"]["bpm"]:
                self.scan_line_stats["min"] = speed

            if prev_speed is not None and speed != prev_speed:
                speed_diff = speed["bpm"] - prev_speed["bpm"]
                speed_change = EventType.speed_up if speed_diff > 0 else \
                    EventType.speed_down

                if speed_change != prev_speed_change:
                    self.speed_changes[speed_change] += 1

                prev_speed_change = speed_change

            key = (speed["bpm"], speed["ticks"])
            scan_line_counts[key] = scan_line_counts.setdefault(key, 0) + 1
            prev_speed = speed

        for speed, count in scan_line_counts.items():
            if count > mode_count:
                self.scan_line_stats["mode"] = {
                    "base": speed[0],
                    "ticks": speed[1],
                    "bpm": self._get_bpm(speed[0], speed[1])
                }
                mode_count = count

        for stat in self.scan_line_stats:
            self.scan_line_stats[stat]["base"] = round(
                self.scan_line_stats[stat]["base"], 2)

    def _get_scan_line_speeds(self) -> List[Tuple[float]]:
        scan_line_speeds = []
        tempo_it, next_tempo_it = tee(iter(self.chart.tempo_list))

        tempo = None
        next_tempo = next(next_tempo_it)

        for page in self.chart.page_list:
            page_added = False

            while next_tempo is not None and page.in_page(next_tempo):
                tempo = next(tempo_it)
                next_tempo = next(next_tempo_it, None)
                bpm = self._get_bpm(tempo.bpm, page.ticks)
                scan_line_speeds.append({
                    "base": tempo.bpm,
                    "ticks": page.ticks,
                    "bpm": bpm
                })
                page_added = True

            if not page_added:
                bpm = self._get_bpm(tempo.bpm, page.ticks)
                scan_line_speeds.append({
                    "base": tempo.bpm,
                    "ticks": page.ticks,
                    "bpm": bpm
                })

        return scan_line_speeds

    def _get_note_counts(self):
        for note in self.chart.note_list:
            self.note_counts[note.note_type] += 1

        self.total_notes = sum(self.note_counts.values())
        self.note_rates = dict()

        self.avg_taps = 0
        for nt, count in self.note_counts.items():
            for category in NOTE_CATEGORIES:
                if nt in NOTE_CATEGORIES[category]:
                    self.subtotals[category] += count

            if nt not in NOTE_CATEGORIES["drag_child"]:
                self.avg_taps += count

            self.note_rates[nt] = truncate(count / self.total_notes, 4)

        self.subtotals["total_drag"] = self.subtotals["drag"]
        self.subtotals["drag"] = self.subtotals["total_drag"] - \
            self.subtotals["cdrag"]

        self.subtotal_rates = {st_key: truncate(count / self.total_notes, 4)
                               for st_key, count in self.subtotals.items()}
        self.avg_taps_per_sec = truncate(self.avg_taps / self.music_length, 2)
        self.notes_per_sec = truncate(self.total_notes / self.music_length, 2)

    def _get_min_scores(self):
        goods = 0
        greats = 0
        perfects = 0

        for nt, count in self.note_counts.items():
            if nt in MINIMUM_GOOD_NOTES:
                goods += count
            elif nt in MINIMIUM_GREAT_NOTES:
                greats += count
            else:
                perfects += count

        self.min_scores["fc_score"] = math.floor(9e5 / self.total_notes * (
            perfects + greats + 0.3 * goods) + 1e5)
        self.min_scores["fc_tp"] = truncate((perfects + 0.7 * greats
            + 0.3 * goods) / self.total_notes, 4)
        self.min_scores["mm_tp"] = truncate((perfects + 0.7 * greats
            + 0.7 * goods) / self.total_notes, 4)

    def _get_bpm(self, base_bpm: float, ticks: int) -> float:
        return round(base_bpm * 2 * self.chart.time_base / ticks, 2)

    def _convert_enum_key(self, obj: Dict[Enum, Any]) -> Dict[str, Any]:
        return {key.name: val for key, val in obj.items()}
