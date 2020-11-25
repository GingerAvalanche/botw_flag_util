from oead.byml import Array, Hash
from typing import Dict, List, Set

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
IGNORED_SAVE_FLAGS = [
    "AlbumPictureIndex",
    "IsGet_Obj_AmiiboItem",
    "CaptionPictSize",
    "SeakSensorPictureIndex",
    "AoC_HardMode_Enabled",
    "FamouseValue",
    "SaveDistrictName",
    "LastSaveTime_Lower",
    "GameClear",
    "IsChangedByDebug",
    "SaveLocationName",
    "IsSaveByAuto",
    "LastSaveTime_Upper",
    "IsLogicalDelete",
    "GyroOnOff",
    "PlayReport_CtrlMode_Ext",
    "PlayReport_CtrlMode_Free",
    "NexUniqueID_Upper",
    "MiniMapDirection",
    "CameraRLReverse",
    "JumpButtonChange",
    "TextRubyOnOff",
    "VoiceLanguage",
    "PlayReport_CtrlMode_Console_Free",
    "PlayReport_PlayTime_Handheld",
    "BalloonTextOnOff",
    "PlayReport_AudioChannel_Other",
    "PlayReport_AudioChannel_5_1ch",
    "NexIsPosTrackUploadAvailableCache",
    "NexsSaveDataUploadIntervalHoursCache",
    "NexUniqueID_Lower",
    "TrackBlockFileNumber",
    "Option_LatestAoCVerPlayed",
    "NexPosTrackUploadIntervalHoursCache",
    "NexLastUploadTrackBlockHardIndex",
    "MainScreenOnOff",
    "PlayReport_AudioChannel_Stereo",
    "NexIsSaveDataUploadAvailableCache",
    "NexLastUploadSaveDataTime",
    "PlayReport_AllPlayTime",
    "NexLastUploadTrackBlockIndex",
    "PlayReport_CtrlMode_Console_Ext",
    "AmiiboItemOnOff",
    "TrackBlockFileNumber_Hard",
    "StickSensitivity",
    "TextWindowChange",
    "IsLastPlayHardMode",
    "PlayReport_CtrlMode_Console_FullKey",
    "NexLastUploadTrackBlockTime",
    "PlayReport_CtrlMode_FullKey",
    "PlayReport_PlayTime_Console",
    "PlayReport_AudioChannel_Mono",
    "CameraUpDownReverse",
    "PlayReport_CtrlMode_Handheld",
]


class FlagStore:
    _store: Dict[str, Dict[int, BFUFlag]]
    _orig_store: Dict[str, Dict[int, BFUFlag]]

    def __init__(self) -> None:
        self._store = {}
        self._orig_store = {}
        for ftype in FLAG_MAPPING:
            self._store[ftype] = {}
            self._orig_store[ftype] = {}

    def add_flags_from_Hash(self, name: str, data: Hash) -> None:
        is_revival = bool("revival" in name)
        for ftype, flags in data.items():
            for flag in flags:
                self._store[ftype][flag["HashValue"].v] = FLAG_MAPPING[ftype](
                    flag, revival=is_revival
                )
                self._orig_store[ftype][flag["HashValue"].v] = FLAG_MAPPING[ftype](
                    flag, revival=is_revival
                )

    def add_flags_from_Hash_no_overwrite(self, name: str, data: Hash) -> None:
        is_revival = bool("revival" in name)
        for ftype, flags in data.items():
            for flag in flags:
                if not self.find(ftype, flag["HashValue"].v).exists():
                    self._store[ftype][flag["HashValue"].v] = FLAG_MAPPING[ftype](
                        flag, revival=is_revival
                    )
                    self._orig_store[ftype][flag["HashValue"].v] = FLAG_MAPPING[ftype](
                        flag, revival=is_revival
                    )

    def find(self, ftype: str, hash: int) -> BFUFlag:
        if hash in self._store[ftype]:
            return self._store[ftype][hash]
        return BFUFlag()

    def find_all(self, ftype: str, search: str) -> List[BFUFlag]:
        r: List[BFUFlag] = []
        for _, flag in self._store[ftype].items():
            if flag.name_contains(search):
                r.append(flag)
        return r

    def find_all_hashes(self, ftype: str, search: str) -> Set[int]:
        r: Set[int] = set()
        for hash, flag in self._store[ftype].items():
            if flag.name_contains(search):
                r.add(hash)
        return r

    def add(self, ftype: str, flag: BFUFlag) -> None:
        self._store[ftype][flag.hash_value] = flag

    def remove(self, ftype: str, hash: int) -> None:
        self._store[ftype].pop(hash, None)

    def get_num_new(self) -> int:
        r = 0
        for ftype in FLAG_MAPPING:
            r += len(self.get_new_ftype(ftype))
        return r

    def get_num_modified(self) -> int:
        r = 0
        for ftype in FLAG_MAPPING:
            r += len(self.get_modified_ftype(ftype))
        return r

    def get_num_deleted(self) -> int:
        r = 0
        for ftype in FLAG_MAPPING:
            r += len(self.get_deleted_ftype(ftype))
        return r

    def get_new_ftype(self, ftype: str) -> Set[str]:
        r: Set[str] = set()
        for _, flag in self._store[ftype].items():
            if flag.hash_value not in self._orig_store[ftype]:
                r.add(flag.data_name)
        return r

    def get_modified_ftype(self, ftype: str) -> Set[str]:
        r: Set[str] = set()
        for _, flag in self._store[ftype].items():
            if flag.hash_value in self._orig_store[ftype]:
                if not flag == self._orig_store[ftype][flag.hash_value]:
                    r.add(flag.data_name)
        return r

    def get_deleted_ftype(self, ftype: str) -> Set[str]:
        r: Set[str] = set()
        for _, flag in self._orig_store[ftype].items():
            if flag.hash_value not in self._store[ftype]:
                r.add(flag.data_name)
        return r

    def get_total_changes(self) -> int:
        return self.get_num_new() + self.get_num_modified() + self.get_num_deleted()

    def get_num_new_svdata(self) -> int:
        r = 0
        for ftype in FLAG_MAPPING:
            r += len(self.get_new_ftype_svdata(ftype))
        return r

    def get_num_modified_svdata(self) -> int:
        """Always returns 0 because modifying anything about
        a save flag will make it a new+delete instead"""
        return 0

    def get_num_deleted_svdata(self) -> int:
        r = 0
        for ftype in FLAG_MAPPING:
            r += len(self.get_deleted_ftype_svdata(ftype))
        return r

    def get_new_ftype_svdata(self, ftype: str) -> Set[str]:
        r: Set[str] = set()
        for _, flag in self._store[ftype].items():
            if flag.is_save:
                if flag.hash_value not in self._orig_store[ftype]:
                    r.add(flag.data_name)
        return r

    def get_modified_ftype_svdata(self, ftype: str) -> Set[str]:
        """Always returns empty because modifying anything about
        a save flag will make it a new+delete instead"""
        return set()

    def get_deleted_ftype_svdata(self, ftype: str) -> Set[str]:
        r: Set[str] = set()
        for _, flag in self._orig_store[ftype].items():
            if flag.is_save:
                if flag.hash_value not in self._store[ftype]:
                    r.add(flag.data_name)
        return r

    def flags_to_bgdata_Array(self, prefix: str) -> Array:
        ftype = BGDATA_MAPPING[prefix]
        if prefix == "revival_bool_data" or prefix == "revival_s32_data":
            flag_list = [
                flag.to_Hash() for _, flag in self._store[ftype].items() if flag.is_revival
            ]
        elif prefix == "bool_data" or prefix == "s32_data":
            flag_list = [
                flag.to_Hash() for _, flag in self._store[ftype].items() if not flag.is_revival
            ]
        else:
            flag_list = [flag.to_Hash() for _, flag in self._store[ftype].items()]

        return Array(sorted(flag_list, key=lambda f: f["HashValue"]))

    def flags_to_svdata_Array(self) -> Array:
        flag_list: list = []
        for _, flagdict in self._store.items():
            flag_list += [
                flag.to_sv_Hash()
                for _, flag in flagdict.items()
                if flag.is_save and not flag.data_name in IGNORED_SAVE_FLAGS
            ]
        return Array(sorted(flag_list, key=lambda f: f["HashValue"]))
