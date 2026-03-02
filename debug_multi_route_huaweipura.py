import importlib.util
import os
import time

os.environ["GLOBAL_ACTIONS_MODULE"] = os.environ.get(
    "GLOBAL_ACTIONS_MODULE",
    "actions.actions_huaweipura",
)
from engine.runner import ACTION_TABLE

# Validate route range [ROUTE_START, ROUTE_END]
ROUTE_START = 1
ROUTE_END = 10

# route folder: "natlan" or "natlan_v2"
ROUTE_SUBDIR = "natlan_v2"

STEP_DELAY = 0.4
ROUTE_GAP = 1.0


def _load_route_module(route_suffix: int):
    base_dir = os.path.dirname(__file__)
    route_path = os.path.join(base_dir, "routes", "hybrid", ROUTE_SUBDIR, f"{route_suffix}.py")
    module_name = f"natlan_hybrid_{route_suffix}"
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Failed to load route module from {route_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_portal(portal):
    return list(portal)


def _build_route_range(start_suffix: int, end_suffix: int):
    if start_suffix <= 0 or end_suffix <= 0:
        raise ValueError("ROUTE_START/ROUTE_END must be positive integers.")
    if start_suffix > end_suffix:
        raise ValueError("ROUTE_START must be <= ROUTE_END.")
    return list(range(start_suffix, end_suffix + 1))


def _run_route(route_suffix: int, route):
    print(f"\n[ROUTE] Start route {route_suffix}")

    for step in route:
        name = step[0]
        args = step[1:] if len(step) > 1 else []

        if name in ("record_start", "record_stop"):
            print(f"[DEBUG] Skip action: {name}")
            continue

        if name == "teleport":
            # For route-switch validation, skip in-route teleport reset.
            print(f"[DEBUG] Skip in-route teleport {tuple(args)}")
            time.sleep(STEP_DELAY)
            continue

        print(f"[ACTION] {name} {tuple(args)}")
        ACTION_TABLE[name](*args)
        time.sleep(STEP_DELAY)

    print(f"[ROUTE] Finish route {route_suffix}")


def run_multi_routes():
    route_suffixes = _build_route_range(ROUTE_START, ROUTE_END)
    print(f"[INFO] Route range: {route_suffixes} (folder: {ROUTE_SUBDIR}) | baseline mapping")

    for index, route_suffix in enumerate(route_suffixes):
        route_module = _load_route_module(route_suffix)

        _run_route(
            route_suffix=route_suffix,
            route=route_module.ROUTE,
        )

        next_portal_raw = getattr(route_module, "NEXT_PORTAL", None)
        if next_portal_raw is None:
            raise ValueError(
                f"Route {route_suffix} has no NEXT_PORTAL. "
                "Please add NEXT_PORTAL=[x, y] in this route file."
            )
        next_portal = _build_portal(next_portal_raw)
        print(f"[TRANSITION] Route {route_suffix} -> next via NEXT_PORTAL {next_portal}")
        ACTION_TABLE["teleport"](next_portal)
        if index < len(route_suffixes) - 1:
            time.sleep(ROUTE_GAP)


if __name__ == "__main__":
    try:
        run_multi_routes()
    except KeyboardInterrupt:
        print("[INTERRUPT] Ctrl+C received.")
