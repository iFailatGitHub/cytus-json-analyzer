import click
import json
import os
from typing import List

from analysis import Analyzer
from file_org import Organizer
from paths import CHART_PATH, MAIN_FILE_PATH, OUT_PATH

path_type = click.Path(exists=True, file_okay=False, dir_okay=True)


@click.group("cytus_analyzer")
def cli():
    pass


@click.command("org_files")
@click.option("--src", type=path_type, default=MAIN_FILE_PATH,
              help="Folder containing all songs, charts, meta, etc.")
@click.option("--dest", type=path_type, default=CHART_PATH,
              help="Folder where all files are grouped")
@click.option("--force", is_flag=True,
              help="Force overwrite any existing song folders")
def org_files(src:str=MAIN_FILE_PATH, dest:str=CHART_PATH, force:bool=False):
    """
        Groups all files into folders based on the song.
    """
    click.echo("Loading song metadata...")
    try:
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
    except OSError as err:
        click.echo(str(err))


@click.command("analyze")
@click.argument("chart_ids", type=click.STRING, nargs=-1)
@click.option("--src", type=path_type, default=CHART_PATH,
              help="Folder all levels & charts")
@click.option("--dest", type=path_type, default=OUT_PATH,
              help="Folder where all statistics are written")
def analyze(chart_ids:List[str]=[], src:str=CHART_PATH, dest:str=OUT_PATH):
    """
        Analyzes charts given a list of IDs. If you want to analyze all levels
        in src, don't input any IDs.
    """
    if len(chart_ids) == 0:
        with os.scandir(src) as dir_items:
            chart_ids = [chart_id.name for chart_id in dir_items
                         if chart_id.is_dir()]

    stat_list = []
    
    try:
        with click.progressbar(chart_ids,
                            label=f"Analyzing {len(chart_ids)} charts...",
                            item_show_func=lambda x: x) as prog_bar:
            for chart_id in prog_bar:
                analyzer = Analyzer(src, chart_id)
                analyzer.start()
                stats = analyzer.get_stats_as_json()
                stat_list.append(stats)
    except Exception as err:
        click.echo(str(err))
    else:
        dest = os.path.join(dest, "stats.json")
        json.dump(stat_list, open(dest, "w", encoding="utf8"), indent=4)
        click.echo(f"Analysis successful. Check stats in {dest}.")


cli.add_command(org_files)
cli.add_command(analyze)

if __name__ == "__main__":
    analyze(["crystalpunk.deepdive"])
