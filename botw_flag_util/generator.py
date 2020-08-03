import ctypes
import json
import time
import zlib
from pathlib import Path

import oead
from bcml.mergers import mubin
from bcml import util as bcmlutil

from . import EXEC_DIR, gdata_file_prefixes, util


def should_not_make_flag(obj) -> bool:
    try:
        # return not obj["!Parameters"]["MakeFlag"]
        return obj["!Parameters"]["NoFlag"]
    except KeyError:
        return False


def revival_bgdata_flag(new_obj, old_obj) -> None:
    old_hash: int = ctypes.c_int32(
        zlib.crc32(f"MainField_{old_obj['UnitConfigName']}_{old_obj['HashId'].v}".encode())
    ).value
    new_name: str = f"MainField_{new_obj['UnitConfigName']}_{new_obj['HashId'].v}"
    new_hash: int = ctypes.c_int32(zlib.crc32(new_name.encode())).value

    if should_not_make_flag(new_obj):
        util.rem_flag_bgdict(old_hash, "revival_bool_data")
        util.rem_flag_bgdict(new_hash, "revival_bool_data")
        return

    entry = oead.byml.Hash()
    entry["DataName"] = new_name
    entry["DeleteRev"] = oead.S32(-1)
    entry["HashValue"] = oead.S32(new_hash)
    entry["InitValue"] = oead.S32(0)
    entry["IsEventAssociated"] = bool("LinksToObj" in new_obj)
    entry["IsOneTrigger"] = False
    entry["IsProgramReadable"] = True
    entry["IsProgramWritable"] = True
    entry["IsSave"] = True
    entry["MaxValue"] = True
    entry["MinValue"] = False
    entry["ResetType"] = oead.S32(1)

    old_flags: set = util.search_bgdict_part(old_hash, "revival_bool_data")
    old_flags |= util.search_bgdict_part(new_hash, "revival_bool_data")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_bgdict(entry, old, "revival_bool_data")
    else:
        util.new_flag_bgdict(entry, "revival_bool_data")


def revival_svdata_flag(new_obj, old_obj) -> None:
    old_hash: int = ctypes.c_int32(
        zlib.crc32(f"MainField_{old_obj['UnitConfigName']}_{old_obj['HashId'].v}".encode())
    ).value
    new_name: str = f"MainField_{new_obj['UnitConfigName']}_{new_obj['HashId'].v}"
    new_hash: int = ctypes.c_int32(zlib.crc32(new_name.encode())).value

    if should_not_make_flag(new_obj):
        util.rem_flag_svdict(old_hash, "game_data.sav")
        util.rem_flag_svdict(new_hash, "game_data.sav")
        return

    entry = oead.byml.Hash()
    entry["DataName"] = new_name
    entry["HashValue"] = oead.S32(new_hash)

    old_flags: set = util.search_svdict_part(old_hash, "game_data.sav")
    old_flags |= util.search_svdict_part(new_hash, "game_data.sav")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_svdict(entry, old, "game_data.sav")
    else:
        util.new_flag_svdict(entry, "game_data.sav")


def isget_bgdata_flag(actor_name: str) -> int:
    flag_name: str = f"IsGet_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    entry = oead.byml.Hash()
    entry["DataName"] = flag_name
    entry["DeleteRev"] = oead.S32(-1)
    entry["HashValue"] = oead.S32(flag_hash)
    entry["InitValue"] = oead.S32(0)
    entry["IsEventAssociated"] = False
    entry["IsOneTrigger"] = True
    entry["IsProgramReadable"] = True
    entry["IsProgramWritable"] = True
    entry["IsSave"] = True
    entry["MaxValue"] = True
    entry["MinValue"] = False
    entry["ResetType"] = oead.S32(0)

    util.new_flag_bgdict(entry, "bool_data")

    return flag_hash


def isget_svdata_flag(actor_name: str) -> int:
    flag_name: str = f"IsGet_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    entry = oead.byml.Hash()
    entry["DataName"] = flag_name
    entry["HashValue"] = oead.S32(flag_hash)

    util.new_flag_svdict(entry, "game_data.sav")

    return flag_hash


def generate_revival_flags(moddir: Path) -> None:
    util.prep_entry_dicts_for_run("revival_bool_data")

    for map_unit in moddir.rglob("**/*_*.smubin"):
        map_start = time.time()
        map_data = oead.byml.from_binary(bcmlutil.decompress(map_unit.read_bytes()))
        map_section = map_unit.stem.split("_")
        stock_map = mubin.get_stock_map((map_section[0], map_section[1]))
        stock_hashes = [obj["HashId"].v for obj in stock_map["Objs"]]
        for obj in map_data["Objs"]:
            if obj["HashId"].v not in stock_hashes and not any(
                excl in obj["UnitConfigName"] for excl in ["Area", "Sphere", "LinkTag"]
            ):
                revival_bgdata_flag(obj, obj)
                revival_svdata_flag(obj, obj)
            elif obj["HashId"].v in stock_hashes and not any(
                excl in obj["UnitConfigName"] for excl in ["Area", "Sphere", "LinkTag"]
            ):
                stock_obj = stock_map["Objs"][stock_hashes.index(obj["HashId"].v)]
                name_changed = obj["UnitConfigName"] != stock_obj["UnitConfigName"]
                event_assoc_changed = bool("LinksToObj" in obj) != bool("LinksToObj" in stock_obj)
                if name_changed or event_assoc_changed:
                    revival_bgdata_flag(obj, stock_obj)
                    if name_changed:
                        revival_svdata_flag(obj, stock_obj)
        print(f"Finished processing {map_unit.name} in {time.time() - map_start} seconds...")


def generate_item_flags(moddir: Path) -> None:
    util.prep_entry_dicts_for_run("bool_data")

    mod_bg_isget: set = set()
    mod_sv_isget: set = set()
    for item_actor in moddir.rglob("**/Item_*.sbactorpack"):
        mod_bg_isget.add(isget_bgdata_flag(str(item_actor.stem)))
        mod_sv_isget.add(isget_svdata_flag(str(item_actor.stem)))
    for armor_actor in moddir.rglob("**/Armor_*.sbactorpack"):
        mod_bg_isget.add(isget_bgdata_flag(str(armor_actor.stem)))
        mod_sv_isget.add(isget_svdata_flag(str(armor_actor.stem)))
    for weapon_actor in moddir.rglob("**/Weapon_*.sbactorpack"):
        mod_bg_isget.add(isget_bgdata_flag(str(weapon_actor.stem)))
        mod_sv_isget.add(isget_svdata_flag(str(weapon_actor.stem)))

    bg_isget: set = set()
    bg_isget |= util.search_bgdict_part("IsGet_Item_", "bool_data")
    bg_isget |= util.search_bgdict_part("IsGet_Armor_", "bool_data")
    bg_isget |= util.search_bgdict_part("IsGet_Weapon_", "bool_data")
    sv_isget: set = set()
    sv_isget |= util.search_svdict_part("IsGet_Item_", "game_data.sav")
    sv_isget |= util.search_svdict_part("IsGet_Armor_", "game_data.sav")
    sv_isget |= util.search_svdict_part("IsGet_Weapon_", "game_data.sav")

    f = EXEC_DIR / "data" / "vanilla_hash.json"
    vanilla_isget_hashes = set(json.loads(f.read_text(), encoding="utf-8")["isget_hash"])
    bg_isget_todelete = bg_isget - (mod_bg_isget | vanilla_isget_hashes)
    sv_isget_todelete = sv_isget - (mod_sv_isget | vanilla_isget_hashes)

    for hash in bg_isget_todelete:
        util.rem_flag_bgdict(hash, "bool_data")
    for hash in sv_isget_todelete:
        util.rem_flag_svdict(hash, "game_data.sav")


def generate(args):
    directory: Path = Path(args.directory)
    if not args.actor and not args.revival:
        print("No flag options were chosen! Use -a and/or -r to generate flags.")
        exit()

    if args.revival:
        generate_revival_flags(directory)
    if args.actor:
        generate_item_flags(directory)

    write_start = time.time()
    files_to_write: list = []
    datas_to_write: list = []
    if total_new_bg + total_mod_bg + total_del_bg > 0:
        files_to_write.append("GameData/gamedata.ssarc")
        datas_to_write.append(bcmlutil.compress(make_new_gamedata(big_endian)))
        print(f"Wrote game data flag data...")
    else:
        print(f"No game data flag data to write. Skipping...")

    if total_new_sv + total_mod_sv + total_del_sv > 0:
        files_to_write.append("GameData/savedataformat.ssarc")
        datas_to_write.append(bcmlutil.compress(make_new_savedata(big_endian)))
        print(f"Wrote save flag data...")
    else:
        print(f"No save flag data to write. Skipping...")
    util.inject_files_into_bootup(bootup_path, files_to_write, datas_to_write)
    print(f"Injected to Bootup.pack...")
    print(f"Flag writing took {time.time() - write_start} seconds...\n")
