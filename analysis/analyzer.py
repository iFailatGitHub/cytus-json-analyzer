import json
import math
import os
from enum import Enum
from itertools import tee
from typing import Any, Dict, List, Tuple, TypeVar

from mutagen.mp3 import MP3

from chart import Chart, EventType, LevelInfo, NoteType

EnumT = TypeVar("EnumT", bound=Enum)

NOTE_CATEGORIES: Dict[str, List[NoteType]] = {
    category: [nt for nt in NoteType if category in nt.name]
    for category in ["HOLD", "DRAG_HEAD", "DRAG_CHILD", "DRAG", "CDRAG"]
}

MINIMUM_GOOD_NOTES = [NoteType.TAP, *NOTE_CATEGORIES["HOLD"], NoteType.CDRAG_HEAD]
MINIMIUM_GREAT_NOTES = [NoteType.FLICK]

def make_dict(enum: EnumT) -> Dict[EnumT, int]:
    return {item: 0 for item in enum}


class Analyzer:
    def __init__(self, folder: str, chart_id: str):
        self.__open_files(folder, chart_id)

        self.note_counts: Dict[NoteType, int] = make_dict(NoteType)
        self.note_rates: Dict[NoteType, int] = make_dict(NoteType)
        self.speed_changes: Dict[EventType, int] = make_dict(EventType)
        self.scan_line_stats: Dict[str, Dict[str, float]] = {
            "min_bpm": {"base_bpm": -1, "ticks": -1, "bpm": float("inf")},
            "mode_bpm": {"base_bpm": -1, "ticks": -1, "bpm": -1},
            "max_bpm": {"base_bpm": -1, "ticks": -1, "bpm": float("-inf")}
        }
        self.subtotals: Dict[str, int]= {
            "HOLD": 0,
            "DRAG_HEAD": 0,
            "DRAG_CHILD": 0,
            "CDRAG": 0,
            "DRAG_ONLY": 0,
            "DRAG": 0,
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
        self.__get_scan_line_stats()
        self.__get_note_counts()
        self.__get_min_scores()

    def get_stats_as_json(self) -> dict:
        ret = dict()
        meta = self.level_info.to_dict()
        ret["meta"] = {key: meta[key] 
                       for key in ("id", "title", "artist", "illustrator")}
        ret["meta"]["length"] = self.music_length
        ret["meta"]["diff"] = self.chart_info.name
        ret["meta"]["level"] = self.chart_info.level

        for stat_type, sl_stat in self.scan_line_stats.items():
            ret[stat_type] = sl_stat

        ret["note_counts"] = {
            nt.name.lower(): count for nt, count in self.note_counts.items()
        }
        ret["subtotals"] = {
            st.lower(): count for st, count in self.subtotals.items()
        }
        ret["note_rates"] = {
            nt.name.lower(): rate for nt, rate in self.note_rates.items()
        }
        ret["subtotal_rates"] = {
            st.lower(): count for st, count in self.subtotal_rates.items()
        }
        ret["speed_changes"]: {
            et.name.lower(): count for et, count in self.speed_changes.items()
        }

        ret["subtotals"]["total"] = self.total_notes
        ret.update({"min_scores": self.min_scores})
        return ret

    def __get_scan_line_stats(self):
        scan_line_speeds = self.__get_scan_line_speeds()
        scan_line_counts = dict()
        mode_count = 0
        prev_speed = scan_line_speeds[0]
        prev_speed_change = None

        for speed in scan_line_speeds:
            if speed["bpm"] > self.scan_line_stats["max_bpm"]["bpm"]:
                self.scan_line_stats["max_bpm"] = speed
            if speed["bpm"] < self.scan_line_stats["min_bpm"]["bpm"]:
                self.scan_line_stats["min_bpm"] = speed

            if prev_speed is not None and speed != prev_speed:
                speed_diff = speed["bpm"] - prev_speed["bpm"]
                speed_change = EventType.SPEED_UP if speed_diff > 0 else \
                    EventType.SPEED_DOWN

                if speed_change != prev_speed_change:
                    self.speed_changes[speed_change] += 1

                prev_speed_change = speed_change

            key = (speed["base_bpm"], speed["ticks"])
            scan_line_counts[key] = scan_line_counts.setdefault(key, 0) + 1
            prev_speed = speed

        for speed, count in scan_line_counts.items():
            if count > mode_count:
                self.scan_line_stats["mode_bpm"] = {
                    "base_bpm": speed[0],
                    "ticks": speed[1],
                    "bpm": self.__get_bpm(speed[0], speed[1])
                }
                mode_count = count

    def __get_scan_line_speeds(self) -> List[Tuple[float]]:
        scan_line_speeds = []
        tempo_it, next_tempo_it = tee(iter(self.chart.tempo_list))

        tempo = None
        next_tempo = next(next_tempo_it)

        for page in self.chart.page_list:
            page_added = False

            while next_tempo is not None and page.in_page(next_tempo):
                tempo = next(tempo_it)
                next_tempo = next(next_tempo_it, None)
                bpm = self.__get_bpm(tempo.bpm, page.ticks)
                scan_line_speeds.append({
                    "base_bpm": tempo.bpm,
                    "ticks": page.ticks,
                    "bpm": bpm
                })
                page_added = True

            if not page_added:
                bpm = self.__get_bpm(tempo.bpm, page.ticks)
                scan_line_speeds.append({
                    "base_bpm": tempo.bpm,
                    "ticks": page.ticks,
                    "bpm": bpm
                })

        return scan_line_speeds

    def __get_note_counts(self):
        for note in self.chart.note_list:
            self.note_counts[note.note_type] += 1

        self.total_notes = sum(self.note_counts.values())
        self.note_rates = dict()

        taps = 0
        for nt, count in self.note_counts.items():
            for category in NOTE_CATEGORIES:
                if nt in NOTE_CATEGORIES[category]:
                    self.subtotals[category] += count

            if nt not in NOTE_CATEGORIES["DRAG_CHILD"] or \
                nt is not NoteType.DRAG_HEAD:
                taps += count

            self.note_rates[nt] = count / self.total_notes

        self.subtotals["DRAG_ONLY"] = self.subtotals["DRAG"] - \
            self.subtotals["CDRAG"]

        self.subtotal_rates = {st_key: count / self.total_notes 
                               for st_key, count in self.subtotals.items()}
        self.avg_tap_rate = taps / self.total_notes

    def __get_min_scores(self):
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
        self.min_scores["fc_tp"] = math.floor((perfects + 0.7 * greats
            + 0.3 * goods) / self.total_notes * 10000) / 100
        self.min_scores["mm_tp"] = math.floor((perfects + 0.7 * greats
            + 0.7 * goods) / self.total_notes * 10000) / 100

    def __get_bpm(self, base_bpm: float, ticks: int) -> float:
        return round(base_bpm * 2 * self.chart.time_base / ticks, 2)
