import os
from dataclasses import InitVar, dataclass
from typing import Any, List, TypeVar, Callable, Type, cast


T = TypeVar("T")


def from_str(x: Any) -> str:
    assert isinstance(x, str)
    return x


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    assert isinstance(x, list)
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class PathWrapper:
    path: str

    @staticmethod
    def from_dict(obj: Any) -> 'Background':
        assert isinstance(obj, dict)
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
    level: int
    path: str

    @staticmethod
    def from_dict(obj: Any) -> 'ChartInfo':
        assert isinstance(obj, dict)
        chart_type = from_str(obj.get("type"))
        name = from_str(obj.get("name"))
        level = int(from_str(obj.get("level")))
        path = from_str(obj.get("path"))
        return ChartInfo(chart_type, name, level, path)

    def to_dict(self) -> dict:
        result: dict = {}
        result["type"] = from_str(self.chart_type)
        result["name"] = from_str(self.name)
        result["level"] = from_str(str(self.level))
        result["path"] = from_str(self.path)
        return result


@dataclass
class LevelInfo:
    version: int
    chart_id: str
    title: str
    artist: str
    illustrator: str
    music: PathWrapper
    preview: PathWrapper
    background: PathWrapper
    charts: List[ChartInfo]
    folder: InitVar[str]

    def __post_init__(self, folder: str) -> None:
        root_folder = os.path.join(folder, self.chart_id)
        self.paths = dict()
        for item in ["music", "preview", "background"]:
            self.paths[item] = os.path.join(root_folder, getattr(self, item).path)
        
        chart_paths = []
        for chart in self.charts:
            chart_paths.append(os.path.join(root_folder, chart.path))

        self.paths["charts"] = chart_paths

    @staticmethod
    def from_dict(obj: Any, folder: str) -> 'LevelInfo':
        assert isinstance(obj, dict)
        version = from_int(obj.get("version"))
        chart_id = from_str(obj.get("id"))
        title = from_str(obj.get("title"))
        artist = from_str(obj.get("artist"))
        illustrator = from_str(obj.get("illustrator"))
        music = PathWrapper.from_dict(obj.get("music"))
        preview = PathWrapper.from_dict(obj.get("preview"))
        background = PathWrapper.from_dict(obj.get("background"))
        charts = from_list(ChartInfo.from_dict, obj.get("charts"))
        return LevelInfo(version, chart_id, title, artist, illustrator, music, preview, background, charts, folder)

    def to_dict(self) -> dict:
        result: dict = {}
        result["version"] = from_int(self.version)
        result["id"] = from_str(self.chart_id)
        result["title"] = from_str(self.title)
        result["artist"] = from_str(self.artist)
        result["illustrator"] = from_str(self.illustrator)
        result["music"] = to_class(PathWrapper, self.music)
        result["preview"] = to_class(PathWrapper, self.preview)
        result["background"] = to_class(PathWrapper, self.background)
        result["charts"] = from_list(lambda x: to_class(LevelInfo, x), self.charts)
        return result

    def are_paths_valid(self) -> bool:
        for item, path in self.paths.items():
            if item == "charts":
                file_exists = all([os.path.exists(cpath) for cpath in path])
            else:
                file_exists = os.path.exists(path)

            if not file_exists:
                return False

        return True


def level_info_from_dict(s: Any, folder: str) -> LevelInfo:
    return LevelInfo.from_dict(s, folder)


def level_info_to_dict(x: LevelInfo) -> Any:
    return to_class(LevelInfo, x)
