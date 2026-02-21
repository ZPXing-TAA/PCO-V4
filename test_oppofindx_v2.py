import importlib.util
import os

ROUTE_SUFFIX = 1

os.environ["GLOBAL_ACTIONS_MODULE"] = "actions.actions_oppo"
from engine.runner import ACTION_TABLE
from recording.recorder import Recorder
from tools.debug_run_route import debug_run_route


def _load_route_module(route_suffix: int):
    base_dir = os.path.dirname(__file__)
    route_path = os.path.join(base_dir, "routes", "hybrid", "natlan_v2", f"{route_suffix}.py")
    module_name = f"natlan_hybrid_{route_suffix}"
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load route module from {route_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _port_to_land(xp: int, yp: int, wp: int = 1272):
    xl = yp
    yl = (wp - 1) - xp
    return xl, yl


def _convert_xy(x: int, y: int):
    src_w = int(os.environ.get("AUTO_SRC_W", "2848"))
    src_h = int(os.environ.get("AUTO_SRC_H", "1276"))
    dst_w = int(os.environ.get("AUTO_DST_W", "2772"))
    dst_h = int(os.environ.get("AUTO_DST_H", "1272"))
    sx = dst_w / src_w
    sy = dst_h / src_h
    return round(x * sx), round(y * sy)


def _build_portal(route_suffix: int, portal_xy):
    portal = list(portal_xy)
    portal = list(_convert_xy(*portal))
    return list(_port_to_land(*portal))


def main():
    route_module = _load_route_module(ROUTE_SUFFIX)
    route = route_module.ROUTE

    current_portal = _build_portal(ROUTE_SUFFIX, route_module.PORTAL)
    next_portal_raw = getattr(route_module, "NEXT_PORTAL", None)
    if not next_portal_raw:
        raise ValueError(f"Route {ROUTE_SUFFIX} has no NEXT_PORTAL. Please fill NEXT_PORTAL in route file.")
    next_portal = _build_portal(ROUTE_SUFFIX, next_portal_raw)

    recorder = Recorder(f"tests/route_{ROUTE_SUFFIX}_then_next.mp4")

    try:
        print(f"[TEST] Run #1 route {ROUTE_SUFFIX} with current portal: {current_portal}")
        debug_run_route(route, portal=current_portal, recorder=recorder)

        print(f"[TEST] Run #2 route {ROUTE_SUFFIX} with NEXT_PORTAL: {next_portal}")
        debug_run_route(route, portal=next_portal, recorder=recorder)
    finally:
        recorder.stop()


if __name__ == "__main__":
    main()
