import os
import time

def exec_action(step):
    t = step["type"]

    if t == "tap":
        x, y = step["x"], step["y"]
        os.system(f"adb shell input tap {x} {y}")

    elif t == "swipe":
        x1, y1 = step["start"]
        x2, y2 = step["end"]
        d = step["duration"]
        os.system(f"adb shell input swipe {x1} {y1} {x2} {y2} {d}")

    elif t == "sleep":
        time.sleep(step["time"])

    elif t == "info":
        # 关键：info 只是日志，不是动作
        msg = step.get("message", "")
        print(f"[INFO] {msg}")

    else:
        raise ValueError(f"未知 action 类型: {t}")
