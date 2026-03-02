import importlib.util
import os

ROUTE_SUFFIX = 16

os.environ["GLOBAL_ACTIONS_MODULE"] = "actions.actions_huaweipura"
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


def main():
    route_module = _load_route_module(ROUTE_SUFFIX)
    route = route_module.ROUTE

    current_portal = list(route_module.PORTAL)
    next_portal_raw = getattr(route_module, "NEXT_PORTAL", None)
    if not next_portal_raw:
        raise ValueError(f"Route {ROUTE_SUFFIX} has no NEXT_PORTAL. Please fill NEXT_PORTAL in route file.")
    next_portal = list(next_portal_raw)

    recorder = Recorder(f"tests/route_{ROUTE_SUFFIX}_then_next_huaweipura.mp4")

    try:
        print(f"[TEST] Run #1 route {ROUTE_SUFFIX} with current portal: {current_portal}")
        debug_run_route(route, portal=current_portal, recorder=recorder)

        print(f"[TEST] Run #2 route {ROUTE_SUFFIX} with NEXT_PORTAL: {next_portal}")
        debug_run_route(route, portal=next_portal, recorder=recorder)
    finally:
        recorder.stop()


if __name__ == "__main__":
    main()
