import ctypes
import json
import time
import zlib
from pathlib import Path

import oead
from bcml.mergers import mubin
from bcml import util as bcmlutil

from . import EXEC_DIR, gdata_file_prefixes, util


current_map: str = ""


def should_not_make_flag(obj) -> bool:
    try:
        if "LinkTag" in obj["UnitConfigName"]:
            makeflag = obj["!Parameters"]["MakeSaveFlag"].v
            if makeflag == 0 and not "SaveFlag" in obj["!Parameters"]:
                return True
            elif obj["!Parameters"]["IncrementSave"]:
                return True  # revival flags are bools, IncrementSave means s32
            else:
                return False
    except KeyError:
        return True
        # the unchecked keys above are mandatory so this shouldn't be necessary...

    try:
        # return not obj["!Parameters"]["MakeFlag"]
        return obj["!Parameters"]["NoFlag"]
    except KeyError:
        return False


def get_flag_name(obj, fieldname: str) -> str:
    if "LinkTag" in obj["UnitConfigName"]:
        makeflag = obj["!Parameters"]["MakeSaveFlag"].v
        if makeflag == 0 and "SaveFlag" in obj["!Parameters"]:
            return obj["!Parameters"]["SaveFlag"]
            # should_not_make_flag() will stop cases where `not "SaveFlag" in obj["!Parameters"]`
        elif makeflag == 1:
            if not current_map:
                raise ValueError(
                    "A LinkTag was created with MakeSaveFlag 1 in MainField, this is not valid"
                )
            return f"Clear_{current_map}"
        elif makeflag == 2:
            raise ValueError(
                "A LinkTag was created with MakeSaveFlag 2 but can't figure out nearest dungeon name"
            )
    return f"{fieldname}_{obj['UnitConfigName']}_{obj['HashId'].v}"


def revival_bgdata_flag(new_obj, old_obj, fieldname: str, resettype: int = 1) -> None:
    old_hash: int = ctypes.c_int32(
        zlib.crc32(f"{fieldname}_{old_obj['UnitConfigName']}_{old_obj['HashId'].v}".encode())
    ).value
    new_name: str = get_flag_name(new_obj, fieldname)
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
    entry["ResetType"] = oead.S32(resettype)

    old_flags: set = util.search_bgdict_part(old_hash, "revival_bool_data")
    old_flags |= util.search_bgdict_part(new_hash, "revival_bool_data")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_bgdict(entry, old, "revival_bool_data")
    else:
        util.new_flag_bgdict(entry, "revival_bool_data")


def revival_svdata_flag(new_obj, old_obj, fieldname: str) -> None:
    old_hash: int = ctypes.c_int32(
        zlib.crc32(f"{fieldname}_{old_obj['UnitConfigName']}_{old_obj['HashId'].v}".encode())
    ).value
    new_name: str = f"{fieldname}_{new_obj['UnitConfigName']}_{new_obj['HashId'].v}"
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


def generate_revival_flags_for_map(
    map_data: oead.byml.Hash, stock_map: oead.byml.Hash, fieldname: str, resettype: int
) -> dict:
    r: dict = {"ignore": set(), "delete": set()}

    map_hashes = [obj["HashId"].v for obj in map_data["Objs"]]
    stock_hashes = [obj["HashId"].v for obj in stock_map["Objs"]]
    for obj in map_data["Objs"]:
        r["ignore"].add(
            ctypes.c_int32(
                zlib.crc32(f"{fieldname}_{obj['UnitConfigName']}_{obj['HashId'].v}".encode())
            ).value
        )
        if obj["HashId"].v not in stock_hashes and not "Area" in obj["UnitConfigName"]:
            revival_bgdata_flag(obj, obj, fieldname, resettype)
            revival_svdata_flag(obj, obj, fieldname)
        elif obj["HashId"].v in stock_hashes and not "Area" in obj["UnitConfigName"]:
            stock_obj = stock_map["Objs"][stock_hashes.index(obj["HashId"].v)]
            name_changed = obj["UnitConfigName"] != stock_obj["UnitConfigName"]
            event_assoc_changed = bool("LinksToObj" in obj) != bool("LinksToObj" in stock_obj)
            if name_changed or event_assoc_changed:
                revival_bgdata_flag(obj, stock_obj, fieldname, resettype)
                if name_changed:
                    revival_svdata_flag(obj, stock_obj, fieldname)
    for obj in stock_map["Objs"]:
        if obj["HashId"].v not in map_hashes:
            old_hash: int = ctypes.c_int32(
                zlib.crc32(f"{fieldname}_{obj['UnitConfigName']}_{obj['HashId'].v}".encode())
            ).value
            r["delete"].add(old_hash)

    return r


def generate_revival_flags(moddir: Path, resettypes: list) -> None:
    util.prep_entry_dicts_for_run("revival_bool_data")
    ignore_hashes: set = set()
    delete_hashes: set = set()

    if not resettypes[0] == -1:
        for map_unit in moddir.rglob("**/*_*.smubin"):
            map_start = time.time()
            map_data = oead.byml.from_binary(bcmlutil.decompress(map_unit.read_bytes()))
            map_section = map_unit.stem.split("_")
            stock_map = mubin.get_stock_map((map_section[0], map_section[1]))
            temp = generate_revival_flags_for_map(map_data, stock_map, "MainField", resettypes[0])
            print(f"Finished processing {map_unit.name} in {time.time() - map_start} seconds...")
            ignore_hashes |= temp["ignore"]
            delete_hashes |= temp["delete"]
    if not resettypes[1] == -1:
        for map_pack in moddir.glob("content/Pack/Dungeon*.pack"):
            current_map = map_pack.stem
            pack_data = oead.Sarc(map_pack.read_bytes())
            stock_pack = oead.Sarc(bcmlutil.get_game_file(map_pack).read_bytes())
            map_types = ("_Static", "_Dynamic")
            for map_type in map_types:
                map_start = time.time()
                map_name = f"{map_pack.stem}{map_type}.smubin"
                map_data = oead.byml.from_binary(
                    oead.yaz0.decompress(
                        pack_data.get_file(f"Map/CDungeon/{map_pack.stem}/{map_name}").data
                    )
                )
                stock_map = oead.byml.from_binary(
                    oead.yaz0.decompress(
                        stock_pack.get_file(f"Map/CDungeon/{map_pack.stem}/{map_name}").data
                    )
                )
                temp = generate_revival_flags_for_map(
                    map_data, stock_map, "CDungeon", resettypes[1]
                )
                print(f"Finished processing {map_name} in {time.time() - map_start} seconds...")
                ignore_hashes |= temp["ignore"]
                delete_hashes |= temp["delete"]
            current_map = ""
            # ^ unnecessary given that it's updated every loop, but we rely on it possibly being
            # empty for determining whether LinkTags are valid, so it's better to be safe
    for hash in delete_hashes:
        if hash not in ignore_hashes:
            util.rem_flag_bgdict(hash, "revival_bool_data")
            util.rem_flag_svdict(hash, "game_data.sav")


def actor_bool_bgdata_flag(flag_type: str, actor_name: str, cat: int = -1) -> int:
    flag_name: str = f"{flag_type}_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    entry = oead.byml.Hash()
    if not cat == -1:
        entry["Category"] = oead.S32(cat)
    entry["DataName"] = flag_name
    entry["DeleteRev"] = oead.S32(-1)
    entry["HashValue"] = oead.S32(flag_hash)
    entry["InitValue"] = oead.S32(0)
    entry["IsEventAssociated"] = False
    entry["IsOneTrigger"] = True if flag_type == "IsGet" else False
    entry["IsProgramReadable"] = True
    entry["IsProgramWritable"] = True
    entry["IsSave"] = True
    entry["MaxValue"] = True
    entry["MinValue"] = False
    entry["ResetType"] = oead.S32(0)

    old_flags: set = util.search_bgdict_part(flag_hash, "bool_data")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_bgdict(entry, old, "bool_data")
    else:
        util.new_flag_bgdict(entry, "bool_data")

    return flag_hash


def actor_s32_bgdata_flag(flag_type: str, actor_name: str) -> int:
    flag_name: str = f"{flag_type}_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    entry = oead.byml.Hash()
    entry["DataName"] = flag_name
    entry["DeleteRev"] = oead.S32(-1)
    entry["HashValue"] = oead.S32(flag_hash)
    entry["InitValue"] = oead.S32(0)
    entry["IsEventAssociated"] = False
    entry["IsOneTrigger"] = False
    entry["IsProgramReadable"] = True
    entry["IsProgramWritable"] = True
    entry["IsSave"] = True
    entry["MaxValue"] = oead.S32(2147483647)
    entry["MinValue"] = oead.S32(0)
    entry["ResetType"] = oead.S32(0)

    old_flags: set = util.search_bgdict_part(flag_hash, "s32_data")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_bgdict(entry, old, "s32_data")
    else:
        util.new_flag_bgdict(entry, "s32_data")

    return flag_hash


def actor_svdata_flag(flag_type: str, actor_name: str) -> int:
    flag_name: str = f"{flag_type}_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    entry = oead.byml.Hash()
    entry["DataName"] = flag_name
    entry["HashValue"] = oead.S32(flag_hash)

    old_flags: set = util.search_svdict_part(flag_hash, "game_data.sav")

    if len(old_flags) > 0:
        for old in old_flags:
            util.mod_flag_svdict(entry, old, "game_data.sav")
    else:
        util.new_flag_svdict(entry, "game_data.sav")

    return flag_hash


def generate_item_flags(moddir: Path) -> None:
    util.prep_entry_dicts_for_run("bool_data")
    util.prep_entry_dicts_for_run("s32_data")

    mod_bg: set = set()
    mod_sv: set = set()
    for item_actor in moddir.rglob("**/Item_*.sbactorpack"):
        mod_bg.add(actor_bool_bgdata_flag("IsNewPictureBook", str(item_actor.stem)))
        mod_bg.add(actor_bool_bgdata_flag("IsRegisteredPictureBook", str(item_actor.stem), 4))
        mod_bg.add(actor_bool_bgdata_flag("IsGet", str(item_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("PictureBookSize", str(item_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsNewPictureBook", str(item_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsRegisteredPictureBook", str(item_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsGet", str(item_actor.stem)))
        mod_sv.add(actor_svdata_flag("PictureBookSize", str(item_actor.stem)))
    for armor_actor in moddir.rglob("**/Armor_*.sbactorpack"):
        mod_bg.add(actor_bool_bgdata_flag("IsGet", str(armor_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("EquipTime", str(armor_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("PorchTime", str(armor_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsGet", str(armor_actor.stem)))
        mod_sv.add(actor_svdata_flag("EquipTime", str(armor_actor.stem)))
        mod_sv.add(actor_svdata_flag("PorchTime", str(armor_actor.stem)))
    for weapon_actor in moddir.rglob("**/Weapon_*.sbactorpack"):
        mod_bg.add(actor_bool_bgdata_flag("IsNewPictureBook", str(weapon_actor.stem)))
        mod_bg.add(actor_bool_bgdata_flag("IsRegisteredPictureBook", str(weapon_actor.stem), 5))
        mod_bg.add(actor_bool_bgdata_flag("IsGet", str(weapon_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("PictureBookSize", str(weapon_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("EquipTime", str(weapon_actor.stem)))
        mod_bg.add(actor_s32_bgdata_flag("PorchTime", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsNewPictureBook", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsRegisteredPictureBook", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("IsGet", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("PictureBookSize", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("EquipTime", str(weapon_actor.stem)))
        mod_sv.add(actor_svdata_flag("PorchTime", str(weapon_actor.stem)))

    total_bg: set = set()
    total_bg |= util.search_bgdict_part("IsNewPictureBook_", "bool_data")
    total_bg |= util.search_bgdict_part("IsRegisteredPictureBook_", "bool_data")
    total_bg |= util.search_bgdict_part("IsGet_", "bool_data")
    total_bg |= util.search_bgdict_part("PictureBookSize_", "s32_data")
    total_bg |= util.search_bgdict_part("EquipTime_", "s32_data")
    total_bg |= util.search_bgdict_part("PorchTime_", "s32_data")
    total_sv: set = set()
    total_sv |= util.search_svdict_part("IsNewPictureBook_", "game_data.sav")
    total_sv |= util.search_svdict_part("IsRegisteredPictureBook_", "game_data.sav")
    total_sv |= util.search_svdict_part("IsGet_", "game_data.sav")
    total_sv |= util.search_svdict_part("PictureBookSize_", "game_data.sav")
    total_sv |= util.search_svdict_part("EquipTime_", "game_data.sav")
    total_sv |= util.search_svdict_part("PorchTime_", "game_data.sav")

    f = EXEC_DIR / "data" / "vanilla_hash.json"
    vanilla_hashes: set = set()
    vanilla_hash_dict = json.loads(f.read_text())
    for _, hash_list in vanilla_hash_dict.items():
        vanilla_hashes |= set(hash_list)
    bg_todelete = total_bg - (mod_bg | vanilla_hashes)
    sv_todelete = total_sv - (mod_sv | vanilla_hashes)

    for hash in bg_todelete:
        util.rem_flag_bgdict(hash, "bool_data")
    for hash in sv_todelete:
        util.rem_flag_svdict(hash, "game_data.sav")


def generate(args):
    directory: Path = Path(args.directory)
    if not args.actor and args.revival[0] == -1 and args.revival[1] == -1:
        print("No flag options were chosen! Use -a and/or -r to generate flags.")
        exit()

    if args.revival:
        generate_revival_flags(directory, args.revival)
    if args.actor:
        generate_item_flags(directory)
