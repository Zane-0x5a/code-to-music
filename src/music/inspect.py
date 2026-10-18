"""Inspect outcome first; return a bounded summary and keep the full report on disk."""
from importlib.resources import files
import json
from pathlib import Path
import wave
from jsonschema import Draft202012Validator
from .audio import measure
from .errors import MusicError, read_json, fingerprint


INSTRUMENT_SUMMARY_BYTES = 2048


def instrument_summary(instruments: list[dict]) -> dict:
    """Project recorded identity/hashes, never current asset paths or verification."""
    result = dict(source="render_report", current_assets_verified=False,
                  total=len(instruments), omitted=len(instruments), items=[])

    def fits():
        return len(json.dumps(result).encode("utf-8")) <= INSTRUMENT_SUMMARY_BYTES

    for instrument in instruments:
        item = dict(id=instrument["id"], version=instrument["version"], assets={},
                    assets_total=len(instrument["assets"]), assets_omitted=len(instrument["assets"]))
        result["items"].append(item)
        result["omitted"] -= 1
        if not fits():
            result["items"].pop()
            result["omitted"] += 1
            continue
        for name, asset in instrument["assets"].items():
            item["assets"][name] = asset["sha256"]
            item["assets_omitted"] -= 1
            if not fits():
                del item["assets"][name]
                item["assets_omitted"] += 1
    return result


def inspect_artifact(path: Path) -> dict:
    if path.is_dir():
        path = path / "report.json"
    path = path.resolve()
    result = dict(version=2, kind="music.inspect", status="invalid_report", report_path=str(path),
                  report_status=None, integrity_passed=None,
                  artifacts=dict(listed=0, checked=0, missing=0, changed=0),
                  issues=[], audio_recheck=None, render_error_code=None, listening_verified=False,
                  instruments=None)

    def fail(code: str, message: str, resource: str, fix: str, status: str):
        result["status"] = status
        raise MusicError(code, message, resource, fix, data=result)

    if not path.is_file():
        fail("E_ARTIFACT_MISSING", "Render report is missing.", str(path),
             "Locate the original report.json or render again to a fresh directory.", "artifact_missing")
    try:
        report = read_json(path)
    except MusicError as exc:
        fail("E_ARTIFACT", f"Cannot read render report: {exc.message}", str(path),
             "Restore the original UTF-8 report.json or render again.", "invalid_report")
    schema = read_json(Path(str(files("music").joinpath("schemas/report-v1.json"))))
    error = next(Draft202012Validator(schema).iter_errors(report), None)
    if error:
        fail("E_ARTIFACT", f"Invalid render report at {error.json_path}: {error.message[:300]}", str(path),
             "Use an unmodified music.render v1 report; restore it or render again.", "invalid_report")
    result["report_status"] = report["status"]
    result["artifacts"]["listed"] = len(report["artifacts"])
    result["instruments"] = instrument_summary(report["instruments"])
    if report["status"] == "failed":
        original = report["error"]
        result["render_error_code"] = original["code"]
        for item in report.get("qa_failures", [])[:8]:
            location = item.get("track_id") or item["scope"]
            result["issues"].append(f"{location}: {item['metric']}={item['actual']} "
                                    f"(required {item['comparison']} {item['threshold']})"[:300])
        fail("E_RENDER_FAILED", f"Render failed ({original['code']}): {original['message'][:300]}", str(path),
             f"Use data.issues for immediate QA diagnostics; full error and native evidence are in {path}. "
             "Repair the reported cause and render to a fresh directory.", "render_failed")
    if report["status"] != "passed":
        fail("E_RENDER_INCOMPLETE", "Render report has not reached a passed or failed outcome.", str(path),
             "Wait for the render to finish or inspect its failure evidence; do not use incomplete output.", "render_incomplete")

    root = path.parent
    listed = set()
    for artifact in report["artifacts"]:
        actual = (root / artifact["path"]).resolve()
        if not actual.is_relative_to(root) or artifact["path"] in listed:
            fail("E_ARTIFACT", "Artifact path escapes the report directory or is duplicated.", str(path),
                 "Restore the original report and artifacts.", "invalid_report")
        listed.add(artifact["path"])
    expected = {"master.wav"}
    if report["output"]["midi"]:
        expected.add("score.mid")
    if report["output"]["stems"]:
        for track in report["tracks"]:
            expected.add(f"stems/{track['id']}.wav")
            if report["output"]["midi"]:
                expected.add(f"stems/{track['id']}.mid")
    if not expected.issubset(listed):
        fail("E_ARTIFACT", "Passed report does not list all required output artifacts.", str(path),
             "Restore the original report or render again; an empty artifact list is not acceptance evidence.", "invalid_report")

    for artifact in report["artifacts"]:
        actual = root / artifact["path"]
        result["artifacts"]["checked"] += 1
        if not actual.is_file():
            result["artifacts"]["missing"] += 1
            problem = "missing"
        elif actual.stat().st_size != artifact["bytes"] or fingerprint(actual) != artifact["sha256"]:
            result["artifacts"]["changed"] += 1
            problem = "changed"
        else:
            continue
        if len(result["issues"]) < 8:
            result["issues"].append(f"{problem}: {artifact['path']}"[:300])
    result["integrity_passed"] = not (result["artifacts"]["missing"] or result["artifacts"]["changed"])
    if not result["integrity_passed"]:
        missing = result["artifacts"]["missing"] > 0
        fail("E_ARTIFACT_MISSING" if missing else "E_ARTIFACT_CHANGED", "Published artifacts are missing or differ from the report.", str(path),
             "Restore original artifacts or render again to a fresh directory; see summary issues and the full report.",
             "artifact_missing" if missing else "artifact_changed")
    try:
        result["audio_recheck"] = measure(root / "master.wav", report["audio"]["frames"],
                                          report["audio"]["sample_rate"])
    except (OSError, EOFError, ValueError, wave.Error) as exc:
        fail("E_ARTIFACT", f"Master WAV cannot be decoded: {exc}", str(root / "master.wav"),
             "Restore the original PCM24 stereo WAV or render again.", "artifact_invalid")
    except MusicError as exc:
        fail(exc.code, exc.message, exc.resource, exc.fix, "artifact_invalid" if exc.code == "E_ARTIFACT" else "audio_failed")
    if (not result["audio_recheck"]["passed"] or not report["audio"]["passed"]
            or not report["stem_sum"]["passed"] or any(not track["qa"]["passed"] for track in report["tracks"])):
        fail("E_AUDIO_QA", "Master recheck or recorded audio checks failed.", str(path),
             "Read audio_recheck and per-track metrics in report.json; correct gains/timing and render again.", "audio_failed")
    result["status"] = "passed"
    return result
