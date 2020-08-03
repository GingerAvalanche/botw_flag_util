import argparse
import shutil
import time
from pathlib import Path

from bcml import util as bcmlutil
from . import util
from .finder import find
from .generator import generate


def main() -> None:
    parser = argparse.ArgumentParser(description="Tool for managing flags in LoZ:BotW")

    subparsers = parser.add_subparsers(dest="command", help="Command")
    subparsers.required = True

    f_parser = subparsers.add_parser(
        "find", description="Search for flags in Bootup.pack", aliases=["f"]
    )
    f_parser.add_argument("directory", help="The root folder of your mod")
    f_parser.add_argument(
        "flag_name", help="The name (or part of the name) of the flag to search for"
    )
    f_parser.set_defaults(func=lambda a: find(a))

    g_parser = subparsers.add_parser(
        "generate", description="Builds GameData and SaveGameData flags", aliases=["g"]
    )
    g_parser.add_argument("directory", help="The root folder of your mod")
    g_parser.add_argument(
        "-a", "--actor", help="Generate IsGet_/compendium flags for actors", action="store_true",
    )
    g_parser.add_argument(
        "-r", "--revival", help="Generate revival flags for actor instances", action="store_true",
    )
    g_parser.set_defaults(func=lambda a: generate(a))

    for p in [f_parser, g_parser]:
        p.add_argument(
            "-b", "--bigendian", help="Use big endian mode (for Wii U)", action="store_true",
        )
        p.add_argument(
            "-v", "--verbose", help="Give verbose after-action report", action="store_true",
        )

    args = parser.parse_args()
    directory: Path = Path(args.directory)
    if not (directory / "content").exists():
        print(
            f"{directory} is not the root folder of your mod. Please try again and enter the root directory of your mod."
        )
        return
    bootup_path: Path = directory / "content" / "Pack" / "Bootup.pack"
    if not bootup_path.exists():
        bootup_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(bcmlutil.get_game_file("Pack/Bootup.pack"), bootup_path)
    bootup_dir = str(bootup_path).replace("\\", "/")

    util.make_bgdict(bootup_dir)
    util.make_svdict(bootup_dir)

    args.func(args)

    write_start = time.time()
    files_to_write: list = []
    files_to_write.append("GameData/gamedata.ssarc")
    files_to_write.append("GameData/savedataformat.ssarc")
    datas_to_write: list = []
    datas_to_write.append(bcmlutil.compress(util.make_new_gamedata(args.bigendian)))
    datas_to_write.append(bcmlutil.compress(util.make_new_savedata(args.bigendian)))
    util.inject_files_into_bootup(bootup_path, files_to_write, datas_to_write)
    write_time = time.time() - write_start

    if util.get_total_changes() > 0:
        print(f"\nFlag writing took {write_time} seconds...\n")
        print(f"{util.get_new_bgdict_changes()} New Game Data Entries")
        print(f"{util.get_mod_bgdict_changes()} Modified Game Data Entries")
        print(f"{util.get_del_bgdict_changes()} Deleted Game Data Entries")
        print(f"{util.get_new_svdict_changes()} New Save Data Entries")
        print(f"{util.get_mod_svdict_changes()} Modified Save Data Entries")
        print(f"{util.get_del_svdict_changes()} Deleted Save Data Entries")

        if args.verbose:
            print(util.get_verbose_output())
    else:
        print("No changes were made.")
