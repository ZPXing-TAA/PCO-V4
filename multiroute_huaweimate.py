import importlib.util
import json
import os
import time
from typing import Dict, List, Optional, Tuple

from config.switcher import apply_render_config
from recording.recorder import Recorder

# Huawei Mate: if you have a dedicated module, override this env var before run.
os.environ["GLOBAL_ACTIONS_MODULE"] = os.environ.get(
    "GLOBAL_ACTIONS_MODULE",
    "actions.actions_huaweimate",
)
from engine.runner import ACTION_TABLE

ROUTE_ROOT = os.path.join(os.path.dirname(__file__), "routes", "hybrid", "natlan_v2")
PROJECT_ROOT = os.environ.get(
    "AUTO_PROJECT_ROOT",
    os.path.expanduser("~/CODEZONE/PCO/Power-Optimization"),
)
CONFIG_ROOT = os.environ.get(
    "AUTO_CONFIG_ROOT_HUAWEIMATE",
    os.path.join(PROJECT_ROOT, "render_configs"),
)
VIDEO_BASE = os.environ.get(
    "AUTO_VIDEO_BASE_HUAWEIMATE",
    r"D:/recordings/huaweimate",
)
GLOBAL_COUNT_PATH = os.path.join(VIDEO_BASE, "_action_counts.json")

# None: 自动扫描 natlan 目录下的数字 route（1.py, 2.py, ...）
# 示例: [1, 2, 3]
ROUTE_SUFFIXES: Optional[List[int]] = None
SKIP_ROUTE_SUFFIXES: List[int] = []

# 每条 route 跑多少个渲染配置
TOTAL_CONFIGS_PER_ROUTE = 80
START_FROM_CONFIG = 1
SKIP_RECORDED = 0

STEP_DELAY = 0.4
ROUTE_GAP = 1.0
RECORD_START_SETTLE_SEC = float(os.environ.get("AUTO_RECORD_START_SETTLE_SEC", "0.3"))
ROLLBACK_CHECKPOINT = os.environ.get("AUTO_ROLLBACK_CHECKPOINT", "").strip()
ROLLBACK_ONLY = os.environ.get("AUTO_ROLLBACK_ONLY", "0").strip() == "1"
RESTART_FROM_ROUTE = os.environ.get("AUTO_RESTART_FROM_ROUTE", "").strip()

ACTION_BASE_COUNTS = {
    "natlan": {
        "glide": 0,
        "run": 0,
        "swim": 0,
    }
}


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

SRC_W = int(os.environ.get("AUTO_SRC_W", "2848"))
SRC_H = int(os.environ.get("AUTO_SRC_H", "1276"))
DST_W = int(os.environ.get("AUTO_DST_W", "2720"))
DST_H = int(os.environ.get("AUTO_DST_H", "1260"))
PORT_W = int(os.environ.get("AUTO_PORT_W", str(DST_H)))


def _convert_xy(x: int, y: int) -> Tuple[int, int]:
    sx = DST_W / SRC_W
    sy = DST_H / SRC_H
    return round(x * sx), round(y * sy)


def _load_route_module(route_suffix: int):
    route_path = os.path.join(ROUTE_ROOT, f"{route_suffix}.py")
    module_name = f"natlan_hybrid_{route_suffix}"
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


def _port_to_land(xp: int, yp: int, wp: int = PORT_W) -> Tuple[int, int]:
    xl = yp
    yl = (wp - 1) - xp
    return xl, yl


def _build_portal(route_suffix: int, portal_xy) -> List[int]:
    portal = list(portal_xy)
    portal = list(_convert_xy(*portal))
    portal = list(_port_to_land(*portal))
    return portal


def _collect_configs(root_folder: str, start_from: int, limit: int):
    seen = 0
    picked = []
    target_start = max(1, start_from)

    for res_folder in sorted(os.listdir(root_folder)):
        full_path = os.path.join(root_folder, res_folder)
        if not os.path.isdir(full_path):
            continue

        for file in sorted(os.listdir(full_path)):
            if not file.endswith(".json"):
                continue
            seen += 1
            if seen < target_start:
                continue

            config_id = f"{res_folder}_{os.path.splitext(file)[0]}" if res_folder else os.path.splitext(file)[0]
            picked.append((os.path.join(full_path, file), config_id))
            if len(picked) >= limit:
                return picked
    return picked


def _next_action_name(route, start_index):
    for step in route[start_index + 1:]:
        name = step[0]
        if name not in ("record_start", "record_stop"):
            return name
    return "unknown"


def _build_route_action_indices(route, action_counts):
    temp_counts = dict(action_counts)
    indexed = []
    for i, step in enumerate(route):
        if step[0] != "record_start":
            continue
        action_name = _next_action_name(route, i)
        temp_counts[action_name] = temp_counts.get(action_name, 0) + 1
        indexed.append((action_name, temp_counts[action_name]))
    return indexed


def _route_end_counts(route, action_counts):
    temp_counts = dict(action_counts)
    for i, step in enumerate(route):
        if step[0] != "record_start":
            continue
        action_name = _next_action_name(route, i)
        temp_counts[action_name] = temp_counts.get(action_name, 0) + 1
    return temp_counts


def _planned_video_paths(video_base_dir, config_id, country, route_label, route_action_indices):
    paths = []
    for action_name, index in route_action_indices:
        action_dir = os.path.join(video_base_dir, action_name, f"{country}_{index}_{route_label}")
        paths.append(os.path.join(action_dir, f"{config_id}.mp4"))
    return paths


def _parse_rollback_checkpoint(raw: str) -> Optional[Tuple[int, int]]:
    if not raw:
        return None
    parts = [item.strip() for item in raw.split(":", 1)]
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError(
            "Invalid AUTO_ROLLBACK_CHECKPOINT format. Use 'routeSuffix:recordStartIndex', e.g. 7:17"
        )

    route_suffix = int(parts[0])
    record_start_index = int(parts[1])
    if route_suffix <= 0 or record_start_index <= 0:
        raise ValueError("AUTO_ROLLBACK_CHECKPOINT values must be positive integers.")
    return route_suffix, record_start_index


def _advance_counts_by_route(route, action_counts: Dict, limit_record_starts: Optional[int] = None) -> Dict:
    temp_counts = dict(action_counts)
    consumed = 0
    for i, step in enumerate(route):
        if step[0] != "record_start":
            continue
        if limit_record_starts is not None and consumed >= limit_record_starts:
            break
        action_name = _next_action_name(route, i)
        temp_counts[action_name] = temp_counts.get(action_name, 0) + 1
        consumed += 1
    return temp_counts


def _rebuild_counts_to_checkpoint(route_suffixes: List[int], checkpoint_route: int, checkpoint_record_start: int) -> Dict:
    country = "natlan"
    rebuilt = dict(ACTION_BASE_COUNTS.get(country, {}))
    target_found = False
    for suffix in route_suffixes:
        route_module = _load_route_module(suffix)
        route = route_module.ROUTE
        if suffix < checkpoint_route:
            rebuilt = _advance_counts_by_route(route, rebuilt)
            continue
        if suffix == checkpoint_route:
            rebuilt = _advance_counts_by_route(route, rebuilt, limit_record_starts=checkpoint_record_start - 1)
            target_found = True
            break
        break

    if not target_found:
        raise ValueError(
            f"Rollback route {checkpoint_route} not found in active route list: {route_suffixes}"
        )
    return {country: rebuilt}


def _apply_rollback_if_needed(route_suffixes: List[int], action_counts_by_country: Dict, checkpoint_raw: str) -> bool:
    checkpoint = _parse_rollback_checkpoint(checkpoint_raw)
    if checkpoint is None:
        return False

    checkpoint_route, checkpoint_record_start = checkpoint
    rebuilt_counts = _rebuild_counts_to_checkpoint(
        route_suffixes=route_suffixes,
        checkpoint_route=checkpoint_route,
        checkpoint_record_start=checkpoint_record_start,
    )
    action_counts_by_country.clear()
    action_counts_by_country.update(rebuilt_counts)
    _save_action_counts(GLOBAL_COUNT_PATH, action_counts_by_country)
    print(
        "[ROLLBACK] Applied global counter rollback to "
        f"route {checkpoint_route} record_start #{checkpoint_record_start}."
    )
    print(f"[ROLLBACK] New counts: {json.dumps(action_counts_by_country, ensure_ascii=False, sort_keys=True)}")
    return True


def _load_action_counts(path: str) -> Dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_action_counts(path: str, data: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, indent=2, sort_keys=True)


def _get_country_counts(country: str, stored_counts: Dict) -> Dict:
    base = dict(ACTION_BASE_COUNTS.get(country, {}))
    if country not in stored_counts:
        return base
    merged = dict(base)
    merged.update(stored_counts.get(country, {}))
    return merged


def run_route_hybrid(
    route,
    current_portal,
    video_base_dir,
    config_id,
    country,
    route_label,
    route_action_indices,
    teleport_portal=None,
):
    recorder = None
    record_start_index = 0
    teleport_used = False
    try:
        for i, step in enumerate(route):
            name = step[0]
            args = step[1:] if len(step) > 1 else []
            print(f"[ACTION] {name} {tuple(args)}")

            if name == "record_start":
                if record_start_index >= len(route_action_indices):
                    raise ValueError("record_start count does not match precomputed route action indices.")
                action_name, index = route_action_indices[record_start_index]
                record_start_index += 1
                action_dir = os.path.join(video_base_dir, action_name, f"{country}_{index}_{route_label}")
                os.makedirs(action_dir, exist_ok=True)
                video_path = os.path.join(action_dir, f"{config_id}.mp4")

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
                # route 内 teleport 统一回到当前 route 的 portal，不解析 current/next marker
                target_portal = teleport_portal if teleport_portal is not None else current_portal
                ACTION_TABLE["teleport"](target_portal)
                teleport_used = True
            else:
                ACTION_TABLE[name](*args)

            time.sleep(STEP_DELAY)
    finally:
        if recorder is not None:
            recorder.stop()
    return teleport_used


def run_one_route(route_suffix: int, configs, action_counts_by_country: Dict):
    route_module = _load_route_module(route_suffix)
    route = route_module.ROUTE
    current_portal = _build_portal(route_suffix, route_module.PORTAL)

    next_portal_raw = getattr(route_module, "NEXT_PORTAL", None)
    next_portal = _build_portal(route_suffix, next_portal_raw) if next_portal_raw else None

    country = "natlan"
    route_label = f"h{route_suffix}"
    base_counts = _get_country_counts(country, action_counts_by_country)
    route_action_indices = _build_route_action_indices(route, base_counts)
    route_end_counts = _route_end_counts(route, base_counts)
    completed = 0
    executed_configs = 0
    transitioned_in_last_run = False

    print(f"\n[ROUTE] Start route {route_suffix}")
    print(f"[ROUTE] Current portal: {current_portal}")
    if next_portal is not None:
        print(f"[ROUTE] Next portal: {next_portal}")

    for idx, (json_path, config_id) in enumerate(configs, start=1):
        if completed >= TOTAL_CONFIGS_PER_ROUTE:
            break

        if SKIP_RECORDED:
            expected_videos = _planned_video_paths(
                video_base_dir=VIDEO_BASE,
                config_id=config_id,
                country=country,
                route_label=route_label,
                route_action_indices=route_action_indices,
            )
            if expected_videos and all(os.path.exists(p) for p in expected_videos):
                print(f"[SKIP][R{route_suffix}] {json_path}")
                completed += 1
                continue

        print(f"[CONFIG][R{route_suffix}][{idx}/{len(configs)}] {json_path}")

        # Adjust time before the 6th, 11th, 16th... actual recording run.
        if executed_configs > 0 and executed_configs % 5 == 0:
            if "adjust_game_time" in ACTION_TABLE:
                print(f"[TIME][R{route_suffix}] adjust before config #{executed_configs + 1}")
                ACTION_TABLE["adjust_game_time"]()
            else:
                print("[WARN] adjust_game_time not available in current action module.")

        apply_render_config(json_path)
        is_last_config = completed == TOTAL_CONFIGS_PER_ROUTE - 1
        teleport_target = next_portal if (is_last_config and next_portal is not None) else current_portal

        teleport_used = run_route_hybrid(
            route=route,
            current_portal=current_portal,
            video_base_dir=VIDEO_BASE,
            config_id=config_id,
            country=country,
            route_label=route_label,
            route_action_indices=route_action_indices,
            teleport_portal=teleport_target,
        )
        if is_last_config and teleport_target == next_portal and teleport_used:
            transitioned_in_last_run = True

        executed_configs += 1
        completed += 1

    if completed == TOTAL_CONFIGS_PER_ROUTE:
        action_counts_by_country[country] = dict(route_end_counts)
        _save_action_counts(GLOBAL_COUNT_PATH, action_counts_by_country)
        print(f"[ROUTE] Finished route {route_suffix} ({completed}/{TOTAL_CONFIGS_PER_ROUTE})")
    else:
        print(
            f"[WARN] Route {route_suffix} only completed {completed}/{TOTAL_CONFIGS_PER_ROUTE}; "
            "global action counts not saved."
        )
    return next_portal, completed, transitioned_in_last_run


def run_multi_routes():
    route_suffixes = ROUTE_SUFFIXES if ROUTE_SUFFIXES is not None else _discover_route_suffixes()
    if not route_suffixes:
        raise ValueError("No route suffix found.")
    skip_suffixes = set(_resolve_skip_route_suffixes())
    if skip_suffixes:
        route_suffixes = [s for s in route_suffixes if s not in skip_suffixes]
        print(f"[INFO] Skip routes: {sorted(skip_suffixes)}")
    if not route_suffixes:
        raise ValueError("No route suffix left after skip filter.")

    rollback_route_suffixes = list(route_suffixes)
    effective_checkpoint = ROLLBACK_CHECKPOINT
    if RESTART_FROM_ROUTE:
        if not RESTART_FROM_ROUTE.isdigit() or int(RESTART_FROM_ROUTE) <= 0:
            raise ValueError("AUTO_RESTART_FROM_ROUTE must be a positive integer route suffix.")
        restart_route = int(RESTART_FROM_ROUTE)
        if restart_route not in route_suffixes:
            raise ValueError(f"AUTO_RESTART_FROM_ROUTE={restart_route} not in active routes: {route_suffixes}")
        restart_index = route_suffixes.index(restart_route)
        route_suffixes = route_suffixes[restart_index:]
        if not effective_checkpoint:
            effective_checkpoint = f"{restart_route}:1"
        print(f"[RESTART] Restart from route {restart_route} (from first config).")
        print(f"[RESTART] Active routes: {route_suffixes}")

    configs = _collect_configs(CONFIG_ROOT, START_FROM_CONFIG, TOTAL_CONFIGS_PER_ROUTE)
    if not configs:
        raise ValueError("No config json found.")

    os.makedirs(VIDEO_BASE, exist_ok=True)
    action_counts_by_country = _load_action_counts(GLOBAL_COUNT_PATH)
    rollback_applied = _apply_rollback_if_needed(
        rollback_route_suffixes,
        action_counts_by_country,
        effective_checkpoint,
    )
    print(f"[INFO] Route list: {route_suffixes}")
    print(f"[INFO] Config count per route: {len(configs)}")

    if rollback_applied and ROLLBACK_ONLY:
        print("[ROLLBACK] AUTO_ROLLBACK_ONLY=1, exit after rollback.")
        return

    for idx, route_suffix in enumerate(route_suffixes):
        next_portal, completed, transitioned_in_last_run = run_one_route(
            route_suffix, configs, action_counts_by_country
        )

        # 每条 route 完成后，额外点击本 route 的 NEXT_PORTAL，进入下一条 route 起点。
        if idx < len(route_suffixes) - 1:
            if completed < TOTAL_CONFIGS_PER_ROUTE:
                raise ValueError(
                    f"Route {route_suffix} did not complete {TOTAL_CONFIGS_PER_ROUTE} configs, "
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
