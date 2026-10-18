from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
import os
import platform
import shutil
import subprocess
import tempfile
import uuid
import numpy as np
from . import __version__
from .audio import THRESHOLDS, STEM_THRESHOLDS, write_wav, read_wav, measure
from .backend import run_backend
from .errors import MusicError, write_json, fingerprint
from .midi import write_midi
from .score import Score, timeline


def check_destination(destination: Path) -> None:
    destination = destination.absolute()
    if destination.exists() or destination.is_symlink():
        raise MusicError("E_OUTPUT_EXISTS", "Output directory already exists; nothing was overwritten.", str(destination),
                         "Choose a fresh --output directory; inspect the existing report before removing old output.")


def relocate_evidence(report: dict, stage: Path, destination: Path) -> None:
    """Only retain references to evidence that survives publication/failure."""
    for track in report["tracks"]:
        backend = track["backend"]
        if not backend.get("command"):
            continue
        request = Path(backend["command"][-1])
        # A publication race may fail after references were mapped to output.
        origin = stage if request.is_relative_to(stage) else Path(report["output"]["directory"])
        request_relative = request.relative_to(origin)
        retained = (stage / request_relative).is_file()
        backend["intermediates_retained"] = retained
        backend["command"] = [*backend["command"][:-1], str(destination / request_relative)] if retained else None
        log_relative = Path(backend["log"]).relative_to(origin)
        backend["log"] = str(destination / log_relative) if (stage / log_relative).is_file() else None


def qa_failures(report: dict) -> list[dict]:
    failures = []
    for track in report["tracks"]:
        failures.extend(dict(scope="stem", track_id=track["id"], **item)
                        for item in track["qa"].get("diagnostics", []))
    if "audio" in report:
        failures.extend(dict(scope="master", track_id=None, **item)
                        for item in report["audio"].get("diagnostics", []))
    if "stem_sum" in report and not report["stem_sum"]["passed"]:
        failures.append(dict(scope="mix", track_id=None, metric="stem_sum_residual",
                             actual=report["stem_sum"]["max_absolute_residual"], comparison="at_most",
                             threshold=report["stem_sum"]["tolerance"]))
    return failures


def render(score: Score, score_path: Path, config_path: Path, instruments: dict, destination: Path) -> dict:
    destination = destination.absolute()
    check_destination(destination)
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=".music-stage-", dir=destination.parent))
    except OSError as exc:
        raise MusicError("E_OUTPUT_PERMISSION", str(exc), str(destination), "Choose a writable --output directory.") from exc
    report = dict(version=1, kind="music.render", status="rendering", tool_version=__version__,
                  timestamp_utc=datetime.now(timezone.utc).isoformat(),
                  score=dict(path=str(score_path.resolve()), sha256=fingerprint(score_path), content=score.data),
                  config=dict(path=str(config_path.resolve()), sha256=fingerprint(config_path)),
                  runtime=dict(python=platform.python_version(), platform=platform.platform(),
                               dependencies={name: version(name) for name in ("numpy", "mido", "jsonschema", "pedalboard")}),
                  instruments=list(instruments.values()), output=dict(directory=str(destination), **score.output),
                  thresholds=THRESHOLDS, stem_thresholds=STEM_THRESHOLDS,
                  tracks=[], artifacts=[], warnings=[], listening_verified=False)
    try:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise MusicError("E_BACKEND_UNAVAILABLE", "Missing FFmpeg for audio acceptance.", "ffmpeg", "Install FFmpeg on PATH.")
        report["runtime"]["ffmpeg"] = subprocess.run([ffmpeg, "-version"], capture_output=True, timeout=15).stdout.decode(errors="replace").splitlines()[0]
        mix = np.zeros((2, score.frames), dtype=np.float64)
        stems = []
        for track in score.data["tracks"]:
            tid = track["id"]
            instrument = instruments[track["instrument"]]
            active = not track.get("mute", False)
            audible = active and any(e["type"] == "note" for e in track["events"])
            events = timeline(score, track)
            if audible:
                audio, backend = run_backend(instrument, events, score.sample_rate, score.frames, stage / "intermediates" / tid)
            else:
                audio, backend = np.zeros((2, score.frames), dtype=np.float32), {"skipped": "muted or no notes"}
            gain = 10 ** ((track.get("gain_db", 0) + score.output["master_gain_db"]) / 20)
            contribution = audio.astype(np.float64) * gain
            mix += contribution
            wav_path = stage / "stems" / f"{tid}.wav"
            wav_path.parent.mkdir(exist_ok=True)
            write_wav(wav_path, contribution, score.sample_rate)
            qa = measure(wav_path, score.frames, score.sample_rate, audible=audible, role="stem")
            stems.append(wav_path)
            report["tracks"].append(dict(id=tid, instrument=instrument["id"], muted=not active, gain_linear=gain, backend=backend, qa=qa))
            if score.output["midi"]:
                write_midi(wav_path.with_suffix(".mid"), score, [track], instruments)
        master_path = stage / "master.wav"
        write_wav(master_path, mix, score.sample_rate)
        # Only individual stems may be intentionally silent; the whole work must pass non-silence QA.
        report["audio"] = measure(master_path, score.frames, score.sample_rate)
        decoded, _ = read_wav(master_path)
        decoded_sum = np.zeros_like(decoded)
        for stem in stems:
            decoded_sum += read_wav(stem)[0]
        residual = float(np.max(np.abs(decoded_sum - decoded)))
        tolerance = (len(stems) + 1) / 8388608
        report["stem_sum"] = dict(max_absolute_residual=residual, tolerance=tolerance, passed=residual <= tolerance,
                                  relation="Post-track-gain and post-master-gain stems sum to master; PCM24 rounding only.")
        if score.output["midi"]:
            write_midi(stage / "score.mid", score, score.data["tracks"], instruments)
        if not report["audio"]["passed"] or not report["stem_sum"]["passed"] or any(not t["qa"]["passed"] for t in report["tracks"]):
            failures = qa_failures(report)
            report["qa_failures"] = failures
            first = failures[0]
            location = first["track_id"] or first["scope"]
            raise MusicError("E_AUDIO_QA", f"Audio checks failed: {location} {first['metric']}={first['actual']} "
                             f"(required {first['comparison']} {first['threshold']}); {len(failures)} failure(s).",
                             location, "Correct the named metric and render to a fresh output directory.",
                             data=dict(status="failed", qa_failures=failures))
        if report["audio"]["final_50ms_peak_dbfs"] is not None and report["audio"]["final_50ms_peak_dbfs"] > -60:
            report["warnings"].append("Tail still audible at end; increase output.tail_seconds to preserve full decay.")
        if not score.output["stems"]:
            shutil.rmtree(stage / "stems")
        if not score.output["intermediates"]:
            shutil.rmtree(stage / "intermediates", ignore_errors=True)
        # Keep references meaningful after the atomic rename.
        relocate_evidence(report, stage, destination)
        for path in sorted(stage.rglob("*")):
            if path.is_file():
                report["artifacts"].append(dict(path=path.relative_to(stage).as_posix(), sha256=fingerprint(path), bytes=path.stat().st_size))
        report["status"] = "passed"
        write_json(stage / "report.json", report)
        # Windows rename refuses an existing destination, including a concurrent render.
        try:
            os.rename(stage, destination)
        except FileExistsError as exc:
            raise MusicError("E_OUTPUT_EXISTS", "Another render created the output directory.", str(destination), "Choose a fresh --output directory.") from exc
        return report
    except BaseException as exc:
        report["status"] = "failed"
        report["error"] = exc.as_dict() if isinstance(exc, MusicError) else dict(code="E_RENDER", message=str(exc))
        failed = config_path.parent / ".music" / "logs" / uuid.uuid4().hex
        failed.parent.mkdir(parents=True, exist_ok=True)
        relocate_evidence(report, stage, failed)
        write_json(stage / "report.json", report)
        shutil.move(str(stage), failed)
        if isinstance(exc, MusicError):
            if exc.data is not None:
                exc.data["report_path"] = str(failed / "report.json")
            exc.fix += f" Failure evidence: {failed / 'report.json'}"
        raise
