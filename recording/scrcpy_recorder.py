import os
import signal
import subprocess
import time

SCRCPY_BIN = os.environ.get("SCRCPY_BIN", r"D:/Softwares/scrcpy-win64-v3.3.3/scrcpy.exe")
SCRCPY_MAX_FPS = os.environ.get("SCRCPY_MAX_FPS", "60")
SCRCPY_STARTUP_WAIT = float(os.environ.get("SCRCPY_STARTUP_WAIT", "1.0"))


def start_record(video_path):
    os.makedirs(os.path.dirname(video_path) or ".", exist_ok=True)
    cmd = [
        SCRCPY_BIN,
        "--record",
        video_path,
        "--no-playback",
        "--max-fps",
        str(SCRCPY_MAX_FPS),
        "--no-audio",
        "--no-window",
    ]
    kwargs = {}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["preexec_fn"] = os.setsid
    proc = subprocess.Popen(cmd, **kwargs)
    time.sleep(SCRCPY_STARTUP_WAIT)
    return proc


def stop_record(proc):
    if proc.poll() is not None:
        return

    try:
        if os.name == "nt":
            proc.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(proc.pid, signal.SIGINT)
    except OSError:
        proc.terminate()

    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
