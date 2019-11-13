import json
import os
from enum import Enum
from typing import Any, Dict, List, TypeVar

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
        self.scanline_info: Dict[str, Dict[int]] = dict()

        for stat in ["min", "mode", "max"]:
            self.scanline_info[stat] = dict()
            self.scanline_info[stat]["base_bpm"] = 0
            self.scanline_info[stat]["ticks"] = 0
            self.scanline_info[stat]["bpm"] = \
                float('inf') if stat == "min" else -1

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

        self.music_length = MP3(self.level_info.paths["music"]).info.length
        
    def start(self):
        return
