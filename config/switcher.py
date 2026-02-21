import json
import time
from engine.executor import exec_action   # 你之前的 tap / swipe 封装

def apply_render_config(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for step in data["steps"]:
        exec_action(step)

    time.sleep(1)  # 确保配置生效