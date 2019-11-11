import os
from typing import Optional

MAIN_FILE_PATH = r'.\\files\\assets'

CHART_PATH = r'.\\files\\charts'
OUT_PATH = r'.\\files\\out'

def get_level_file_paths(folder: str, level_json: dict):
    root_folder = os.path.join(folder, level_json["id"])
    paths = dict()
    for item in ["music", "preview", "background"]:
        paths[item] = os.path.join(root_folder, level_json[item]["path"])
    
    chart_paths = []
    for chart in level_json["charts"]:
        chart_paths.append(os.path.join(root_folder, chart["path"]))

    paths["charts"] = chart_paths

    return paths
