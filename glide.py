import os
import time
from pipeline.run_pipeline import run_one_config
import routes.natlan_glide_10 as route_module
from portals.natlan_glide_3 import PORTAL
from engine.runner import teleport

PROJECT_ROOT = os.environ.get(
    "AUTO_PROJECT_ROOT",
    os.path.expanduser("~/CODEZONE/PCO/Power-Optimization"),
)
CONFIG_ROOT = os.environ.get("AUTO_CONFIG_ROOT", os.path.join(PROJECT_ROOT, "render_configs"))
VIDEO_BASE = os.environ.get("AUTO_VIDEO_BASE", os.path.join(PROJECT_ROOT, "Recordings", "glide"))
START_FROM = 0


def infer_route_name(route_module_ref):
    """
    根据 routes 目录下的路线文件名推断 route 名
    例如 routes/natlan_glide_8.py → natlan_glide_8
    """
    mod = getattr(route_module_ref, "__name__", None)
    if not mod:
        return "unknown_route"

    route_name = mod.split(".")[-1]
    parts = route_name.split("_")
    if len(parts) >= 3:
        route_name = f"{parts[0]}_{parts[-1]}"
    return route_name


def run_all_configs(root_folder, max_configs=999, start_from=0):
    count = 0
    skipped = 0

    # ===== 根据 ROUTE 自动生成 video path =====
    route_name = infer_route_name(route_module)
    video_root = os.path.join(VIDEO_BASE, route_name)
    os.makedirs(video_root, exist_ok=True)

    # ===== 只传送一次 =====
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

            if skipped < start_from:
                skipped += 1
                continue

            video_dir = os.path.join(video_root, res_folder)
            os.makedirs(video_dir, exist_ok=True)

            video_name = os.path.splitext(file)[0]

            run_one_config(
                json_path=json_path,
                route=route_module.ROUTE,
                portal=PORTAL,
                video_dir=video_dir,
                video_name=video_name
            )

            count += 1


run_all_configs(CONFIG_ROOT, start_from=START_FROM)
