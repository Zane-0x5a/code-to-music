import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shutil
import sys
import tempfile
import uuid
from . import __version__
from .backend import run_backend
from .errors import MusicError, write_json
from .inspect import inspect_artifact
from .resources import catalog, check_assets, resolve_score
from .score import load_score
from .render import render, check_destination


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise MusicError("E_USAGE", message, "command line", "Run music --help or music <command> --help.")


def parser() -> Parser:
    root = Parser(prog="music", description="Headless score -> sampled piano + VST3 -> checked WAV/stems/MIDI/report. JSON contract v3.")
    root.add_argument("--version", action="version", version=__version__)
    commands = root.add_subparsers(dest="command", required=True)
    for command, description in [("doctor", "Verify assets, load each instrument and render a short offline probe."),
                                  ("instruments", "List configured licenses, capabilities, paths and recorded verification."),
                                  ("validate", "Validate score/schema/capabilities and asset hashes without loading native backends."),
                                  ("render", "Render in isolated native workers; fail on audio checks; never overwrite outputs."),
                                  ("inspect", "Summarize outcome and recorded instrument fingerprints, verify artifacts and recheck master audio; full report stays on disk.")]:
        child = commands.add_parser(command, help=description, description=description)
        child.add_argument("--json", action="store_true", help="Emit exactly one versioned JSON object to stdout.")
        child.add_argument("--config", type=Path, default=Path(os.environ.get("MUSIC_CONFIG", "music.config.json")), help="Config path (default MUSIC_CONFIG or cwd/music.config.json); asset paths relative to it.")
        if command in {"validate", "render"}:
            child.add_argument("score", type=Path, help="UTF-8 score JSON, version 1.")
        if command == "render":
            child.add_argument("--output", type=Path, default=Path("outputs/render"), help="Fresh output directory; existing directories fail E_OUTPUT_EXISTS.")
            child.add_argument("--dry-run", action="store_true", help="Resolve resources, hashes and output plan; do not render/create outputs.")
        if command == "inspect":
            child.add_argument("artifact", type=Path, help="report.json or render directory.")
    return root


def execute(args) -> dict:
    if args.command == "inspect":
        return inspect_artifact(args.artifact)
    instruments = catalog(args.config.resolve())
    if args.command == "instruments":
        result = []
        for instrument in instruments.values():
            try:
                check_assets(instrument)
                result.append({**instrument, "availability": "present_hash_verified"})
            except MusicError as exc:
                result.append({**instrument, "availability": "unavailable", "error": exc.as_dict()})
        return {"instruments": result}
    if args.command == "doctor":
        checks = []
        log_root = args.config.resolve().parent / ".music" / "doctor"
        log_root.mkdir(parents=True, exist_ok=True)
        for instrument in instruments.values():
            try:
                check_assets(instrument)
                directory = Path(tempfile.mkdtemp(prefix=instrument["id"] + "-", dir=log_root))
                events = [dict(frame=0, data=[0x90,60,96]), dict(frame=24000, data=[0x80,60,0]), dict(frame=24000, data=[0xB0,64,0])]
                audio, details = run_backend(instrument, events, 48000, 48000, directory, timeout=90)
                if float(abs(audio).max()) <= 0.00001:
                    raise MusicError("E_AUDIO_QA", "Offline doctor probe is silent.", instrument["id"], "Restore the instrument/profile and inspect the native log.")
                checks.append(dict(instrument=instrument["id"], passed=True, evidence=details))
            except MusicError as exc:
                checks.append(dict(instrument=instrument["id"], passed=False, error=exc.as_dict()))
        ffmpeg = shutil.which("ffmpeg")
        checks.append(dict(resource="ffmpeg", passed=bool(ffmpeg), path=ffmpeg,
                           fix=None if ffmpeg else "Install FFmpeg on PATH for LUFS and true peak."))
        writable = os.access(args.config.resolve().parent, os.W_OK)
        checks.append(dict(resource="config directory write permission", passed=writable))
        return dict(healthy=all(c["passed"] for c in checks), checks=checks, python=sys.version.split()[0], log_directory=str(log_root))
    score = load_score(args.score)
    selected = resolve_score(score, instruments)
    if args.command == "render":
        check_destination(args.output)
    if args.command == "validate" or args.dry_run:
        return dict(valid=True, native_backend_loaded=False, duration_seconds=score.frames/score.sample_rate,
                    sample_rate=score.sample_rate, frames=score.frames, instruments=selected,
                    output_plan=dict(directory=str(args.output.absolute()) if args.command == "render" else None, **score.output))
    report = render(score, args.score, args.config.resolve(), {i["id"]: i for i in selected}, args.output)
    return dict(report_path=str(args.output.absolute()/"report.json"), master_path=str(args.output.absolute()/"master.wav"),
                status=report["status"], audio=report["audio"], stem_sum=report["stem_sum"], warnings=report["warnings"])


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    command = next((word for word in argv if word in {"doctor", "instruments", "validate", "render", "inspect"}), None)
    json_mode = "--json" in argv
    try:
        args = parser().parse_args(argv)
        data = execute(args)
        ok = data.get("healthy", True)
        payload = dict(version=3, tool_version=__version__, command=args.command, ok=ok, data=data, error=None)
        exit_code = 0 if ok else 1
    except Exception as exc:
        error = exc if isinstance(exc, MusicError) else MusicError("E_INTERNAL", f"{type(exc).__name__}: {exc}", command or "music", "Inspect .music/logs and report this failure with the command/config.")
        payload = dict(version=3, tool_version=__version__, command=command, ok=False, data=error.data, error=error.as_dict())
        exit_code = 2
        try:
            log_dir = Path.cwd() / ".music" / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            write_json(log_dir / f"cli-{uuid.uuid4().hex}.json", {**payload, "timestamp_utc": datetime.now(timezone.utc).isoformat()})
        except OSError:
            pass
    if json_mode:
        print(json.dumps(payload, ensure_ascii=True, allow_nan=False))
    elif payload["ok"]:
        print(f"music {payload['command']}: OK")
        data = payload["data"]
        if command == "render":
            if data.get("report_path"):
                print(f"WAV: {data['master_path']}\nReport: {data['report_path']}")
            else:
                print(f"Dry run: {data['frames']} frames at {data['sample_rate']} Hz; native backend not loaded.")
        elif command == "doctor":
            for check in data["checks"]:
                print(f"  {'PASS' if check['passed'] else 'FAIL'}: {check.get('instrument',check.get('resource'))}")
            print(f"Evidence: {data['log_directory']}")
        elif command == "instruments":
            for instrument in data["instruments"]:
                print(f"  {instrument['id']}: {instrument['name']} {instrument['version']} | {instrument['license']} | {instrument['availability']}")
        elif command == "validate":
            print(f"Valid: {data['duration_seconds']:.3f}s, {data['sample_rate']} Hz; {len(data['instruments'])} instruments. Native backend not loaded.")
        elif command == "inspect":
            print(f"Status: {data['status']}; {data['artifacts']['checked']} artifact hashes checked. Listening verified: false.\nReport: {data['report_path']}")
        else:
            print(json.dumps(data, ensure_ascii=True, indent=2))
    else:
        if payload["error"]:
            error = payload["error"]
            print(f"{error['code']}: {error['message']}\nResource: {error['resource']}\nFix: {error['fix']}", file=sys.stderr)
        else:
            print(json.dumps(payload["data"], ensure_ascii=True, indent=2), file=sys.stderr)
    return exit_code
