from .global_actions import bind_actions

MAPPING_MODULE = "mapping.huaweipura"
OFFSETS = {}

bind_actions(globals(), mapping_module=MAPPING_MODULE, offsets=OFFSETS)
