from pathlib import Path
from .audio import measure
from .errors import MusicError, read_json, fingerprint


def inspect_artifact(path: Path) -> dict:
    if path.is_dir():
        path = path / "report.json"
    report = read_json(path)
    if not isinstance(report, dict) or report.get("version") != 1 or report.get("kind") != "music.render":
        raise MusicError("E_ARTIFACT", "Unsupported render report kind/version.", str(path), "Use a music.render v1 report or output directory.")
    integrity = []
    root = path.parent.resolve()
    for artifact in report.get("artifacts", []):
        actual = (root / artifact["path"]).resolve()
        if not actual.is_relative_to(root):
            raise MusicError("E_ARTIFACT", "Artifact path escapes report directory.", str(actual), "Use an untampered report.")
        integrity.append(dict(path=artifact["path"], passed=actual.is_file() and fingerprint(actual) == artifact["sha256"]))
    result = dict(report=report, integrity=integrity, integrity_passed=all(x["passed"] for x in integrity))
    if report["status"] == "passed":
        frames = report["audio"]["frames"]
        audible = report["audio"]["sample_peak_dbfs"] is not None
        result["audio_recheck"] = measure(root / "master.wav", frames, report["audio"]["sample_rate"], audible)
    return result
