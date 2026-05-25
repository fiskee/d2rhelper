from __future__ import annotations

import os
import subprocess
import sys
from ctypes import (
    CDLL,
    POINTER,
    byref,
    c_char_p,
    c_int,
    c_uint,
    c_void_p,
    create_string_buffer,
)
from pathlib import Path


def _find_library() -> str:
    module_dir = Path(__file__).resolve().parent
    if sys.platform == "win32":
        candidates = [
            module_dir / "Casclib.dll",
        ]
    else:
        candidates = [
            module_dir / "libcasc.so",
            module_dir / "libcasc.so.1",
        ]
    for p in candidates:
        if p.exists():
            return str(p)
    raise FileNotFoundError(
        "Cannot find CascLib shared library. "
        "Build it with scripts/build_casclib.sh or set the path via casc.load_library()."
    )


_lib = None


def load_library(path: str | None = None) -> CDLL:
    global _lib
    lib_path = path or _find_library()
    _lib = CDLL(str(lib_path))
    _setup_api()
    return _lib


def _get_lib() -> CDLL:
    global _lib
    if _lib is None:
        _lib = load_library()
    return _lib


def _setup_api() -> None:
    lib = _get_lib()

    lib.CascOpenStorage.argtypes = [c_char_p, c_uint, POINTER(c_void_p)]
    lib.CascOpenStorage.restype = c_int

    lib.CascCloseStorage.argtypes = [c_void_p]
    lib.CascCloseStorage.restype = c_int

    lib.CascOpenFile.argtypes = [c_void_p, c_char_p, c_uint, c_uint, POINTER(c_void_p)]
    lib.CascOpenFile.restype = c_int

    lib.CascReadFile.argtypes = [c_void_p, c_void_p, c_uint, POINTER(c_uint)]
    lib.CascReadFile.restype = c_int

    lib.CascGetFileSize.argtypes = [c_void_p, POINTER(c_uint)]
    lib.CascGetFileSize.restype = c_uint

    lib.CascCloseFile.argtypes = [c_void_p]
    lib.CascCloseFile.restype = c_int

    lib.GetCascError.argtypes = []
    lib.GetCascError.restype = c_uint


def get_error() -> int:
    return _get_lib().GetCascError()


class CascStorage:
    def __init__(self, d2r_install_dir: str | Path):
        self._d2r_path = Path(d2r_install_dir)
        self._handle: c_void_p | None = None
        self._open()

    def _open(self) -> None:
        storage_dir = self._d2r_path
        if (storage_dir / "Data").is_dir():
            storage_dir = storage_dir / "Data"

        handle = c_void_p()
        lib = _get_lib()
        if not lib.CascOpenStorage(str(storage_dir).encode(), 0, byref(handle)):
            err = get_error()
            raise OSError(f"CascOpenStorage failed: error code {err}")

        self._handle = handle

    def close(self) -> None:
        if self._handle is not None:
            _get_lib().CascCloseStorage(self._handle)
            self._handle = None

    def read_file(self, path: str) -> bytes:
        fh = c_void_p()
        lib = _get_lib()
        if not lib.CascOpenFile(self._handle, path.encode(), 0, 0, byref(fh)):
            raise FileNotFoundError(f"File not found in CASC: {path}")

        try:
            size_hi = c_uint()
            size_lo = lib.CascGetFileSize(fh, byref(size_hi))
            file_size = (size_hi.value << 32) | size_lo
            if file_size == 0xFFFFFFFF:  # INVALID_FILE_SIZE
                return b""

            buf = create_string_buffer(file_size)
            nread = c_uint()
            if not lib.CascReadFile(fh, buf, c_uint(file_size), byref(nread)):
                raise OSError(f"Failed to read file: {path}")
            return buf.raw[: nread.value]
        finally:
            lib.CascCloseFile(fh)

    def __enter__(self) -> CascStorage:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    @property
    def handle(self) -> c_void_p | None:
        return self._handle


CASCLIB_PATH = "data:data/global/excel"

KNOWN_TXT_FILES = [
    "armor.txt",
    "autoMagic.txt",
    "automap.txt",
    "belts.txt",
    "bodyLocs.txt",
    "books.txt",
    "charstats.txt",
    "colors.txt",
    "composit.txt",
    "cubemain.txt",
    "difficultylevels.txt",
    "elemtypes.txt",
    "events.txt",
    "gamble.txt",
    "gems.txt",
    "hiredesc.txt",
    "hireling.txt",
    "inventory.txt",
    "itemstatcost.txt",
    "itemtypes.txt",
    "levels.txt",
    "lowqualityitems.txt",
    "lvlprest.txt",
    "lvlsub.txt",
    "lvltxtypes.txt",
    "magicprefix.txt",
    "magicsuffix.txt",
    "misc.txt",
    "misscalc.txt",
    "missiles.txt",
    "monai.txt",
    "monchainstats.txt",
    "mondex.txt",
    "monitempercent.txt",
    "monlvl.txt",
    "monmode.txt",
    "monmodemusic.txt",
    "monequip.txt",
    "monplaces.txt",
    "monprop.txt",
    "monseq.txt",
    "monsounds.txt",
    "monstats.txt",
    "monstats2.txt",
    "monumod.txt",
    "nameappear.txt",
    "npc.txt",
    "npctalk.txt",
    "objects.txt",
    "overlay.txt",
    "pettype.txt",
    "plrtype.txt",
    "plrmode.txt",
    "playerclass.txt",
    "properties.txt",
    "qualityitems.txt",
    "rareprefix.txt",
    "raresuffix.txt",
    "runes.txt",
    "setitems.txt",
    "sets.txt",
    "shrines.txt",
    "skillcalc.txt",
    "skilldesc.txt",
    "skills.txt",
    "soundenviron.txt",
    "soundsettings.txt",
    "states.txt",
    "superuniques.txt",
    "treasureclassex.txt",
    "uniqueitems.txt",
    "weapons.txt",
]


def _steam_library_paths() -> list[Path]:
    paths: list[Path] = []
    steam_root = Path.home() / ".local/share/Steam"
    if not steam_root.is_dir():
        steam_root = Path.home() / ".steam/steam"
    if not steam_root.is_dir():
        if sys.platform == "win32":
            steam_root = Path("C:/Program Files (x86)/Steam")
    if steam_root.is_dir():
        paths.append(steam_root)

    library_file = steam_root / "steamapps" / "libraryfolders.vdf"
    if library_file.is_file():
        content = library_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith('"path"'):
                parts = stripped.split("\t")
                if len(parts) >= 2:
                    p = Path(parts[-1].strip('"'))
                    if p.is_dir() and p not in paths:
                        paths.append(p)

    return paths


_D2R_EXE_SUBPATHS = [
    "D2R.exe",
    "pfx/drive_c/Program Files (x86)/Diablo II Resurrected/D2R.exe",
    "pfx/drive_c/Program Files/Diablo II Resurrected/D2R.exe",
    "drive_c/Program Files (x86)/Diablo II Resurrected/D2R.exe",
    "drive_c/Program Files/Diablo II Resurrected/D2R.exe",
    "dosdevices/c:/Program Files (x86)/Diablo II Resurrected/D2R.exe",
    "dosdevices/c:/Program Files/Diablo II Resurrected/D2R.exe",
]


def _wine_prefix_search_roots() -> list[Path]:
    home = Path.home()
    roots: list[Path] = []

    for steam_lib in _steam_library_paths():
        compat = steam_lib / "steamapps" / "compatdata"
        if compat.is_dir():
            for entry in compat.iterdir():
                if entry.is_dir():
                    roots.append(entry)

    roots.extend([
        home / ".wine",
        home / "Games",
        home / "games",
        home / ".local/share/wineprefixes",
    ])

    return roots


def _windows_install_search_roots() -> list[Path]:
    if sys.platform != "win32":
        return []
    return [
        Path("C:/Program Files (x86)"),
        Path("C:/Program Files"),
        Path("C:/"),
        Path("D:/"),
    ]


def _windows_saved_games_paths() -> list[Path]:
    if sys.platform != "win32":
        return []

    candidates: list[Path] = []
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / "Saved Games" / "Diablo II Resurrected")

    home_drive = os.environ.get("HOMEDRIVE")
    home_path = os.environ.get("HOMEPATH")
    if home_drive and home_path:
        candidates.append(Path(f"{home_drive}{home_path}") / "Saved Games" / "Diablo II Resurrected")

    return candidates


def _saved_games_near_d2r(d2r_path: str | Path) -> list[Path]:
    parent = Path(d2r_path).parent
    candidates: list[Path] = []
    for _ in range(4):
        users_dir = parent / "users"
        if users_dir.is_dir():
            for user_dir in users_dir.iterdir():
                if user_dir.is_dir():
                    candidates.append(
                        user_dir / "Saved Games" / "Diablo II Resurrected"
                    )
        parent = parent.parent
    return candidates


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        if path not in seen:
            seen.add(path)
            result.append(path)
    return result


def find_d2r_path() -> str | None:
    env_path = os.environ.get("D2R_PATH")
    if env_path:
        p = Path(env_path)
        if p.is_dir():
            return str(p)
        for subpath in _D2R_EXE_SUBPATHS:
            test = p / subpath
            if test.exists():
                return str(test.parent)

    for root in _wine_prefix_search_roots() + _windows_install_search_roots():
        if not root.is_dir():
            continue
        for subpath in _D2R_EXE_SUBPATHS:
            test = root / subpath
            if test.exists():
                return str(test.parent)

        try:
            for found in root.rglob("D2R.exe"):
                if found.is_file():
                    return str(found.parent)
        except PermissionError:
            continue

    try:
        result = subprocess.run(
            ["find", str(Path.home()), "-maxdepth", "6", "-name", "D2R.exe", "-type", "f"],
            capture_output=True, text=True, timeout=15,
        )
        for line in result.stdout.strip().splitlines():
            p = Path(line.strip())
            if p.is_file():
                return str(p.parent)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return None


def find_d2_save_files(extension: str | None = None) -> list[Path]:
    files: list[Path] = []
    d2r_path = find_d2r_path()

    broad_windows_roots = [Path("C:/"), Path("D:/")]
    roots: list[Path] = []
    if d2r_path:
        roots.extend(_saved_games_near_d2r(d2r_path))
    roots.extend(_windows_saved_games_paths())
    roots.extend(_wine_prefix_search_roots())
    roots = _dedupe_paths(roots)

    if sys.platform == "win32":
        roots = [root for root in roots if root not in broad_windows_roots]

    glob_pattern = f"*.{extension}" if extension else "*.d2s"
    for root in roots:
        if not root.is_dir():
            continue
        try:
            for found in root.rglob(glob_pattern):
                if found.is_file():
                    files.append(found)
        except PermissionError:
            continue

    if files or sys.platform != "win32":
        return files

    for root in broad_windows_roots:
        if not root.is_dir():
            continue
        try:
            for found in root.rglob(glob_pattern):
                if found.is_file():
                    files.append(found)
        except PermissionError:
            continue

    return files


def find_latest_save_file(extension: str) -> Path | None:
    files = find_d2_save_files(extension)
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]
