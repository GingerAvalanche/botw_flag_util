import ctypes
import json
import time
import zlib
from math import ceil
from pathlib import Path

import oead
from bcml.mergers import mubin
from bcml import util as bcmlutil

from . import (
    EXEC_DIR,
    BGDATA_MAPPING,
    util,
    vanilla_hash_dict,
    vanilla_actors,
    vanilla_shrine_locs,
)
from .flag import BoolFlag, S32Flag
from .store import FlagStore


current_map: str = ""
bgdata: FlagStore = FlagStore()
mod_actors_with_life: set = set()


def should_not_make_flag(obj) -> bool:
    if "!Parameters" in obj:
        if "ForceFlag" in obj["!Parameters"]:
            return not obj["!Parameters"]["ForceFlag"]

    if "LinkTag" in obj["UnitConfigName"]:
        makeflag = obj["!Parameters"]["MakeSaveFlag"].v
        if makeflag == 0 and not "SaveFlag" in obj["!Parameters"]:
            return True
        else:
            return False

    if "TBox" in obj["UnitConfigName"]:
        if "EnableRevival" in obj["!Parameters"]:
            return not obj["!Parameters"]["EnableRevival"]
        else:
            return False

    if obj["UnitConfigName"] in mod_actors_with_life:
        return False

    if obj["UnitConfigName"] in vanilla_actors["with_flags"]:
        return False
    return True


def get_flag_name(obj, maptype: str) -> str:
    if "LinkTag" in obj["UnitConfigName"] and "!Parameters" in obj:
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
            if current_map:
                raise ValueError(
                    "A LinkTag was created with MakeSaveFlag 2 in CDungeon, this is not valid"
                )
            loc = oead.Vector3f()
            loc.x = obj["Translate"][0].v
            loc.y = obj["Translate"][1].v
            loc.z = obj["Translate"][2].v
            return f"Open_{util.get_nearest_shrine(loc)}"
    return f"{maptype}_{obj['UnitConfigName']}_{obj['HashId'].v}"


def bool_flag(new_obj, old_obj, maptype: str, resettype: int = 1, revival: bool = True) -> None:
    old_hash: int = ctypes.c_int32(zlib.crc32(get_flag_name(old_obj, maptype).encode())).value
    new_name: str = get_flag_name(new_obj, maptype)
    new_hash: int = ctypes.c_int32(zlib.crc32(new_name.encode())).value

    if should_not_make_flag(new_obj):
        bgdata.remove("bool_data", old_hash)
        bgdata.remove("bool_data", new_hash)
        return

    flag = bgdata.find("bool_data", old_hash)
    old_exists = flag.exists()
    flag = BoolFlag(revival=revival) if not old_exists else flag
    flag.set_data_name(new_name)
    flag.set_event_assoc(bool("LinksToObj" in new_obj))
    flag.set_is_save(True)
    flag.set_reset_type(resettype)

    mod_flag = bgdata.find("bool_data", flag.get_hash())
    if mod_flag.exists():
        old_exists = True
        old_hash = mod_flag.get_hash()

    if old_exists:
        bgdata.modify("bool_data", old_hash, flag)
    else:
        bgdata.add("bool_data", flag)


def s32_flag(new_obj, old_obj, maptype: str, resettype: int = 1, revival: bool = True) -> None:
    old_hash: int = ctypes.c_int32(zlib.crc32(get_flag_name(old_obj, maptype).encode())).value
    new_name: str = get_flag_name(new_obj, maptype)
    new_hash: int = ctypes.c_int32(zlib.crc32(new_name.encode())).value

    if should_not_make_flag(new_obj):
        bgdata.remove("s32_data", old_hash)
        bgdata.remove("s32_data", new_hash)
        return

    flag = bgdata.find("s32_data", old_hash)
    old_exists = flag.exists()
    flag = S32Flag(revival=revival) if not old_exists else flag
    flag.set_data_name(new_name)
    flag.set_event_assoc(bool("LinksToObj" in new_obj))
    flag.set_is_save(True)
    flag.set_reset_type(resettype)

    mod_flag = bgdata.find("s32_data", flag.get_hash())
    if mod_flag.exists():
        old_exists = True
        old_hash = mod_flag.get_hash()

    if old_exists:
        bgdata.modify("s32_data", old_hash, flag)
    else:
        bgdata.add("s32_data", flag)


def location_flag(name: str) -> None:
    flag = S32Flag()
    flag.set_data_name(name)
    flag.set_is_save(True)
    flag.set_init_value(0)
    flag.set_max_value(2147483647)
    flag.set_min_value(-2147483648)

    bgdata.add("s32_data", flag)


def misc_bool_flag(name: str) -> None:
    flag = BoolFlag()
    flag.set_data_name(name)
    flag.set_is_save(True)
    flag.set_is_one_trigger(True)

    bgdata.add("bool_data", flag)


def generate_revival_flags_for_map(
    map_data: oead.byml.Hash, stock_map: oead.byml.Hash, maptype: str, resettype: int
) -> dict:
    r: dict = {"ignore": set(), "delete": set()}

    map_hashes = [obj["HashId"].v for obj in map_data["Objs"]]
    stock_hashes = [obj["HashId"].v for obj in stock_map["Objs"]]
    for obj in map_data["Objs"]:
        r["ignore"].add(
            ctypes.c_int32(
                zlib.crc32(f"{maptype}_{obj['UnitConfigName']}_{obj['HashId'].v}".encode())
            ).value
        )
        revival = True
        bflag = True
        if "LinkTag" in obj["UnitConfigName"]:
            revival = False
            if not "!Parameters" in obj:
                continue  # if it's a LinkTag with no !Parameters, fuck that developer
            if "IncrementSave" in obj["!Parameters"]:
                if obj["!Parameters"]["IncrementSave"]:
                    bflag = False
        if obj["HashId"].v not in stock_hashes:
            if bflag:
                bool_flag(obj, obj, maptype, resettype, revival)
            else:
                s32_flag(obj, obj, maptype, resettype, revival)
        elif obj["HashId"].v in stock_hashes:
            stock_obj = stock_map["Objs"][stock_hashes.index(obj["HashId"].v)]
            name_changed = obj["UnitConfigName"] != stock_obj["UnitConfigName"]
            event_assoc_changed = bool("LinksToObj" in obj) != bool("LinksToObj" in stock_obj)
            if name_changed or event_assoc_changed:
                if bflag:
                    bool_flag(obj, stock_obj, maptype, resettype, revival)
                else:
                    s32_flag(obj, stock_obj, maptype, resettype, revival)
    for obj in stock_map["Objs"]:
        if obj["HashId"].v not in map_hashes:
            old_hash: int = ctypes.c_int32(
                zlib.crc32(f"{maptype}_{obj['UnitConfigName']}_{obj['HashId'].v}".encode())
            ).value
            r["delete"].add(old_hash)

    return r


def generate_revival_flags(resettypes: list) -> None:
    moddir: Path = util.root_dir()
    ignore_hashes: set = set()
    delete_hashes: set = set()

    if not resettypes[0] == -1:
        for map_unit in moddir.rglob("*_*.smubin"):
            map_start = time.time()
            map_data = oead.byml.from_binary(oead.yaz0.decompress(map_unit.read_bytes()))
            map_section = map_unit.stem.split("_")
            stock_map = mubin.get_stock_map((map_section[0], map_section[1]))
            temp = generate_revival_flags_for_map(map_data, stock_map, "MainField", resettypes[0])
            print(f"Finished processing {map_unit.name} in {time.time() - map_start} seconds...")
            ignore_hashes |= temp["ignore"]
            delete_hashes |= temp["delete"]
        for static_unit in moddir.rglob("MainField/Static.smubin"):
            map_start = time.time()
            static_data = oead.byml.from_binary(oead.yaz0.decompress(static_unit.read_bytes()))
            for marker in static_data["LocationMarker"]:
                if not "Icon" in marker:
                    continue
                if not marker["Icon"] == "Dungeon":
                    continue
                if "MessageID" in marker:
                    if not marker["MessageID"] in vanilla_shrine_locs:
                        location_flag(marker["SaveFlag"])
                        misc_bool_flag(f"Enter_{marker['MessageID']}")
                        misc_bool_flag(f"CompleteTreasure_{marker['MessageID']}")
            print(
                f"Finished processing MainField/Static.smubin in {time.time() - map_start} seconds..."
            )
    if not resettypes[1] == -1:
        for map_pack in moddir.rglob("Pack/Dungeon*.pack"):
            current_map = map_pack.stem
            pack_data = oead.Sarc(map_pack.read_bytes())
            try:
                stock_pack = oead.Sarc(bcmlutil.get_game_file(map_pack).read_bytes())
            except FileNotFoundError:
                stock_pack = None
            map_types = ("_Static", "_Dynamic")
            for map_type in map_types:
                map_start = time.time()
                map_name = f"{map_pack.stem}{map_type}.smubin"
                map_data = oead.byml.from_binary(
                    oead.yaz0.decompress(
                        pack_data.get_file(f"Map/CDungeon/{map_pack.stem}/{map_name}").data
                    )
                )
                if stock_pack:
                    stock_map = oead.byml.from_binary(
                        oead.yaz0.decompress(
                            stock_pack.get_file(f"Map/CDungeon/{map_pack.stem}/{map_name}").data
                        )
                    )
                else:
                    stock_map = oead.byml.Hash()
                    stock_map["Objs"] = oead.byml.Array()
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
            bgdata.remove("bool_data", hash)


def actor_bool_flag(flag_type: str, actor_name: str, cat: int = -1) -> int:
    flag_name: str = f"{flag_type}_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    flag = bgdata.find("bool_data", flag_hash)
    old_exists = flag.exists()
    flag = BoolFlag() if not old_exists else flag
    flag.set_data_name(flag_name)
    flag.set_is_save(True)
    if not cat == -1:
        flag.set_category(cat)
    if flag_type == "IsGet":
        flag.set_is_one_trigger(True)

    mod_flag = bgdata.find("bool_data", flag.get_hash())
    if mod_flag.exists():
        old_exists = True
        old_hash = mod_flag.get_hash()

    if old_exists:
        bgdata.modify("bool_data", flag_hash, flag)
    else:
        bgdata.add("bool_data", flag)

    return flag.get_hash()


def actor_s32_flag(flag_type: str, actor_name: str) -> int:
    flag_name: str = f"{flag_type}_{actor_name}"
    flag_hash: int = ctypes.c_int32(zlib.crc32(flag_name.encode())).value

    flag = bgdata.find("s32_data", flag_hash)
    old_exists = flag.exists()
    flag = S32Flag() if not old_exists else flag
    flag.set_data_name(flag_name)
    flag.set_is_save(True)
    flag.set_max_value(2147483647)
    flag.set_min_value(0)

    mod_flag = bgdata.find("bool_data", flag.get_hash())
    if mod_flag.exists():
        old_exists = True
        old_hash = mod_flag.get_hash()

    if old_exists:
        bgdata.modify("s32_data", flag_hash, flag)
    else:
        bgdata.add("s32_data", flag)

    return flag.get_hash()


def generate_item_flags() -> None:
    moddir: Path = util.root_dir()
    mod_bool: set = set()
    mod_s32: set = set()
    for item_actor in moddir.rglob("**/Item_*.sbactorpack"):
        mod_bool.add(actor_bool_flag("IsNewPictureBook", str(item_actor.stem)))
        mod_bool.add(actor_bool_flag("IsRegisteredPictureBook", str(item_actor.stem), 4))
        mod_bool.add(actor_bool_flag("IsGet", str(item_actor.stem)))
        mod_s32.add(actor_s32_flag("PictureBookSize", str(item_actor.stem)))
    for armor_actor in moddir.rglob("**/Armor_*.sbactorpack"):
        mod_bool.add(actor_bool_flag("IsGet", str(armor_actor.stem)))
        mod_s32.add(actor_s32_flag("EquipTime", str(armor_actor.stem)))
        mod_s32.add(actor_s32_flag("PorchTime", str(armor_actor.stem)))
    for weapon_actor in moddir.rglob("**/Weapon_*.sbactorpack"):
        mod_bool.add(actor_bool_flag("IsNewPictureBook", str(weapon_actor.stem)))
        mod_bool.add(actor_bool_flag("IsRegisteredPictureBook", str(weapon_actor.stem), 5))
        mod_bool.add(actor_bool_flag("IsGet", str(weapon_actor.stem)))
        mod_s32.add(actor_s32_flag("PictureBookSize", str(weapon_actor.stem)))
        mod_s32.add(actor_s32_flag("EquipTime", str(weapon_actor.stem)))
        mod_s32.add(actor_s32_flag("PorchTime", str(weapon_actor.stem)))

    vanilla_hashes: set = set()
    for _, hash_list in vanilla_hash_dict.items():
        vanilla_hashes |= set(hash_list)

    total_bool: set = set()
    total_bool |= bgdata.find_all_hashes("bool_data", "IsNewPictureBook_")
    total_bool |= bgdata.find_all_hashes("bool_data", "IsRegisteredPictureBook_")
    total_bool |= bgdata.find_all_hashes("bool_data", "IsGet_")
    to_delete = total_bool - (mod_bool | vanilla_hashes)
    for hash in to_delete:
        bgdata.remove("bool_data", hash)

    total_s32: set = set()
    total_s32 |= bgdata.find_all_hashes("s32_data", "PictureBookSize_")
    total_s32 |= bgdata.find_all_hashes("s32_data", "EquipTime_")
    total_s32 |= bgdata.find_all_hashes("s32_data", "PorchTime_")
    to_delete = total_s32 - (mod_s32 | vanilla_hashes)
    for hash in to_delete:
        bgdata.remove("s32_data", hash)


def generate(args):
    if not args.actor and args.revival[0] == -1 and args.revival[1] == -1:
        print("No flag options were chosen! Use -a and/or -r to generate flags.")
        exit()

    util.root_dir(args.directory)
    actorinfo_path = util.root_dir() / "content/Actor/ActorInfo.product.sbyml"
    if actorinfo_path.exists():
        actorinfo_bytes = actorinfo_path.read_bytes()
        actorinfo = oead.byml.from_binary(oead.yaz0.decompress(actorinfo_bytes))
        for actor in actorinfo["Actors"]:
            if (
                not actor["name"] in vanilla_actors["with_flags"]
                and not actor["name"] in vanilla_actors["no_flags"]
                and "generalLife" in actor
            ):
                mod_actors_with_life.add(actor["name"])
        del actorinfo_bytes
        del actorinfo

    gamedata_sarc = util.get_gamedata_sarc()
    for bgdata_name, bgdata_hash in map(util.unpack_oead_file, gamedata_sarc.get_files()):
        bgdata.add_flags_from_Hash(bgdata_name, bgdata_hash)

    if args.revival:
        generate_revival_flags(args.revival)
    if args.actor:
        generate_item_flags()

    files_to_write: list = []
    files_to_write.append("GameData/gamedata.ssarc")
    files_to_write.append("GameData/savedataformat.ssarc")
    orig_files = util.get_last_two_savedata_files()
    datas_to_write: list = []
    bgdata_start = time.time()
    datas_to_write.append(oead.yaz0.compress(util.make_new_gamedata(bgdata, args.bigendian)))
    bgdata_time = time.time() - bgdata_start
    print(f"Generating bgdata took {bgdata_time} seconds...")
    bgdata_start = time.time()
    datas_to_write.append(
        oead.yaz0.compress(util.make_new_savedata(bgdata, args.bigendian, orig_files))
    )
    bgdata_time = time.time() - bgdata_start
    print(f"Generating svdata took {bgdata_time} seconds...")
    util.inject_files_into_bootup(files_to_write, datas_to_write)

    if bgdata.get_total_changes() > 0:
        print()
        print(f"{bgdata.get_num_new()} New Game Data Entries")
        print(f"{bgdata.get_num_modified()} Modified Game Data Entries")
        print(f"{bgdata.get_num_deleted()} Deleted Game Data Entries")
        print(f"{bgdata.get_num_new_svdata()} New Save Data Entries")
        print(f"{bgdata.get_num_modified_svdata()} Modified Save Data Entries")
        print(f"{bgdata.get_num_deleted_svdata()} Deleted Save Data Entries")

        if args.verbose:
            (util.root_dir() / "flag_log.txt").touch()
            (util.root_dir() / "flag_log.txt").write_text(util.get_verbose_output(bgdata))
    else:
        print("No changes were made.")
