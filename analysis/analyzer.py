import json
import math
import os
from enum import Enum
from itertools import tee
from typing import Any, Dict, List, Tuple, TypeVar

from mutagen.mp3 import MP3

from chart import Chart, EventType, LevelInfo, NoteType

EnumT = TypeVar("EnumT", bound=Enum)

def make_dict(enum: EnumT) -> Dict[EnumT, int]:
    return {item: 0 for item in enum}
class Analyzer:
    def __init__(self, folder: str, chart_id: str):
        self.__open_files(folder, chart_id)

        self.note_counts: Dict[NoteType, int] = make_dict(NoteType)
        self.speed_changes: Dict[EventType, int] = make_dict(EventType)
        self.scan_line_stats: Dict[str, Tuple[float]] = {
            "min_bpm" : {"base_bpm": -1, "ticks": -1, "bpm": float("inf")},
            "mode_bpm": {"base_bpm": -1, "ticks": -1, "bpm": -1},
            "max_bpm" : {"base_bpm": -1, "ticks": -1, "bpm": float("-inf")}
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
                f"{self.chart_info['name']} chart."
            ) from err
        
    def start(self):
        self.music_length = MP3(self.level_info.paths["music"]).info.length
        for note in self.chart.note_list:
            self.note_counts[note.note_type] += 1

        self.total_notes = sum(self.note_counts.values())
        self.note_rates = {nt: self.note_counts[nt] / self.total_notes
                           for nt in NoteType}

        self.__get_scan_line_stats()

    def get_stats_as_json(self) -> dict:
        ret = dict()
        ret["meta"] = self.level_info.to_dict().fromkeys([
            "id", "title", "artist", "illustrator"
        ])
        ret["meta"]["length"] = self.music_length
        ret["meta"]["diff"] = self.chart_info.name
        ret["meta"]["level"] = self.chart_info.level

        for stat_type, sl_stat in self.scan_line_stats.items(): 
            ret[stat_type] = sl_stat

        ret["note_counts"] = {
            nt.name.lower(): count for nt, count in self.note_counts.items()
        }
        ret["note_rates"] = {
            nt.name.lower(): rate for nt, rate in self.note_rates.items()
        }
        ret["speed_changes"]: {
            et.name.lower: count for et, count in self.speed_changes.items()
        }

        ret["note_counts"]["total"] = self.total_notes
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

    def __get_bpm(self, base_bpm: float, ticks: int) -> float:
        return round(base_bpm * 2 * self.chart.time_base / ticks, 2)
