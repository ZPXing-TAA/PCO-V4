import importlib.util
import os

ROUTE_SUFFIX = 7
SKIP_TELEPORT = 1

os.environ["GLOBAL_ACTIONS_MODULE"] = "actions.actions_huaweipura"


def _load_route_module(route_suffix: int):
    base_dir = os.path.dirname(__file__)
    route_path = os.path.join(base_dir, "routes", "hybrid", "natlan", f"{route_suffix}.py")
    module_name = f"natlan_hybrid_{route_suffix}"
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load route module from {route_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


route_module = _load_route_module(ROUTE_SUFFIX)
ROUTE = route_module.ROUTE
PORTAL = list(route_module.PORTAL)
if SKIP_TELEPORT:
    ROUTE = [step for step in ROUTE if step and step[0] != "teleport"]

from recording.recorder import Recorder
from tools.debug_run_route import debug_run_route

PROJECT_ROOT = os.environ.get(
    "AUTO_PROJECT_ROOT",
    os.path.expanduser("~/CODEZONE/PCO/Power-Optimization"),
)
VIDEO_DIR = os.environ.get("AUTO_DEBUG_VIDEO_DIR", r"D:/recordings/debug")
VIDEO_NAME = "test_huawei_pura"

os.makedirs(VIDEO_DIR, exist_ok=True)
video_path = os.path.join(VIDEO_DIR, f"{VIDEO_NAME}.mp4")
recorder = Recorder(video_path)

try:
    debug_run_route(ROUTE, portal=PORTAL, recorder=recorder)
finally:
    recorder.stop()
