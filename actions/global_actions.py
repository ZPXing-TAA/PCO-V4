import importlib
import os
import time
from typing import Dict, Iterable, Mapping, MutableMapping, Tuple

OffsetMap = Mapping[str, Tuple[int, int]]
PointMap = Dict[str, Tuple[int, int]]

BASE_MAPPING_MODULE = "mapping.huaweipura"

# Baseline coordinates (Huawei Pura)
BASE_POINTS: PointMap = {
    "MOVE_START": (523, 800),
    "MOVE_END": (523, 700),
    "ATTACK": (2280, 980),
    "JUMP": (2510, 830),
    "SPRINT": (2500, 1125),
    "UTIL": (2060, 1120),
    "TURN_180_L": (550, 300),
    "TURN_180_R": (1766, 300),
    "TURN_90_R_L": (550, 300),
    "TURN_90_R_R": (1158, 300),
    "TURN_90_L_L": (1158, 300),
    "TURN_90_L_R": (500, 300),
    "TURN_45_R_L": (550, 300),
    "TURN_45_R_R": (854, 300),
    "TURN_45_L_L": (854, 300),
    "TURN_45_L_R": (550, 300),
    "TURN_30_R_L": (550, 300),
    "TURN_30_R_R": (753, 300),
    "TURN_30_L_L": (753, 300),
    "TURN_30_L_R": (550, 300),
    "TURN_135_R_L": (550, 300),
    "TURN_135_R_R": (1462, 300),
    "TURN_135_L_L": (1462, 300),
    "TURN_135_L_R": (550, 300),
    "OPEN_MAP": (400, 200),
    "CONFIRM_TELEPORT": (2450, 1180),
    "ADJUST_GAME_TIME_P1": (175, 60),
    "ADJUST_GAME_TIME_P2": (165, 870),
    "ADJUST_GAME_TIME_S1": (2025, 535),
    "ADJUST_GAME_TIME_S2": (2025, 635),
    "ADJUST_GAME_TIME_S3": (1885, 635),
    "ADJUST_GAME_TIME_S4": (1885, 565),
    "ADJUST_GAME_TIME_S5": (1985, 565),
    "ADJUST_GAME_TIME_P3": (2000, 1175),
    "ADJUST_GAME_TIME_P4": (165, 90),
}

POINT_GROUPS: Dict[str, Tuple[str, ...]] = {
    "MOVE_START": ("MOVE",),
    "MOVE_END": ("MOVE",),
    "ATTACK": ("ATTACK",),
    "JUMP": ("JUMP",),
    "SPRINT": ("SPRINT",),
    "UTIL": ("UTIL",),
    "TURN_180_L": ("TURN", "TURN_180"),
    "TURN_180_R": ("TURN", "TURN_180"),
    "TURN_90_R_L": ("TURN", "TURN_90_R"),
    "TURN_90_R_R": ("TURN", "TURN_90_R"),
    "TURN_90_L_L": ("TURN", "TURN_90_L"),
    "TURN_90_L_R": ("TURN", "TURN_90_L"),
    "TURN_45_R_L": ("TURN", "TURN_45_R"),
    "TURN_45_R_R": ("TURN", "TURN_45_R"),
    "TURN_45_L_L": ("TURN", "TURN_45_L"),
    "TURN_45_L_R": ("TURN", "TURN_45_L"),
    "TURN_30_R_L": ("TURN", "TURN_30_R"),
    "TURN_30_R_R": ("TURN", "TURN_30_R"),
    "TURN_30_L_L": ("TURN", "TURN_30_L"),
    "TURN_30_L_R": ("TURN", "TURN_30_L"),
    "TURN_135_R_L": ("TURN", "TURN_135_R"),
    "TURN_135_R_R": ("TURN", "TURN_135_R"),
    "TURN_135_L_L": ("TURN", "TURN_135_L"),
    "TURN_135_L_R": ("TURN", "TURN_135_L"),
    "OPEN_MAP": ("OPEN_MAP",),
    "CONFIRM_TELEPORT": ("CONFIRM_TELEPORT",),
    "ADJUST_GAME_TIME_P1": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_P2": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_S1": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_S2": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_S3": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_S4": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_S5": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_P3": ("ADJUST_GAME_TIME",),
    "ADJUST_GAME_TIME_P4": ("ADJUST_GAME_TIME",),
}


def _load_resolution(mapping_module: str) -> Tuple[int, int]:
    mod = importlib.import_module(mapping_module)
    width = int(getattr(mod, "WIDTH"))
    height = int(getattr(mod, "HEIGHT"))
    if width <= 0 or height <= 0:
        raise ValueError(f"Invalid resolution in {mapping_module}: {width}x{height}")
    return width, height


def _add(p: Tuple[int, int], off: Tuple[int, int]) -> Tuple[int, int]:
    return p[0] + off[0], p[1] + off[1]


def _env_offset(key: str) -> Tuple[int, int]:
    return int(os.environ.get(f"{key}_X_OFFSET", "0")), int(os.environ.get(f"{key}_Y_OFFSET", "0"))


def _scale_point(base_xy: Tuple[int, int], base_wh: Tuple[int, int], target_wh: Tuple[int, int]) -> Tuple[int, int]:
    bx, by = base_xy
    bw, bh = base_wh
    tw, th = target_wh
    return round(bx * tw / bw), round(by * th / bh)


def _resolve_point(name: str, mapped_xy: Tuple[int, int], offsets: OffsetMap, use_env_offsets: bool) -> Tuple[int, int]:
    xy = mapped_xy
    keys: Iterable[str] = ("GLOBAL",) + POINT_GROUPS.get(name, ()) + (name,)
    for key in keys:
        if key in offsets:
            xy = _add(xy, offsets[key])
        if use_env_offsets:
            xy = _add(xy, _env_offset(key))
    return int(xy[0]), int(xy[1])


def build_actions(
    mapping_module: str = BASE_MAPPING_MODULE,
    offsets: OffsetMap | None = None,
    use_env_offsets: bool = False,
) -> Dict[str, object]:
    device_offsets = offsets or {}
    base_wh = _load_resolution(BASE_MAPPING_MODULE)
    target_wh = _load_resolution(mapping_module)

    mapped_points: PointMap = {
        name: _scale_point(base_xy, base_wh, target_wh)
        for name, base_xy in BASE_POINTS.items()
    }
    points: PointMap = {
        name: _resolve_point(name, mapped_xy, device_offsets, use_env_offsets)
        for name, mapped_xy in mapped_points.items()
    }

    def tap(x: int, y: int):
        os.system(f"adb shell input tap {x} {y}")

    def swipe(x1: int, y1: int, x2: int, y2: int, d: int):
        os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} {d}")

    def move(seconds):
        swipe(*points["MOVE_START"], *points["MOVE_END"], int(seconds * 1000))

    def climb(seconds):
        move(seconds)

    def swim(seconds):
        move(seconds)

    def attack():
        tap(*points["ATTACK"])

    def heavy_attack():
        x, y = points["ATTACK"]
        swipe(x, y, x, y, 1000)

    def long_attack(seconds):
        x, y = points["ATTACK"]
        swipe(x, y, x, y, int(seconds * 1000))

    def jump():
        tap(*points["JUMP"])

    def dash():
        tap(*points["SPRINT"])

    def run(seconds):
        tap(*points["SPRINT"])
        sleep(0.1)
        move(seconds)

    def util():
        tap(*points["UTIL"])

    def long_util():
        x, y = points["UTIL"]
        swipe(x, y, x, y, 1000)

    def glide(seconds):
        long_util()
        time.sleep(1)
        tap(*points["JUMP"])
        move(seconds)

    def sleep(seconds):
        time.sleep(seconds)

    def turn_180():
        swipe(*points["TURN_180_L"], *points["TURN_180_R"], 800)

    def turn_right_90():
        swipe(*points["TURN_90_R_L"], *points["TURN_90_R_R"], 600)

    def turn_left_90():
        swipe(*points["TURN_90_L_L"], *points["TURN_90_L_R"], 600)

    def turn_right_45():
        swipe(*points["TURN_45_R_L"], *points["TURN_45_R_R"], 600)

    def turn_left_45():
        swipe(*points["TURN_45_L_L"], *points["TURN_45_L_R"], 600)

    def turn_right_30():
        swipe(*points["TURN_30_R_L"], *points["TURN_30_R_R"], 600)

    def turn_left_30():
        swipe(*points["TURN_30_L_L"], *points["TURN_30_L_R"], 600)

    def turn_right_135():
        swipe(*points["TURN_135_R_L"], *points["TURN_135_R_R"], 700)

    def turn_left_135():
        swipe(*points["TURN_135_L_L"], *points["TURN_135_L_R"], 700)

    def open_map():
        tap(*points["OPEN_MAP"])

    def confirm_teleport():
        tap(*points["CONFIRM_TELEPORT"])
        time.sleep(5.0)

    def adjust_game_time():
        tap(*points["ADJUST_GAME_TIME_P1"])
        time.sleep(1)
        tap(*points["ADJUST_GAME_TIME_P2"])
        time.sleep(1)

        swipe(*points["ADJUST_GAME_TIME_S1"], *points["ADJUST_GAME_TIME_S2"], 300)
        time.sleep(0.2)
        swipe(*points["ADJUST_GAME_TIME_S2"], *points["ADJUST_GAME_TIME_S3"], 300)
        time.sleep(0.2)
        swipe(*points["ADJUST_GAME_TIME_S3"], *points["ADJUST_GAME_TIME_S4"], 300)
        time.sleep(0.2)
        swipe(*points["ADJUST_GAME_TIME_S4"], *points["ADJUST_GAME_TIME_S5"], 300)
        time.sleep(0.3)

        tap(*points["ADJUST_GAME_TIME_P3"])
        time.sleep(20)
        tap(*points["ADJUST_GAME_TIME_P4"])
        time.sleep(5)

    return {
        "tap": tap,
        "swipe": swipe,
        "move": move,
        "climb": climb,
        "swim": swim,
        "attack": attack,
        "heavy_attack": heavy_attack,
        "long_attack": long_attack,
        "jump": jump,
        "dash": dash,
        "run": run,
        "util": util,
        "long_util": long_util,
        "glide": glide,
        "sleep": sleep,
        "turn_180": turn_180,
        "turn_right_90": turn_right_90,
        "turn_left_90": turn_left_90,
        "turn_right_45": turn_right_45,
        "turn_left_45": turn_left_45,
        "turn_right_30": turn_right_30,
        "turn_left_30": turn_left_30,
        "turn_right_135": turn_right_135,
        "turn_left_135": turn_left_135,
        "open_map": open_map,
        "confirm_teleport": confirm_teleport,
        "adjust_game_time": adjust_game_time,
        "POINTS": points,
        "BASE_RESOLUTION": base_wh,
        "TARGET_RESOLUTION": target_wh,
    }


def bind_actions(
    namespace: MutableMapping[str, object],
    offsets: OffsetMap | None = None,
    mapping_module: str = BASE_MAPPING_MODULE,
    use_env_offsets: bool = False,
):
    exports = build_actions(mapping_module=mapping_module, offsets=offsets, use_env_offsets=use_env_offsets)
    namespace.update(exports)
    namespace["OFFSETS"] = dict(offsets or {})
    namespace["MAPPING_MODULE"] = mapping_module


# Baseline export: baseline resolution + no offset.
bind_actions(globals(), offsets={}, mapping_module=BASE_MAPPING_MODULE, use_env_offsets=False)
