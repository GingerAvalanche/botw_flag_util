from math import ceil, sqrt
from pathlib import Path
from typing import Union
from time import time

import oead
from bcml import util as bcmlutil
from . import BGDATA_MAPPING, vanilla_shrine_locs
from .store import FlagStore


BGDATA_TYPES = [
    "bool_array_data",
    "bool_data",
    "f32_array_data",
    "f32_data",
    "s32_array_data",
    "s32_data",
    "string256_array_data",
    "string256_data",
    "string_data",
    "string64_array_data",
    "string64_data",
    "vector2f_array_data",
    "vector2f_data",
    "vector3f_array_data",
    "vector3f_data",
    "vector4f_data",
]


def root_dir(dir: str = "") -> Path:
    if not dir == "":
        root_dir._root_dir = dir  # type:ignore[attr-defined]
    if not hasattr(root_dir, "_root_dir"):
        raise RuntimeError("Root directory was never set.")
    return Path(root_dir._root_dir)  # type:ignore[attr-defined]


def convert_to_vec3f(hash: Union[dict, oead.byml.Hash]) -> oead.Vector3f:
    vec = oead.Vector3f()
    if type(hash) == dict:
        vec.x = hash["X"]
        vec.y = hash["Y"]
        vec.z = hash["Z"]
    elif type(hash) == oead.byml.Hash:
        vec.x = hash["X"].v
        vec.y = hash["Y"].v
        vec.z = hash["Z"].v
    return vec


def get_vector_distance(vec1: oead.Vector3f, vec2: oead.Vector3f) -> float:
    return sqrt((vec1.x - vec2.x) ** 2 + (vec1.y - vec2.y) ** 2 + (vec1.z - vec2.z) ** 2)


def get_shrine_locs() -> dict:
    if not hasattr(get_shrine_locs, "_shrine_locs"):
        shrine_locs = {
            shrine: convert_to_vec3f(loc) for shrine, loc in vanilla_shrine_locs.items()
        }
        static_path = root_dir() / "aoc/0010/Map/MainField/Static.smubin"
        if static_path.exists():
            static = oead.byml.from_binary(oead.yaz0.decompress(static_path.read_bytes()))
            for marker in static["LocationMarker"]:
                if not "Icon" in marker:
                    continue
                if not marker["Icon"] == "Dungeon":
                    continue
                if "MessageID" in marker:
                    if not marker["MessageID"] in vanilla_shrine_locs:
                        shrine_locs[marker["MessageID"]] = convert_to_vec3f(marker["Location"])
        get_shrine_locs._shrine_locs = shrine_locs  # type:ignore[attr-defined]
    return get_shrine_locs._shrine_locs  # type:ignore[attr-defined]


def get_nearest_shrine(vec: oead.Vector3f) -> str:
    shrine_locs = get_shrine_locs()
    smallest_distance: float = 10000000.0
    nearest_shrine: str = ""
    for name, loc in shrine_locs.items():
        shrine_distance = get_vector_distance(vec, loc)
        if shrine_distance < smallest_distance:
            nearest_shrine = name
            smallest_distance = shrine_distance
    return nearest_shrine


def get_gamedata_sarc() -> oead.Sarc:
    bootup_path: Path = root_dir() / "content" / "Pack" / "Bootup.pack"
    bootup_sarc = oead.Sarc(bootup_path.read_bytes())
    gamedata_sarc = oead.Sarc(
        oead.yaz0.decompress(bootup_sarc.get_file("GameData/gamedata.ssarc").data)
    )
    return gamedata_sarc


def get_last_two_savedata_files() -> list:
    bootup_path: Path = root_dir() / "content" / "Pack" / "Bootup.pack"
    bootup_sarc = oead.Sarc(bootup_path.read_bytes())
    savedata_sarc = oead.Sarc(
        oead.yaz0.decompress(bootup_sarc.get_file("GameData/savedataformat.ssarc").data)
    )
    savedata_writer = oead.SarcWriter.from_sarc(savedata_sarc)
    idx = 0
    files = []
    while True:
        try:
            savedata_writer.files[f"/saveformat_{idx+2}.bgsvdata"]
            idx += 1
        except KeyError:
            files.append(savedata_writer.files[f"/saveformat_{idx}.bgsvdata"])
            files.append(savedata_writer.files[f"/saveformat_{idx+1}.bgsvdata"])
            return files


def make_new_gamedata(store: FlagStore, big_endian: bool) -> None:
    bgwriter = oead.SarcWriter(
        endian=oead.Endianness.Big if big_endian else oead.Endianness.Little
    )
    for prefix, data_type in BGDATA_MAPPING.items():
        bgdata_array = store.flags_to_bgdata_Array(prefix)
        num_files = ceil(len(bgdata_array) / 4096)
        for idx in range(num_files):
            start = idx * 4096
            end = (idx + 1) * 4096
            if end > len(bgdata_array):
                end = len(bgdata_array)
            bgwriter.files[f"/{prefix}_{idx}.bgdata"] = oead.byml.to_binary(
                oead.byml.Hash({data_type: bgdata_array[start:end]}), big_endian,
            )
    return bgwriter.write()[1]


def make_new_savedata(store: FlagStore, big_endian: bool, orig_files: list) -> bytes:
    svwriter = oead.SarcWriter(
        endian=oead.Endianness.Big if big_endian else oead.Endianness.Little
    )
    svdata_array = store.flags_to_svdata_Array()
    num_files = ceil(len(svdata_array) / 8192)
    for idx in range(num_files):
        start = idx * 8192
        end = (idx + 1) * 8192
        if end > len(svdata_array):
            end = len(svdata_array)
        svwriter.files[f"/saveformat_{idx}.bgsvdata"] = oead.byml.to_binary(
            oead.byml.Hash(
                {
                    "file_list": oead.byml.Array(
                        [
                            {
                                "IsCommon": False,
                                "IsCommonAtSameAccount": False,
                                "IsSaveSecureCode": True,
                                "file_name": "game_data.sav",
                            },
                            oead.byml.Array(svdata_array[start:end]),
                        ]
                    ),
                    "save_info": oead.byml.Array(
                        [
                            {
                                "directory_num": oead.S32(num_files + 2),
                                "is_build_machine": True,
                                "revision": oead.S32(18203),
                            }
                        ]
                    ),
                }
            ),
            big_endian,
        )
    svwriter.files[f"/saveformat_{num_files}.bgsvdata"] = orig_files[0]
    svwriter.files[f"/saveformat_{num_files+1}.bgsvdata"] = orig_files[1]
    return svwriter.write()[1]


def inject_files_into_bootup(files: list, datas: list):
    bootup_path: Path = root_dir() / "content" / "Pack" / "Bootup.pack"
    sarc_data = bootup_path.read_bytes()
    yaz = sarc_data[0:4] == b"Yaz0"
    if yaz:
        sarc_data = bcmlutil.decompress(sarc_data)
    old_sarc = oead.Sarc(sarc_data)
    del sarc_data
    new_sarc = oead.SarcWriter.from_sarc(old_sarc)
    del old_sarc
    for idx in range(len(files)):
        new_sarc.files[files[idx]] = (
            datas[idx] if isinstance(datas[idx], bytes) else bytes(datas[idx])
        )
    new_bytes = new_sarc.write()[1]
    del new_sarc
    bootup_path.write_bytes(new_bytes if not yaz else bcmlutil.compress(new_bytes))
    del new_bytes


def unpack_oead_file(f: oead.File) -> tuple:
    return (f.name, oead.byml.from_binary(f.data))


def get_verbose_output(store: FlagStore) -> str:
    r: list = ["\n"]
    for ftype in BGDATA_TYPES:
        r.append(f"For {ftype}:\n")
        r.append("  Game data entries:\n")
        r.append("    New flags:\n")
        r.append(f"      {len(store.get_new_ftype(ftype))} flags were added to {ftype}\n")
        r.append("    Modified flags:\n")
        r.append(f"      {len(store.get_modified_ftype(ftype))} flags were modified in {ftype}\n")
        r.append("    Deleted flags:\n")
        r.append(f"      {len(store.get_deleted_ftype(ftype))} flags were deleted from {ftype}\n")
        r.append("  Save data entries:\n")
        r.append("    New flags:\n")
        r.append(f"      {len(store.get_new_ftype_svdata(ftype))} flags were added to {ftype}\n")
        r.append("    Modified flags:\n")
        r.append(
            f"      {len(store.get_modified_ftype_svdata(ftype))} flags were modified in {ftype}\n"
        )
        r.append("    Deleted flags:\n")
        r.append(
            f"      {len(store.get_deleted_ftype_svdata(ftype))} flags were deleted from {ftype}\n"
        )
    return "".join(r)
