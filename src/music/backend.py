from pathlib import Path
import os
import subprocess
import sys
import numpy as np
from .errors import MusicError, read_json, write_json


def run_backend(instrument: dict, events: list, sample_rate: int, frames: int, directory: Path, timeout: float = 120) -> tuple[np.ndarray, dict]:
    directory.mkdir(parents=True, exist_ok=True)
    request_path = directory / "request.json"
    result_path = directory / "result.json"
    audio_path = directory / "audio.npy"
    write_json(request_path, dict(version=1, instrument=instrument, events=events, sample_rate=sample_rate,
                                  frames=frames, result_path=str(result_path), audio_path=str(audio_path)))
    log_path = directory / "native.log"
    command = [sys.executable, "-m", "music.worker", str(request_path)]
    try:
        with log_path.open("wb") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       stdin=subprocess.DEVNULL)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                # Windows venv Python is a launcher with a child interpreter.
                # Kill while the parent still exists so taskkill can find both.
                if os.name == "nt":
                    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                   stdout=log, stderr=subprocess.STDOUT, timeout=15)
                else:
                    process.kill()
                process.wait(timeout=15)
                raise
    except subprocess.TimeoutExpired as exc:
        raise MusicError("E_BACKEND_TIMEOUT", f"Native worker exceeded {timeout} seconds.", instrument["id"],
                         f"Inspect {log_path}; shorten the score or repair this instrument.") from exc
    result = read_json(result_path) if result_path.exists() else {"ok": False, "reason": f"Native worker exited {process.returncode}; see {log_path}"}
    if process.returncode or not result["ok"]:
        raise MusicError("E_BACKEND_UNAVAILABLE", result.get("reason", "Native worker failed."), instrument["id"],
                         f"Inspect {log_path}; reinstall the pinned backend and its dependencies.")
    return np.load(audio_path, allow_pickle=False), {**result, "command": command, "log": str(log_path)}
