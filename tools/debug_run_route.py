import time
from engine.runner import ACTION_TABLE

# Debug helper: optionally skip actions
SKIP_ACTIONS = set()


def debug_run_route(route, portal=None, recorder=None):
    print("\n[DEBUG] Start executing route (debug mode)\n")

    for step in route:
        name = step[0]
        args = step[1:] if len(step) > 1 else []

        if name in SKIP_ACTIONS:
            print(f"[DEBUG] Skip action: {name}")
            continue

        if name == "record_start":
            if recorder is None:
                print("[DEBUG] Skip action: record_start (no recorder)")
            else:
                recorder.start()
            continue

        if name == "record_stop":
            if recorder is None:
                print("[DEBUG] Skip action: record_stop (no recorder)")
            else:
                recorder.stop()
            continue

        if name == "teleport":
            if portal is None:
                print("[DEBUG] Skip action: teleport (no portal)")
            else:
                ACTION_TABLE["teleport"](portal)
            continue

        print(f"[DEBUG] Run action: {name} {args}")
        ACTION_TABLE[name](*args)

        time.sleep(0.5)

    print("\n[DEBUG] Route finished\n")
