import json
import os
import re
import shutil
import time
from dataclasses import InitVar, dataclass, field
from typing import Dict, List

from chart import LevelInfo
from .titles import TITLE_OVERRIDES

FIRST_CAP_REGEX = re.compile(r'(.)([A-Z][a-z]+)')
ALL_CAPS_REGEX = re.compile(r'([a-z0-9])([A-Z])')
FEAT_REGEX = re.compile(r'(?i)feat(?:\.|\s).*')
PARENS_REGEX = re.compile(r'\([^\(\)]*\)')

@dataclass
class Organizer:
    src: str
    dest: str
    force: bool

    def __post_init__(self):
        if not os.path.exists(self.dest):
            os.makedirs(self.dest)

        song_pack_path = os.path.join(
            self.src, "meta", "song_pack_data.json")
        ex_pack_path = os.path.join(
            self.src, "meta", "expansion_pack_data.json")

        try:
            with open(song_pack_path, encoding="utf8") as song_pack_file, \
                    open(ex_pack_path, encoding="utf8") as ex_pack_file:
                song_pack_data = json.load(song_pack_file)
                ex_pack_data = json.load(ex_pack_file)
                song_pack_file.close()
                ex_pack_file.close()

                song_pack_data = self.format_keys(
                    song_pack_data["offline_song_pack_list"])
                ex_pack_data = self.format_keys(
                    ex_pack_data["ExpansionPackList"])
                self._get_songs(song_pack_data, ex_pack_data)
        except Exception as err:
            raise Exception(
                f"There's something wrong with {song_pack_path} and "
                f"{ex_pack_path}. Check those files to make sure they exist and "
                f"they are valid JSON files."
            )

        self.num_of_charts = {
            "success": 0,
            "fail": 0,
            "exist": 0
        }

    def _get_songs(self, song_pack_data, ex_pack_data):
        self.song_infos: List[dict] = []

        for song_pack_info in song_pack_data:
            for song_info in song_pack_info["song_info_list"]:
                song_info = self.format_keys(song_info)
                song_info["expansion_pack"] = "base"
                song_info["song_pack"] = song_pack_info["song_pack_name"]
                self.song_infos.append(song_info)

        for ex_pack_info in ex_pack_data:
            for song_info in ex_pack_info["song_info_list"]:
                song_info = self.format_keys(song_info)
                song_info["expansion_pack"] = ex_pack_info["expansion_pack_name"]

                for song_pack_info in song_pack_data:
                    if song_info["song_pack_id"] == song_pack_info["song_pack_id"]:
                        song_info["song_pack"] = song_pack_info["song_pack_name"]
                        break
                else:
                    song_info["song_pack"] = "unknown"

                self.song_infos.append(song_info)

    @staticmethod
    def format_keys(obj):
        if type(obj) is dict:
            ret = dict()
            for key, value in obj.items():
                new_key = FIRST_CAP_REGEX.sub(r'\1_\2', key)
                new_key = ALL_CAPS_REGEX.sub(r'\1_\2', key).lower()
                ret[new_key] = Organizer.format_keys(value)
        elif type(obj) is list:
            ret = [Organizer.format_keys(item) for item in obj]
        else:
            ret = obj

        return ret

    def organize(self, song_info: dict):
        chart_id = self._create_chart_id(song_info)
        chart_folder = os.path.join(self.dest, chart_id)
        if not os.path.exists(chart_folder):
            os.makedirs(chart_folder)

        level_json_path = os.path.join(self.dest, chart_id, "level.json")

        if not self.force:
            try:
                with open(level_json_path, encoding="utf8") as level_json_file:
                    level_info = LevelInfo.from_dict(json.load(level_json_file), self.dest) 

                    if level_info.are_paths_valid():
                        self.num_of_charts["exist"] += 1
                        return
                    else:
                        raise OSError(
                            "One of the paths in the level.json is invalid"
                        )
            except Exception:
                pass

        level_json = self._create_level_json(song_info, chart_id)
        level_info = LevelInfo.from_dict(level_json, self.dest)
        try:
            self._copy_chart_files(song_info["song_id"], level_info)
        except OSError as err:
            raise OSError(
                f"Cannot find one of the required files for the song "
                f"\"{level_json['title']}\". Aborting organization..."
            ) from err

        with open(level_json_path, "w", encoding="utf8") as level_json_file:
            json.dump(level_json, level_json_file, indent=4)
        self.num_of_charts["success"] += 1

    def _create_chart_id(self, song_info: dict):
        title_id = TITLE_OVERRIDES.get(
            song_info["song_id"], song_info["song_name"])

        if title_id == song_info["song_name"]:
            title_id = PARENS_REGEX.sub("", title_id)
            title_id = FEAT_REGEX.sub("", title_id)
            title_id = "".join([letter.lower() for letter in title_id
                                if letter.isalnum()])

        char_id = song_info["song_pack"]
        if char_id == "NEKO#\u03a6\u03c9\u03a6":
            char_id = "nekoowo"
        else:
            char_id = song_info["song_pack"].replace(" ", "")
            char_id = char_id.replace("_", "")
            char_id = char_id.lower()

        return f"{char_id}.{title_id}"

    def _create_level_json(self, song_info: dict, chart_id: str) -> dict:
        level_json = dict()

        level_json["version"] = 1
        level_json["id"] = chart_id

        level_json["title"] = song_info["song_name"]
        level_json["artist"] = song_info["artist"]
        level_json["artist_source"] = "https://www.rayark.com/en/games/cytus2/"
        level_json["illustrator"] = "Rayark Inc."
        level_json["illustrator_source"] = "https://www.rayark.com/en/games/cytus2/"
        level_json["charter"] = song_info["song_pack"]

        level_json["music"] = {"path": "music.mp3"}
        level_json["preview"] = {"path": "preview.mp3"}
        level_json["background"] = {"path": "background.png"}
        level_json["charts"] = []

        for diff, song_chart_info in song_info["charts"].items():
            chart_info = {
                "type": diff,
                "name": diff.title(),
                "level": song_chart_info["level"],
                "path": f"chart.{diff}.txt"
            }
            if diff == "chaos" or diff == "glitch":
                chart_info["type"] = "extreme"

            level_json["charts"].append(chart_info)

        return level_json

    def _copy_chart_files(self, old_id: str, level_json: LevelInfo):
        file_paths = level_json.paths
        for item, path in file_paths.items():
            if item == "charts":
                for idx, chart_path in enumerate(path):
                    orig_chart_fname = f"{old_id}_{idx}.txt"
                    orig_chart_path = os.path.join(
                        self.src, item, orig_chart_fname)
                    shutil.copy2(orig_chart_path, chart_path)
            elif item == "background":
                orig_path = os.path.join(self.src, item, f"{old_id}.png")
                shutil.copy2(orig_path, path)
            elif item == "music" or item == "preview":
                orig_path = os.path.join(self.src, item, f"{old_id}.mp3")
                shutil.copy2(orig_path, path)
