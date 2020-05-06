import os
from dataclasses import InitVar, dataclass
from typing import Any, List, Optional

from chart.type_helper import (from_int, from_list, from_none, from_str,
                               from_union, to_class)


@dataclass
class PathWrapper:
    path: str

    @staticmethod
    def from_dict(obj: Any) -> 'PathWrapper':
        assert isinstance(obj, dict), "Object is not a dict."
        path = from_str(obj.get("path"))
        return PathWrapper(path)

    def to_dict(self) -> dict:
        result: dict = {}
        result["path"] = from_str(self.path)
        return result


@dataclass
class ChartInfo:
    chart_type: str
    name: str
    difficulty: int
    path: str
    music_override: Optional[PathWrapper]

    @staticmethod
    def from_dict(obj: Any) -> 'ChartInfo':
        assert isinstance(obj, dict), "Object is not a dict."
        chart_type = from_str(obj.get("type"))
        name = from_str(obj.get("name", chart_type.title()))
        difficulty = from_int(obj.get("difficulty"))
        path = from_str(obj.get("path"))
        music_override = from_union([PathWrapper.from_dict, from_none], 
                                    obj.get("music_override"))
        return ChartInfo(chart_type, name, difficulty, path, music_override)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = from_str(self.chart_type)
        result["name"] = from_str(self.name)
        result["difficulty"] = from_str(str(self.difficulty))
        result["path"] = from_str(self.path)
        result["music_override"] = from_union([lambda x: to_class(PathWrapper, x), from_none], 
                                              self.music_override)
        return result


@dataclass
class LevelInfo:
    version: int
    schema_version: int
    chart_id: str
    title: str
    title_localized: str
    artist: str
    artist_source: str
    illustrator: str
    illustrator_source: str
    charter: str
    music: PathWrapper
    music_preview: PathWrapper
    background: PathWrapper
    charts: List[ChartInfo]
    folder: InitVar[str]

    def __post_init__(self, folder: str) -> None:
        root_folder = os.path.join(folder, self.chart_id)
        self.paths = dict()
        for item in ["music", "music_preview", "background"]:
            self.paths[item] = os.path.join(
                root_folder, getattr(self, item).path)

        chart_paths = {}
        override_paths = {}
        for chart in self.charts:
            chart_path = os.path.join(root_folder, chart.path)
            chart_paths[chart.name] = chart_path
            override = chart.music_override
            if override is not None:
                override_path = os.path.join(root_folder, override.path)
                override_paths[chart.name] = override_path

        self.paths["charts"] = chart_paths
        if override_paths:
            self.paths["overrides"] = override_paths

    @staticmethod
    def from_dict(obj: Any, folder: str) -> 'LevelInfo':
        assert isinstance(obj, dict), "Object is not a dict."
        version = from_int(obj.get("version"))
        schema_version = from_int(obj.get("schema_version"))
        chart_id = from_str(obj.get("id"))
        title = from_str(obj.get("title"))
        title_localized = from_union([from_str, from_none], obj.get("title_localized"))
        artist = from_str(obj.get("artist"))
        artist_source = from_str(obj.get("artist_source"))
        illustrator = from_str(obj.get("illustrator"))
        illustrator_source = from_str(obj.get("illustrator_source"))
        charter = from_str(obj.get("charter"))
        music = PathWrapper.from_dict(obj.get("music"))
        music_preview = PathWrapper.from_dict(obj.get("music_preview"))
        background = PathWrapper.from_dict(obj.get("background"))
        charts = from_list(ChartInfo.from_dict, obj.get("charts"))
        return LevelInfo(version, schema_version, chart_id, title, title_localized, 
                         artist, artist_source, illustrator, illustrator_source,
                         charter, music, music_preview, background, charts,
                         folder)

    def to_dict(self) -> dict:
        result: dict = {}
        result["version"] = from_int(self.version)
        result["schema_version"] = from_int(self.schema_version)
        result["id"] = from_str(self.chart_id)
        result["title"] = from_str(self.title)
        result["title_localized"] = from_union([from_str, from_none], 
                                               self.title_localized)
        result["artist"] = from_str(self.artist)
        result["artist_source"] = from_str(self.artist_source)
        result["illustrator"] = from_str(self.illustrator)
        result["illustrator_source"] = from_str(self.illustrator_source)
        result["charter"] = from_str(self.charter)
        result["music"] = to_class(PathWrapper, self.music)
        result["music_preview"] = to_class(PathWrapper, self.music_preview)
        result["background"] = to_class(PathWrapper, self.background)
        result["charts"] = from_list(
            lambda x: to_class(ChartInfo, x), self.charts)
        return result

    def are_paths_valid(self) -> bool:
        for item, path in self.paths.items():
            if item == "charts" or item == "overrides":
                file_exists = all([os.path.exists(cpath) for cpath in path.values()])
            else:
                file_exists = os.path.exists(path)

            if not file_exists:
                return False

        return True


def level_info_from_dict(s: Any, folder: str) -> LevelInfo:
    return LevelInfo.from_dict(s, folder)


def level_info_to_dict(x: LevelInfo) -> Any:
    return to_class(LevelInfo, x)
