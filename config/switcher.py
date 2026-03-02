import importlib
import json
import os
import time
from copy import deepcopy
from typing import Dict, Optional, Tuple

from engine.executor import exec_action


def _load_action_resolution() -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
    actions_module_name = os.environ.get("GLOBAL_ACTIONS_MODULE", "actions.global_actions")
    try:
        actions_module = importlib.import_module(actions_module_name)
    except ModuleNotFoundError:
        actions_module = importlib.import_module("actions.global_actions")

    base = getattr(actions_module, "BASE_RESOLUTION", None)
    target = getattr(actions_module, "TARGET_RESOLUTION", None)
    if not base or not target:
        return None
    return (int(base[0]), int(base[1])), (int(target[0]), int(target[1]))


def _scale_xy(x: int, y: int, src: Tuple[int, int], dst: Tuple[int, int]) -> Tuple[int, int]:
    sx = dst[0] / src[0]
    sy = dst[1] / src[1]
    return round(x * sx), round(y * sy)


def _map_step(step: Dict, src: Tuple[int, int], dst: Tuple[int, int]) -> Dict:
    mapped = deepcopy(step)
    t = mapped.get("type")
    if t == "tap":
        mapped["x"], mapped["y"] = _scale_xy(mapped["x"], mapped["y"], src, dst)
    elif t == "swipe":
        x1, y1 = mapped["start"]
        x2, y2 = mapped["end"]
        mapped["start"] = list(_scale_xy(x1, y1, src, dst))
        mapped["end"] = list(_scale_xy(x2, y2, src, dst))
    return mapped


def apply_render_config(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    resolution = _load_action_resolution()
    if resolution is None:
        for step in data["steps"]:
            exec_action(step)
    else:
        src_res, dst_res = resolution
        for step in data["steps"]:
            exec_action(_map_step(step, src_res, dst_res))

    time.sleep(1)
