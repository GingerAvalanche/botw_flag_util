from oead.byml import Array, Hash
from typing import Dict, List

from . import BGDATA_MAPPING
from .flag import (
    BFUFlag,
    BoolFlag,
    BoolArrayFlag,
    S32Flag,
    S32ArrayFlag,
    F32Flag,
    F32ArrayFlag,
    String32Flag,
    String64Flag,
    String64ArrayFlag,
    String256Flag,
    String256ArrayFlag,
    Vec2Flag,
    Vec2ArrayFlag,
    Vec3Flag,
    Vec3ArrayFlag,
    Vec4Flag,
)


FLAG_MAPPING = {
    "bool_data": BoolFlag,
    "bool_array_data": BoolArrayFlag,
    "s32_data": S32Flag,
    "s32_array_data": S32ArrayFlag,
    "f32_data": F32Flag,
    "f32_array_data": F32ArrayFlag,
    "string_data": String32Flag,
    "string64_data": String64Flag,
    "string64_array_data": String64ArrayFlag,
    "string256_data": String256Flag,
    "string256_array_data": String256ArrayFlag,
    "vector2f_data": Vec2Flag,
    "vector2f_array_data": Vec2ArrayFlag,
    "vector3f_data": Vec3Flag,
    "vector3f_array_data": Vec3ArrayFlag,
    "vector4f_data": Vec4Flag,
}


class FlagStore:
    _store: Dict[str, dict]
    _new_bgdata: Dict[str, set]
    _modified_bgdata: Dict[str, set]
    _deleted_bgdata: Dict[str, set]
    _new_svdata: Dict[str, set]
    _modified_svdata: Dict[str, set]
    _deleted_svdata: Dict[str, set]

    def __init__(self) -> None:
        self._store = {}
        self._new_bgdata = {}
        self._modified_bgdata = {}
        self._deleted_bgdata = {}
        self._new_svdata = {}
        self._modified_svdata = {}
        self._deleted_svdata = {}
        for _, ftype in BGDATA_MAPPING.items():
            self._store[ftype] = {}
            self._new_bgdata[ftype] = set()
            self._modified_bgdata[ftype] = set()
            self._deleted_bgdata[ftype] = set()
            self._new_svdata[ftype] = set()
            self._modified_svdata[ftype] = set()
            self._deleted_svdata[ftype] = set()

    def add_flags_from_Hash(self, name: str, data: Hash) -> None:
        is_revival = bool("revival" in name)
        for ftype, flags in data.items():
            for flag in flags:
                self._store[ftype][flag["HashValue"].v] = FLAG_MAPPING[ftype](
                    flag, revival=is_revival
                )

    def find(self, ftype: str, hash: int) -> BFUFlag:
        if hash in self._store[ftype]:
            return self._store[ftype][hash]
        return BoolFlag()

    def find_all(self, ftype: str, search: str) -> List[BFUFlag]:
        r: list = []
        for _, flag in self._store[ftype].items():
            if flag.name_contains(search):
                r.append(flag)
        return r

    def find_all_hashes(self, ftype: str, search: str) -> set:
        r: set = set()
        for hash, flag in self._store[ftype].items():
            if flag.name_contains(search):
                r.add(hash)
        return r

    def add(self, ftype: str, flag: BFUFlag) -> bool:
        self._store[ftype][flag.get_hash()] = flag
        self._new_bgdata[ftype].add(flag.get_hash())
        if flag.is_save():
            self._new_svdata[ftype].add(flag.get_hash())
        return True

    def modify(self, ftype: str, old_hash: int, new_flag: BFUFlag) -> bool:
        flag = self.find(ftype, old_hash)
        new_hash = new_flag.get_hash()
        if new_hash == old_hash:
            return False
        self._store[ftype].pop(old_hash)
        self._store[ftype][new_hash] = new_flag
        self._modified_bgdata[ftype].add(new_hash)
        if new_flag.is_save():
            self._modified_svdata[ftype].add(new_hash)
        return True

    def remove(self, ftype: str, hash: int) -> bool:
        flag = self.find(ftype, hash)
        if flag.exists():
            self._store[ftype].pop(hash)
            self._deleted_bgdata[ftype].add(hash)
            if flag.is_save():
                self._deleted_svdata[ftype].add(hash)
            return True
        return False

    def get_total_num_changes(self) -> int:
        changes: int = 0
        for ftype in FLAG_MAPPING:
            changes += len(self._new_bgdata[ftype])
            changes += len(self._modified_bgdata[ftype])
            changes += len(self._deleted_bgdata[ftype])
        return changes

    def get_new_ftype(self, ftype: str) -> set:
        return self._new_bgdata[ftype]

    def get_modified_ftype(self, ftype: str) -> set:
        return self._modified_bgdata[ftype]

    def get_deleted_ftype(self, ftype: str) -> set:
        return self._deleted_bgdata[ftype]

    def get_new_ftype_svdata(self, ftype: str) -> set:
        return self._new_svdata[ftype]

    def get_modified_ftype_svdata(self, ftype: str) -> set:
        return self._modified_svdata[ftype]

    def get_deleted_ftype_svdata(self, ftype: str) -> set:
        return self._deleted_svdata[ftype]

    def flags_to_bgdata_Array(self, prefix: str) -> Array:
        ftype = BGDATA_MAPPING[prefix]
        if prefix == "revival_bool_data" or prefix == "revival_s32_data":
            flag_list = [
                flag.to_Hash() for _, flag in self._store[ftype].items() if flag.is_revival()
            ]
        elif prefix == "bool_data" or prefix == "s32_data":
            flag_list = [
                flag.to_Hash() for _, flag in self._store[ftype].items() if not flag.is_revival()
            ]
        else:
            flag_list = [flag.to_Hash() for _, flag in self._store[ftype].items()]

        return Array(sorted(flag_list, key=lambda f: f["HashValue"]))

    def flags_to_svdata_Array(self) -> Array:
        flag_list: list = []
        for _, flagdict in self._store.items():
            flag_list += [flag.to_sv_Hash() for _, flag in flagdict.items() if flag.is_save()]
        return Array(sorted(flag_list, key=lambda f: f["HashValue"]))
