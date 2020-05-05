import json
import math
import os
from collections import OrderedDict
from enum import Enum
from itertools import tee
from typing import Any, Dict, List, Tuple, TypeVar

import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_fx
import numpy as np
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis

from chart import Chart, EventType, LevelInfo, NoteType

from .dist_format import count_formats

EnumT = TypeVar("EnumT", bound=Enum)
count_types = ["long_hold", "hold", "tap", "flick", "cdrag", "drag"]


def truncate(num: float, decimals: int) -> float:
    base = 10 ** decimals
    return math.floor(num * base) / base


class NoteDistPlotter:
    def __init__(self, folder: str, chart_id: str):
        self.__open_files(folder, chart_id)

        _, ext = os.path.splitext(self.music_path)
        if ext == ".mp3":
            music = MP3(self.music_path)
        elif ext == ".ogg":
            music = OggVorbis(self.music_path)
        self.music_length = math.ceil(music.info.length)
        self.note_counts = {ct: np.zeros(self.music_length)
                            for ct in count_types}

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
        level_paths = self.level_info.paths
        diff = self.chart_info.name
        try:
            chart_path = level_paths["charts"][diff]
            with open(chart_path, encoding="utf8") as chart_file:
                self.chart = Chart.from_dict(json.load(chart_file))
        except Exception as err:
            raise Exception(
                f"There's something wrong with {chart_id}'s "
                f"{self.chart_info.name} chart."
            ) from err

        if "overrides" in level_paths:
            self.music_path = level_paths["overrides"][diff]
        else:
            self.music_path = level_paths["music"]

    def count_notes(self) -> None:
        for note in self.chart.note_list:
            is_hold = "hold" in note.note_type.name

            if "cdrag" in note.note_type.name:
                count_type = "cdrag"
            elif "drag" in note.note_type.name:
                count_type = "drag"
            else:
                count_type = note.note_type.name

            sec = self._convert_to_sec(note.tick)
            self.note_counts[count_type][sec] += 1

            if note.hold_tick != 0:
                end_tick = note.tick + note.hold_tick
                end_sec = self._convert_to_sec(end_tick)
                for mid_sec in range(sec + 1, end_sec):
                    self.note_counts[count_type][mid_sec] += 1

    def _convert_to_sec(self, tick: int) -> int:
        time_base = self.chart.time_base
        tempos = self.chart.tempo_list

        ms = 0
        tempo = tempos[0]

        for next_tempo in tempos[1:]:
            if tick > next_tempo.tick:
                ms += (next_tempo.tick - tempo.tick) / time_base * tempo.value
                tempo = next_tempo
            else:
                break

        ms += (tick - tempo.tick) / time_base * tempo.value
        return int(math.floor(ms / 1e6 + self.chart.start_offset_time))

    def plot_counts(self, dest: str):
        plt.rc("font", size=16)
        plt.rc('xtick', labelsize=12)
        plt.rc('ytick', labelsize=12)

        fig, ax = plt.subplots(dpi=150)
        xaxis = np.arange(self.music_length)
        xticks = np.arange(0, self.music_length, 15)
        cum_total_counts = np.zeros(self.music_length)

        ax.margins(0.01)
        title = self.level_info.title
        if self.level_info.title_localized:
            title = self.level_info.title_localized

        ax.set_title(f"Note Distribution of {title} ({self.chart_info.name}, "
                     f"Lv. {self.chart_info.difficulty})")
        ax.set_xlabel("Time")
        ax.set_ylabel("No. of Notes")
        ax.set_xticks(xticks)
        ax.set_xticklabels([f"{t//60:02}:{t%60:02}" for t in xticks])

        for ct, counts in self.note_counts.items():
            ax.bar(xaxis, counts, bottom=cum_total_counts,
                   **count_formats[ct])
            cum_total_counts += counts

        avg_note_rate = np.average(cum_total_counts)
        ax.axhline(avg_note_rate, c='black', lw=3)
        note_rate_text = ax.text(0, avg_note_rate + 0.25,
                                 f"Average Note Rate: {avg_note_rate:0.3}",
                                 c='w', weight="bold")
        note_rate_text.set_path_effects(
            [path_fx.withStroke(linewidth=3, foreground='black')])

        combo_ceil = np.max(cum_total_counts)
        ax.legend(loc="upper left", bbox_to_anchor=(1, 1))
        if combo_ceil > self.music_length: # you can thank mekko's funny for this
            fig.set_size_inches(4 * combo_ceil / self.music_length, 8)
        else:
            fig.set_size_inches(4 * self.music_length / combo_ceil, 8)
        fig.savefig(dest, bbox_inches='tight', pad_inches=0.25)
        plt.close(fig)
