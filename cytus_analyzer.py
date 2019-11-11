import click

from file_org import Organizer
from paths import CHART_PATH, MAIN_FILE_PATH, OUT_PATH

path_type = click.Path(exists=True, file_okay=False, dir_okay=True)
file_type = click.Path(file_okay=True, dir_okay=False)


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
def org_files(src, dest, force):
    """
        Groups all files into folders based on the song.
    """
    click.echo("Loading song metadata...")
    try:
        organizer = Organizer(src, dest, force)

        def get_id(song: dict) -> str:
            return "" if song is None else song["song_name"]

        label = f"Organizing {len(organizer.song_infos)} songs..."
        with click.progressbar(organizer.song_infos,
                            label=label,
                            item_show_func=get_id) as prog_bar:
            for song_info in prog_bar:
                organizer.organize(song_info)

        click.echo(
            f"{organizer.num_of_charts['success']} songs successfully organized\n"
            f"{organizer.num_of_charts['fail']} songs failed to organize\n"
            f"{organizer.num_of_charts['exist']} songs already organized"
        )
    except OSError as err:
        click.echo(str(err))
        return


@click.command("analyze")
@click.argument("ids", type=click.STRING, nargs=-1)
@click.option("--src", type=path_type, default=MAIN_FILE_PATH,
              help="Folder all levels & charts")
@click.option("--dest", type=file_type, default=OUT_PATH,
              help="Folder where all statistics are written")
def analyze(ids, src, dest):
    """
        Analyzes charts given a list of IDs. If you want to analyze all levels
        in the source folder, don't input any IDs.
    """
    pass

cli.add_command(org_files)
cli.add_command(analyze)

if __name__ == "__main__":
    org_files() # pylint: disable=no-value-for-parameter
