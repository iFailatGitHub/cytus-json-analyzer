import json
import os
from dataclasses import InitVar, dataclass

from paths import get_level_file_paths

class Analyzer:
    def __init__(self, folder, chart_id):
        level_json_path = os.path.join(folder, chart_id)

        try:
            with open(level_json_path, encoding="utf8") as level_json_file:
                self.level_info = json.load(level_json_file)
                self.file_paths = get_level_file_paths(folder, self.level_info)
        except Exception as err:
            raise Exception(
                f"There's something wrong with {chart_id}'s level.json"
            ) from err
