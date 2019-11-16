import click
import json
import os
import pandas as pd
from typing import Any, Dict, List, Tuple

from analysis import Analyzer
from excel import ExcelWriter
from file_org import Organizer
from paths import CHART_PATH, MAIN_FILE_PATH, OUT_PATH

path_type = click.Path(exists=True, file_okay=False, dir_okay=True)
file_type = click.Path(file_okay=True, dir_okay=False)
default_excel_path = os.path.join(OUT_PATH, "stats.xlsx")


@click.group("cytus_analyzer")
def cli():
    pass


@click.command("org_files")
@click.option("--src", "-s",
              type=path_type, default=MAIN_FILE_PATH,
              help="Folder containing all songs, charts, meta, etc.")
@click.option("--dest", "-d",
              type=path_type, default=CHART_PATH,
              help="Folder where all files are grouped")
@click.option("--force", "-f",
              is_flag=True,
              help="Force overwrite any existing song folders")
def org_files(src: str = MAIN_FILE_PATH, dest: str = CHART_PATH, force: bool = False):
    """
        Groups all files into folders based on the song.
    """
    click.echo("Loading song metadata...")
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)

    organizer = Organizer(src, dest, force)

    def get_name(song: dict) -> str:
        return "" if song is None else song["song_name"]

    label = f"Organizing {len(organizer.song_infos)} songs..."
    with click.progressbar(organizer.song_infos,
                            label=label,
                            item_show_func=get_name) as prog_bar:
        for song_info in prog_bar:
            organizer.organize(song_info)

    click.echo(
        f"{organizer.num_of_charts['success']} songs successfully organized\n"
        f"{organizer.num_of_charts['fail']} songs failed to organize\n"
        f"{organizer.num_of_charts['exist']} songs already organized"
    )


@click.command("analyze")
@click.argument("chart_ids", type=click.STRING, nargs=-1)
@click.option("--src", "-s",
              type=path_type, default=CHART_PATH,
              help="Folder all levels & charts")
@click.option("--dest", "-d",
              type=file_type, default=default_excel_path,
              help="Folder where all statistics are written")
def analyze(chart_ids: List[str] = [], src: str = CHART_PATH, dest: str = OUT_PATH):
    """
        Analyzes charts given a list of IDs. If you want to analyze all levels
        in src, don't input any IDs.
    """
    if len(chart_ids) == 0:
        with os.scandir(src) as dir_items:
            chart_ids = [chart_id.name for chart_id in dir_items
                         if chart_id.is_dir()]

    stat_list = dict()
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)

    with click.progressbar(chart_ids,
                           label=f"Analyzing {len(chart_ids)} charts...",
                           item_show_func=lambda x: x) as prog_bar:
        for chart_id in prog_bar:
            analyzer = Analyzer(src, chart_id)
            analyzer.start()
            stats = analyzer.get_stats_as_json()
            stat_list[chart_id] = stats

    click.echo(f"Done analyzing, now saving to {dest}...")
    stat_df = pd.DataFrame.from_dict(stat_list, orient="index")
    stat_df.index.name = "chart_id"

    excel_writer = ExcelWriter(stat_df, dest)
    excel_writer.format_table()
    excel_writer.close()

    dest_folder = os.path.dirname(dest)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder, exist_ok=True)

    click.echo("Stats successfully saved.")

cli.add_command(org_files)
cli.add_command(analyze)

if __name__ == "__main__":
    analyze([])
