import os
from routes.natlan_hybrid_1 import ROUTE,PORTAL

from recording.recorder import Recorder
from tools.debug_run_route import debug_run_route

PROJECT_ROOT = os.environ.get(
    "AUTO_PROJECT_ROOT",
    os.path.expanduser("~/CODEZONE/PCO/Power-Optimization"),
)
VIDEO_DIR = os.environ.get("AUTO_DEBUG_VIDEO_DIR", r"D:/recordings/debug")
VIDEO_NAME = "test"

os.makedirs(VIDEO_DIR, exist_ok=True)
video_path = os.path.join(VIDEO_DIR, f"{VIDEO_NAME}.mp4")
recorder = Recorder(video_path)

try:
    debug_run_route(ROUTE, portal=PORTAL, recorder=recorder)
finally:
    recorder.stop()
  
