import json
import os
import time
import importlib
from config.switcher import apply_render_config
from recording.recorder import Recorder

ROUTE_SUFFIX = 6

route_module = importlib.import_module(f"routes.natlan_hybrid_{ROUTE_SUFFIX}")
PORTAL = route_module.PORTAL
os.environ["GLOBAL_ACTIONS_MODULE"] = "actions.actions_huaweipura"
from engine.runner import ACTION_TABLE


PROJECT_ROOT = os.environ.get(
    "AUTO_PROJECT_ROOT",
    os.path.expanduser("~/CODEZONE/PCO/Power-Optimization"),
)
CONFIG_ROOT = os.environ.get("AUTO_CONFIG_ROOT_OFX", os.path.join(PROJECT_ROOT, "render_configs_ofx"))
VIDEO_BASE = os.environ.get("AUTO_VIDEO_BASE_OFX", os.path.join(PROJECT_ROOT, "Recordings", "ofx"))
START_FROM = 1
Skip_recorded = 0
GLOBAL_COUNT_PATH = os.path.join(VIDEO_BASE, "_action_counts.json")
TOTAL_CONFIGS = 80
# Per-country starting index offsets by action. Example: natlan glide has 10 pre-recorded.
ACTION_BASE_COUNTS = {
    "natlan": {
        "glide": 10,
        "run": 10,
        "swim": 9
    }
}

def infer_route_info(route_module_ref):

    mod = getattr(route_module_ref, "__name__", None)
    if not mod:
        return "unknown", "route"

    route_file = mod.split(".")[-1]
    parts = route_file.split("_")
    if len(parts) >= 2:
        country = parts[0]
        route_suffix = "_".join(parts[1:])
    else:
        country = "unknown"
        route_suffix = route_file

    if len(parts) >= 3:
        route_label = f"{parts[1][0]}{parts[-1]}"
    else:
        route_label = route_suffix

    return country, route_label


def _config_id(res_folder, file_name):
    base = os.path.splitext(file_name)[0]
    if res_folder:
        return f"{res_folder}_{base}"
    return base


def _next_action_name(route, start_index):
    for step in route[start_index + 1:]:
        name = step[0]
        if name not in ("record_start", "record_stop"):
            return name
    return "unknown"

def _planned_video_paths(route, video_base_dir, config_id, country, route_label, action_counts):
    temp_counts = dict(action_counts)
    paths = []
    for i, step in enumerate(route):
        if step[0] != "record_start":
            continue
        action_name = _next_action_name(route, i)
        temp_counts[action_name] = temp_counts.get(action_name, 0) + 1
        index = temp_counts[action_name]
        action_dir = os.path.join(video_base_dir, action_name, f"{country}_{index}_{route_label}")
        paths.append(os.path.join(action_dir, f"{config_id}.mp4"))
    return paths, temp_counts


def _route_end_counts(route, action_counts):
    temp_counts = dict(action_counts)
    for i, step in enumerate(route):
        if step[0] != "record_start":
            continue
        action_name = _next_action_name(route, i)
        temp_counts[action_name] = temp_counts.get(action_name, 0) + 1
    return temp_counts


def _load_action_counts(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _save_action_counts(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=True, indent=2, sort_keys=True)


def _get_country_counts(country, stored_counts):
    base = dict(ACTION_BASE_COUNTS.get(country, {}))
    if country not in stored_counts:
        return base
    merged = base
    merged.update(stored_counts.get(country, {}))
    return merged


def run_route_hybrid(route, portal, video_base_dir, config_id, country, route_label, action_counts):
    recorder = None
    try:
        for i, step in enumerate(route):
            name = step[0]
            args = step[1:] if len(step) > 1 else []
            print(f"[ACTION] {name} {tuple(args)}")

            if name == "record_start":
                action_name = _next_action_name(route, i)
                action_counts[action_name] = action_counts.get(action_name, 0) + 1
                index = action_counts[action_name]
                action_dir = os.path.join(video_base_dir, action_name, f"{country}_{index}_{route_label}")
                os.makedirs(action_dir, exist_ok=True)

                video_path = os.path.join(action_dir, f"{config_id}.mp4")

                if recorder is not None:
                    recorder.stop()
                recorder = Recorder(video_path)
                recorder.start()
                continue

            if name == "record_stop":
                if recorder is not None:
                    recorder.stop()
                    recorder = None
                continue

            if name == "teleport":
                ACTION_TABLE["teleport"](portal)
            else:
                ACTION_TABLE[name](*args)

            time.sleep(0.4)
    finally:
        if recorder is not None:
            recorder.stop()


def run_all_configs(root_folder, max_configs=80, start_from=0):
    count = 0
    seen = 0
    target_start = max(1, start_from)

    country, route_label = infer_route_info(route_module)
    video_root = VIDEO_BASE
    os.makedirs(video_root, exist_ok=True)
    action_counts_by_country = _load_action_counts(GLOBAL_COUNT_PATH)
    base_counts = _get_country_counts(country, action_counts_by_country)
    route_end_counts = _route_end_counts(route_module.ROUTE, base_counts)

    # teleport(PORTAL)
    time.sleep(3.0)

    for res_folder in sorted(os.listdir(root_folder)):
        full_path = os.path.join(root_folder, res_folder)
        if not os.path.isdir(full_path):
            continue

        for file in sorted(os.listdir(full_path)):
            if not file.endswith(".json"):
                continue

            if count >= max_configs:
                return

            json_path = os.path.join(full_path, file)
            config_id = _config_id(res_folder, file)

            seen += 1
            if seen < target_start:
                continue
            country_counts = dict(base_counts)
            if Skip_recorded:
                expected_videos, planned_counts = _planned_video_paths(
                    route=route_module.ROUTE,
                    video_base_dir=video_root,
                    config_id=config_id,
                    country=country,
                    route_label=route_label,
                    action_counts=country_counts
                )
                if expected_videos and all(os.path.exists(p) for p in expected_videos):
                    print(f"[SKIP]  {json_path} (videos already exist)")
                    count += 1
                    continue

            print(f"[CONFIG]  {json_path}")
            apply_render_config(json_path)

            run_route_hybrid(
                route=route_module.ROUTE,
                portal=route_module.PORTAL,
                video_base_dir=video_root,
                config_id=config_id,
                country=country,
                route_label=route_label,
                action_counts=country_counts
            )

            count += 1
    if count == TOTAL_CONFIGS:
        action_counts_by_country[country] = route_end_counts
        _save_action_counts(GLOBAL_COUNT_PATH, action_counts_by_country)
    else:
        print(f"[INFO] 完成 {count}/{TOTAL_CONFIGS} 个配置，未写入全局计数。")


try:
    run_all_configs(CONFIG_ROOT, start_from=START_FROM)
except KeyboardInterrupt:
    print("[INTERRUPT] 收到 Ctrl+C，正在清理录制进程...")
