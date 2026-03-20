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
    "walk": A.walk,
    "climb": A.climb,
    "swim": A.swim,
    "run": A.run,
    "dash": A.dash,
    "attack": lambda: A.attack(),
    "heavy_attack": lambda: A.heavy_attack(),
    "jump": lambda: A.jump(),
    "util": lambda: A.util(),
    "long_util": lambda: A.long_util(),
    "combat": lambda: A.combat(),
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
