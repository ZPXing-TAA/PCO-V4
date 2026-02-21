import os
from config.switcher import apply_render_config
from engine.runner import run_route
from recording.recorder import Recorder

def run_one_config(
    json_path,
    route,
    portal,
    video_dir,
    video_name
):
    # 1. 切换配置
    print(f"[CONFIG] 应用配置 {json_path}")
    apply_render_config(json_path)

    # 2. 准备 Recorder（⚠️ 不启动）
    video_path = os.path.join(video_dir, f"{video_name}.mp4")
    recorder = Recorder(video_path)

    # 3. 执行动作（路线自己决定何时录）
    run_route(
        route=route,
        portal=portal,
        recorder=recorder
    )

    # 4. 兜底：防止忘记 stop
    recorder.stop()
    print("[PIPELINE] 配置执行完成\n")
