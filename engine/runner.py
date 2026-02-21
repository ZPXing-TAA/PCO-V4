import importlib
import os
import time

_ACTIONS_MODULE = os.environ.get("GLOBAL_ACTIONS_MODULE", "actions.global_actions")
try:
    A = importlib.import_module(_ACTIONS_MODULE)
except ModuleNotFoundError:
    A = importlib.import_module("actions.global_actions")

def teleport(portal):
    A.open_map()
    time.sleep(1)
    A.tap(*portal)
    time.sleep(1)
    A.confirm_teleport()
    time.sleep(3)

ACTION_TABLE = {
    "move": A.move,
    "climb": A.climb,
    "swim": A.swim,
    "run": A.run,
    "dash": A.dash,
    "attack": lambda: A.attack(),
    "heavy_attack": lambda: A.heavy_attack(),
    "jump": lambda: A.jump(),
    "util": lambda: A.util(),
    "long_util": lambda: A.long_util(),
    "glide": A.glide,
    "turn_180": lambda: A.turn_180(),
    "turn_right_90": lambda: A.turn_right_90(),
    "turn_left_90": lambda: A.turn_left_90(),
    "turn_right_45": lambda: A.turn_right_45(),
    "turn_left_45": lambda: A.turn_left_45(),
    "turn_right_30": lambda: A.turn_right_30(),
    "turn_left_30": lambda: A.turn_left_30(),
    "turn_right_135": lambda: A.turn_right_135(),
    "turn_left_135": lambda: A.turn_left_135(),
    "teleport": teleport,
    "sleep": A.sleep
}

if hasattr(A, "adjust_game_time"):
    ACTION_TABLE["adjust_game_time"] = lambda: A.adjust_game_time()

def run_route(route, portal, recorder):
    for step in route:
        name = step[0]
        args = step[1:] if len(step) > 1 else []

        print(f"[ACTION] {name}")

        if name == "record_start":
            time.sleep(1)
            recorder.start()

        elif name == "record_stop":
            recorder.stop()
            time.sleep(1)

        elif name == "teleport":
            A.open_map()
            time.sleep(1)
            A.tap(*portal)
            time.sleep(1)
            A.confirm_teleport()
            time.sleep(3)

        else:
            ACTION_TABLE[name](*args)

        time.sleep(0.4)
