from .global_actions import bind_actions

# 1) Create mapping/mydevice.py with WIDTH/HEIGHT.
# 2) Set MAPPING_MODULE to that file.
# 3) Fill OFFSETS only for actions/points needing fine tuning.
MAPPING_MODULE = "mapping.mydevice"
OFFSETS = {
    # "GLOBAL": (0, 0),
    # "MOVE": (0, 0),
    # "ATTACK": (0, 0),
    # "TURN": (0, 0),
    # "MOVE_START": (0, 0),
    # "TURN_180_R": (0, 0),
}

bind_actions(globals(), mapping_module=MAPPING_MODULE, offsets=OFFSETS)
