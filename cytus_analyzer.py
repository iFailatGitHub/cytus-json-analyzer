import click
import json
import os
import sys
import pandas as pd
from typing import Any, Dict, List, Tuple

from analysis import Analyzer, NoteDistPlotter
from excel import ExcelWriter
from file_org import Organizer
from paths import CHART_PATH, MAIN_FILE_PATH, OUT_PATH

path_type = click.Path(exists=True, file_okay=False, dir_okay=True)
opt_path_type = click.Path(exists=False, file_okay=False, dir_okay=True)
file_type = click.Path(file_okay=True, dir_okay=False)
default_excel_path = os.path.join(OUT_PATH, "stats.xlsx")
default_dist_path = os.path.join(OUT_PATH, "note_dists")


@click.group("cytus_analyzer")
def cli():
    pass


def is_chart_folder(path: str):
    if not os.path.isdir(path):
        return False

    return any([f.name == "level.json" for f in os.scandir(path)])


@click.command("org_files")
@click.option("--src", "-s",
              type=path_type, default=MAIN_FILE_PATH,
              help="Folder containing all songs, charts, meta, etc.")
@click.option("--dest", "-d",
              type=opt_path_type, default=CHART_PATH,
              help="Folder where all files are grouped")
@click.option("--force", "-f",
              is_flag=True,
              help="Force overwrite any existing song folders")
def org_files(src: str = MAIN_FILE_PATH, dest: str = CHART_PATH, force: bool = False):
    """
        Groups all files into folders based on the song.
    """
    def get_name(song: dict) -> str:
        return "" if song is None else song["song_name"]

    click.echo("Loading song metadata...")
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    organizer = Organizer(src, dest, force)
    label = f"Organizing {len(organizer.song_infos)} songs..."
    with click.progressbar(organizer.song_infos,
                           label=label,
                           item_show_func=get_name) as prog_bar:
        for song_info in prog_bar:
            organizer.organize(song_info)

            if "glitch" in song_info["charts"]:
                organizer.organize(song_info, True)

    click.echo(
        f"{organizer.num_of_charts['success']:03} Chaos Charts organized\n"
        f"{organizer.num_of_charts['success_glitch']:03} Glitch Charts organized\n"
        f"{organizer.num_of_charts['exist']:03} Charts already organized\n"
    )


@click.command("analyze")
@click.argument("chart_ids", type=click.STRING, nargs=-1)
@click.option("--src", "-s",
              type=path_type, default=CHART_PATH,
              help="Folder all levels & charts")
@click.option("--dest", "-d",
              type=file_type, default=default_excel_path,
              help="Folder where all statistics are written")
def analyze(chart_ids: List[str] = [], src: str = CHART_PATH, dest: str = default_excel_path):
    """
        Analyzes charts given a list of IDs. If you want to analyze all levels
        in src, don't input any IDs.
    """
    if len(chart_ids) == 0:
        with os.scandir(src) as dir_items:
            chart_ids = [cid.name for cid in dir_items
                         if is_chart_folder(cid.path)]

    if len(chart_ids) == 0:
        click.echo("No charts in the folder!")

    stat_list = dict()
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)

    with click.progressbar(chart_ids,
                           label=f"Analyzing {len(chart_ids)} charts...",
                           item_show_func=lambda x: x) as prog_bar:
        for chart_id in prog_bar:
            analyzer = Analyzer(src, chart_id)
            analyzer.start()
            stats = analyzer.get_stats_as_json()
            stat_list[chart_id] = stats

    click.echo(f"Done analyzing, now saving to {dest}...")
    dest_folder = os.path.dirname(dest)
    os.makedirs(dest_folder, exist_ok=True)

    stat_df = pd.DataFrame.from_dict(stat_list, orient="index")
    stat_df.index.name = "chart_id"

    excel_writer = ExcelWriter(stat_df, dest)
    excel_writer.format_table()
    excel_writer.close()

    click.echo("Stats successfully saved.")


@click.command("plot_dist")
@click.argument("chart_ids", type=click.STRING, nargs=-1)
@click.option("--src", "-s",
              type=path_type, default=CHART_PATH,
              help="Folder all levels & charts")
@click.option("--dest", "-d",
              type=opt_path_type, default=default_dist_path,
              help="Folder where all note distributions are written")
def plot_dist(chart_ids: List[str] = [], src: str = CHART_PATH, dest: str = default_dist_path):
    """
        Plots the note distribution of charts given a list of IDs.
        If you want to analyze all levels in src, don't input any IDs.
    """
    if len(chart_ids) == 0:
        with os.scandir(src) as dir_items:
            chart_ids = [cid.name for cid in dir_items
                         if is_chart_folder(cid.path)]

    if len(chart_ids) == 0:
        click.echo("No charts in the folder!")

    stat_list = dict()
    src = os.path.abspath(src)
    dest = os.path.abspath(dest)
    os.makedirs(dest, exist_ok=True)

    with click.progressbar(chart_ids,
                           label=f"Plotting {len(chart_ids)} note dists...",
                           item_show_func=lambda x: x) as prog_bar:
        for chart_id in prog_bar:
            dist_plotter = NoteDistPlotter(src, chart_id)
            dist_plotter.count_notes()
            dist_plotter.plot_counts(os.path.join(dest, f"{chart_id}.png"))


cli.add_command(org_files)
cli.add_command(analyze)
cli.add_command(plot_dist)

if __name__ == "__main__":
    if getattr(sys, 'frozen', False):
        cli(sys.argv[1:])  # pylint: disable=too-many-function-args
    else:
        org_files(["-d", "charts/rayark"])
        analyze(["-s", "charts/rayark"])
        plot_dist(["-s", "charts/rayark"])
