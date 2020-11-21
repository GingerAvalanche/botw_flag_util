from pathlib import Path

from . import util
from .flag import BFUFlag
from .store import FlagStore


def find(args):
    util.root_dir(args.directory)
    gamedata_sarc = util.get_gamedata_sarc()
    bgdata = FlagStore()
    for bgdata_name, bgdata_hash in map(util.unpack_oead_file, gamedata_sarc.get_files()):
        bgdata.add_flags_from_Hash(bgdata_name, bgdata_hash)

    search_name = args.flag_name
    found: dict = {}
    numfound = 0
    numsv = 0
    for ftype in util.BGDATA_TYPES:
        found[ftype] = bgdata.find_all(ftype, search_name)
        numfound += len(found[ftype])
    for _, flags in found.items():
        for flag in flags:
            if flag.is_save:
                numsv += 1

    while True:
        print(
            f"\n{numfound} gamedata flags and {numsv} savedata flags were found that matched {search_name}."
        )
        print("\nPlease choose an option:")
        print("v - View the full flag names, files, and indices in their files")
        print("d - Delete these flags and exit")
        print("x - Exit without deleting the flags")
        selection = input("(v/d/x):")

        if selection == "v":
            for ftype, flags in found.items():
                for flag in flags:
                    if flag.is_save():
                        string = f"{flag.get_name()} in {ftype} and in game_data.sav"
                    else:
                        string = f"{flag.get_name()} in {ftype}"
                    print(string)

        elif selection == "d":
            for ftype, flags in found.items():
                for flag in flags:
                    bgdata.remove(ftype, hash)
            write_start = time.time()
            files_to_write: list = []
            files_to_write.append("GameData/gamedata.ssarc")
            files_to_write.append("GameData/savedataformat.ssarc")
            orig_files = util.get_last_two_savedata_files(directory)
            datas_to_write: list = []
            datas_to_write.append(
                oead.yaz0.compress(util.make_new_gamedata(bgdata, args.bigendian))
            )
            datas_to_write.append(
                oead.yaz0.compress(util.make_new_savedata(bgdata, args.bigendian, orig_files))
            )
            util.inject_files_into_bootup(bootup_path, files_to_write, datas_to_write)
            write_time = time.time() - write_start
            return

        elif selection == "x":
            return
