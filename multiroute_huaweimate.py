import importlib.util
import os
import time
from typing import List, Optional, Sequence, Tuple

from config.switcher import apply_render_config, load_action_resolution, scale_xy
from engine.route_segments import (
    RouteSegment,
    build_route_segments,
    cleanup_route_outputs,
    segment_video_path,
    validate_expected_videos,
)
from recording.recorder import Recorder

os.environ["GLOBAL_ACTIONS_MODULE"] = os.environ.get(
    "GLOBAL_ACTIONS_MODULE",
    "actions.actions_huaweimate",
)
from engine.runner import ACTION_TABLE

ROUTE_ROOT = os.path.join(os.path.dirname(__file__), "routes", "natlan_v2")
DEFAULT_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECT_ROOT = os.environ.get("AUTO_PROJECT_ROOT", DEFAULT_PROJECT_ROOT)
CONFIG_ROOT = os.environ.get(
    "AUTO_CONFIG_ROOT_HUAWEIMATE",
    os.path.join(PROJECT_ROOT, "render_configs"),
)
VIDEO_BASE = os.environ.get(
    "AUTO_VIDEO_BASE_HUAWEIMATE",
    r"D:/recordings/huaweimate",
)

ROUTE_SUFFIXES: Optional[List[int]] = None
SKIP_ROUTE_SUFFIXES: List[int] = [4, 22]
TOTAL_CONFIGS_PER_ROUTE = 80
START_FROM_ROUTE: Optional[int] = None
END_AT_ROUTE: Optional[int] = None

STEP_DELAY = 0.4
ROUTE_GAP = 1.0
RECORD_START_SETTLE_SEC = float(os.environ.get("AUTO_RECORD_START_SETTLE_SEC", "0.3"))
PORTAL_RESOLUTION = load_action_resolution()
if PORTAL_RESOLUTION is None:
    raise RuntimeError("Failed to load action resolution for portal scaling.")
PORTAL_SRC_RESOLUTION, PORTAL_DST_RESOLUTION = PORTAL_RESOLUTION


def _resolve_skip_route_suffixes() -> List[int]:
    skip = set(SKIP_ROUTE_SUFFIXES)
    raw = os.environ.get("AUTO_SKIP_ROUTE_SUFFIXES", "").strip()
    if not raw:
        return sorted(skip)

    for token in raw.split(","):
        item = token.strip()
        if not item:
            continue
        if not item.isdigit():
            raise ValueError(
                f"Invalid route suffix in AUTO_SKIP_ROUTE_SUFFIXES: {item!r}. "
                "Use comma-separated positive integers, e.g. 2,5,9"
            )
        skip.add(int(item))
    return sorted(skip)


def _resolve_optional_route_suffix(default_value: Optional[int], env_key: str) -> Optional[int]:
    raw = os.environ.get(env_key, "").strip()
    if not raw:
        return default_value
    if not raw.isdigit() or int(raw) <= 0:
        raise ValueError(f"{env_key} must be a positive integer route suffix.")
    return int(raw)


def _load_route_module(route_suffix: int):
    route_path = os.path.join(ROUTE_ROOT, f"{route_suffix}.py")
    module_name = f"natlan_route_{route_suffix}"
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load route module from {route_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _discover_route_suffixes() -> List[int]:
    suffixes: List[int] = []
    for name in os.listdir(ROUTE_ROOT):
        base, ext = os.path.splitext(name)
        if ext != ".py" or not base.isdigit():
            continue
        suffixes.append(int(base))
    suffixes.sort()
    return suffixes


def _apply_route_window(route_suffixes: List[int]) -> List[int]:
    start_from = _resolve_optional_route_suffix(START_FROM_ROUTE, "AUTO_START_FROM_ROUTE")
    end_at = _resolve_optional_route_suffix(END_AT_ROUTE, "AUTO_END_AT_ROUTE")

    if start_from is not None and start_from not in route_suffixes:
        raise ValueError(f"START_FROM_ROUTE={start_from} not in active routes: {route_suffixes}")
    if end_at is not None and end_at not in route_suffixes:
        raise ValueError(f"END_AT_ROUTE={end_at} not in active routes: {route_suffixes}")
    if start_from is not None and end_at is not None and start_from > end_at:
        raise ValueError("START_FROM_ROUTE must be <= END_AT_ROUTE.")

    if start_from is not None:
        route_suffixes = [suffix for suffix in route_suffixes if suffix >= start_from]
        print(f"[INFO] Start from route: {start_from}")
    if end_at is not None:
        route_suffixes = [suffix for suffix in route_suffixes if suffix <= end_at]
        print(f"[INFO] End at route: {end_at}")
    return route_suffixes


def _build_portal(portal_xy) -> List[int]:
    return list(scale_xy(portal_xy[0], portal_xy[1], PORTAL_SRC_RESOLUTION, PORTAL_DST_RESOLUTION))


def _collect_configs(root_folder: str, limit: int) -> List[Tuple[str, str]]:
    picked: List[Tuple[str, str]] = []
    for res_folder in sorted(os.listdir(root_folder)):
        full_path = os.path.join(root_folder, res_folder)
        if not os.path.isdir(full_path):
            continue

        for file_name in sorted(os.listdir(full_path)):
            if not file_name.endswith(".json"):
                continue
            config_id = (
                f"{res_folder}_{os.path.splitext(file_name)[0]}"
                if res_folder
                else os.path.splitext(file_name)[0]
            )
            picked.append((os.path.join(full_path, file_name), config_id))
            if len(picked) >= limit:
                return picked
    return picked


def run_route_recording(
    route: Sequence[Sequence[object]],
    current_portal: List[int],
    video_base_dir: str,
    config_id: str,
    segments: Sequence[RouteSegment],
    teleport_portal=None,
) -> bool:
    recorder = None
    segment_cursor = 0
    teleport_used = False
    try:
        for step in route:
            name = step[0]
            args = step[1:] if len(step) > 1 else []
            print(f"[ACTION] {name} {tuple(args)}")

            if name == "record_start":
                if segment_cursor >= len(segments):
                    raise ValueError("record_start count does not match precomputed route segments.")
                segment = segments[segment_cursor]
                segment_cursor += 1
                video_path = segment_video_path(video_base_dir, config_id, segment)
                os.makedirs(os.path.dirname(video_path), exist_ok=True)

                if recorder is not None:
                    recorder.stop()
                recorder = Recorder(video_path)
                recorder.start()
                time.sleep(RECORD_START_SETTLE_SEC)
                continue

            if name == "record_stop":
                if recorder is not None:
                    recorder.stop()
                    recorder = None
                continue

            if name == "teleport":
                target_portal = teleport_portal if teleport_portal is not None else current_portal
                ACTION_TABLE["teleport"](target_portal)
                teleport_used = True
            else:
                ACTION_TABLE[name](*args)

            time.sleep(STEP_DELAY)
    finally:
        if recorder is not None:
            recorder.stop()

    if segment_cursor != len(segments):
        raise ValueError(
            f"Route consumed {segment_cursor} record_start actions, expected {len(segments)}."
        )
    return teleport_used


def run_one_route(route_suffix: int, configs: Sequence[Tuple[str, str]]):
    route_module = _load_route_module(route_suffix)
    route = route_module.ROUTE
    current_portal = _build_portal(route_module.PORTAL)

    next_portal_raw = getattr(route_module, "NEXT_PORTAL", None)
    next_portal = _build_portal(next_portal_raw) if next_portal_raw else None

    country = "natlan"
    segments = build_route_segments(route, country, route_suffix)
    config_ids = [config_id for _, config_id in configs]
    transitioned_in_last_run = False

    print(f"\n[ROUTE] Start route {route_suffix}")
    print(f"[ROUTE] Current portal: {current_portal}")
    if next_portal is not None:
        print(f"[ROUTE] Next portal: {next_portal}")
    print(f"[ROUTE] Segment count: {len(segments)}")

    cleanup_route_outputs(VIDEO_BASE, segments)
    if segments:
        print(f"[ROUTE] Cleared stable outputs for route {route_suffix}.")

    for idx, (json_path, config_id) in enumerate(configs, start=1):
        print(f"[CONFIG][R{route_suffix}][{idx}/{len(configs)}] {json_path}")

        if idx > 1 and (idx - 1) % 3 == 0:
            if "adjust_game_time" in ACTION_TABLE:
                print(f"[TIME][R{route_suffix}] adjust before config #{idx}")
                ACTION_TABLE["adjust_game_time"]()
            else:
                print("[WARN] adjust_game_time not available in current action module.")

        apply_render_config(json_path)
        is_last_config = idx == len(configs)
        teleport_target = next_portal if (is_last_config and next_portal is not None) else current_portal
        teleport_used = run_route_recording(
            route=route,
            current_portal=current_portal,
            video_base_dir=VIDEO_BASE,
            config_id=config_id,
            segments=segments,
            teleport_portal=teleport_target,
        )
        if is_last_config and teleport_target == next_portal and teleport_used:
            transitioned_in_last_run = True

    missing = validate_expected_videos(config_ids, VIDEO_BASE, segments)
    if missing:
        preview = ", ".join(missing[:3])
        print(
            f"[WARN] Route {route_suffix} completed but missing {len(missing)} expected videos. "
            f"Examples: {preview}"
        )
    else:
        print(f"[ROUTE] Finished route {route_suffix} ({len(configs)}/{len(configs)})")
    return next_portal, len(configs), transitioned_in_last_run


def run_multi_routes():
    route_suffixes = ROUTE_SUFFIXES if ROUTE_SUFFIXES is not None else _discover_route_suffixes()
    if not route_suffixes:
        raise ValueError("No route suffix found.")

    route_suffixes = _apply_route_window(route_suffixes)
    skip_suffixes = set(_resolve_skip_route_suffixes())
    if skip_suffixes:
        route_suffixes = [suffix for suffix in route_suffixes if suffix not in skip_suffixes]
        print(f"[INFO] Skip routes: {sorted(skip_suffixes)}")
    if not route_suffixes:
        raise ValueError("No route suffix left after route window and skip filter.")

    configs = _collect_configs(CONFIG_ROOT, TOTAL_CONFIGS_PER_ROUTE)
    if not configs:
        raise ValueError("No config json found.")

    os.makedirs(VIDEO_BASE, exist_ok=True)
    print(f"[INFO] Route list: {route_suffixes}")
    print(f"[INFO] Config count per route: {len(configs)}")

    for idx, route_suffix in enumerate(route_suffixes):
        next_portal, completed, transitioned_in_last_run = run_one_route(route_suffix, configs)

        if idx < len(route_suffixes) - 1:
            if completed < len(configs):
                raise ValueError(
                    f"Route {route_suffix} did not complete {len(configs)} configs, "
                    "stop multi-route transition."
                )
            if next_portal is None:
                raise ValueError(
                    f"Route {route_suffix} has no NEXT_PORTAL. "
                    "Please add NEXT_PORTAL = [x, y] in this route file."
                )
            if transitioned_in_last_run:
                print(
                    f"[TRANSITION] Route {route_suffix} already moved to NEXT_PORTAL "
                    "during last config run."
                )
            else:
                print(f"[TRANSITION] Route {route_suffix} -> next route via NEXT_PORTAL {next_portal}")
                ACTION_TABLE["teleport"](next_portal)
                time.sleep(ROUTE_GAP)


if __name__ == "__main__":
    try:
        run_multi_routes()
    except KeyboardInterrupt:
        print("[INTERRUPT] Ctrl+C received, exit.")
