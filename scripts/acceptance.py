"""One real acceptance run with machine-readable evidence; no mocked instruments."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import time
from datetime import datetime
import numpy as np
import mido
from music.audio import read_wav
from music.backend import run_backend
from music.errors import MusicError, read_json, write_json, fingerprint
from music.resources import catalog
from jsonschema import Draft202012Validator
from importlib.resources import files

ROOT = Path(__file__).resolve().parents[1]


def main():
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    evidence = ROOT / "outputs" / f"acceptance-{stamp}"
    directory = evidence / "中文 路径"
    directory.mkdir(parents=True)
    summary = dict(version=1, status="running", python=sys.executable, evidence_directory=str(evidence), commands=[], checks=[])
    config = ROOT / "music.config.json"
    envelope_schema = read_json(Path(str(files("music").joinpath("schemas/cli-v1.json"))))
    report_schema = read_json(Path(str(files("music").joinpath("schemas/report-v1.json"))))
    source = read_json(ROOT / "examples/first-score.json")
    score_path = directory / "短 乐谱.json"
    write_json(score_path, source)

    def command(args, expected_code=None, config_path=config, success=True):
        argv = [sys.executable, "-m", "music", *args, "--config", str(config_path), "--json"]
        start = time.perf_counter()
        process = subprocess.run(argv, cwd=directory, capture_output=True, stdin=subprocess.DEVNULL, timeout=240)
        stdout = process.stdout.decode("utf-8", errors="strict")
        result = json.loads(stdout)
        Draft202012Validator(envelope_schema).validate(result)
        record = dict(argv=argv, exit_code=process.returncode, elapsed_seconds=round(time.perf_counter()-start,3), result=result,
                      stderr=process.stderr.decode("utf-8", errors="replace"))
        summary["commands"].append(record)
        write_json(evidence / "summary.json", summary)
        assert result["version"] == 1 and result["ok"] == success, record
        assert (process.returncode == 0) == success, record
        if expected_code:
            assert result["error"]["code"] == expected_code, record
            assert all(result["error"].get(key) for key in ("message", "resource", "fix")), record
        print(f"{args[0]}: {'OK' if success else expected_code} ({record['elapsed_seconds']}s)", flush=True)
        return result

    try:
        command(["doctor"])
        command(["instruments"])
        command(["validate", str(score_path)])
        dry = directory / "dry run"
        command(["render", str(score_path), "--dry-run", "--output", str(dry)])
        assert not dry.exists()
        output_a, output_b = directory / "render A", directory / "render B"
        command(["render", str(score_path), "--output", str(output_a)])
        command(["inspect", str(output_a)])
        Draft202012Validator(report_schema).validate(read_json(output_a/"report.json"))
        command(["render", str(score_path), "--output", str(output_b)])
        for name in ["master.wav", "stems/piano.wav", "stems/synth.wav", "score.mid"]:
            first, second = fingerprint(output_a/name), fingerprint(output_b/name)
            check = dict(name=f"repeatability:{name}", passed=first==second, byte_identical=first==second, first_sha256=first, second_sha256=second)
            summary["checks"].append(check)
            if name.endswith(".wav"):
                a, _ = read_wav(output_a/name)
                b, _ = read_wav(output_b/name)
                check["maximum_sample_difference"] = float(np.max(np.abs(a-b)))
                # Surge's measured numerical floor is below 4 PCM24 LSBs.
                # Keep piano/MIDI bit-exact; do not falsely claim synth hashes match.
                check["tolerance"] = 0 if name == "stems/piano.wav" else 4 / 8388608
                check["passed"] = check["maximum_sample_difference"] <= check["tolerance"]
            assert check["passed"], check
        midi = mido.MidiFile(output_a/"score.mid")
        note_ons = sum(msg.type == "note_on" and msg.velocity > 0 for track in midi.tracks for msg in track)
        expected_notes = sum(e["type"] == "note" for t in source["tracks"] for e in t["events"])
        assert note_ons == expected_notes, note_ons
        assert any(msg.type == "control_change" and msg.control == 64 for track in midi.tracks for msg in track)
        summary["checks"].append(dict(name="midi note count and sustain", passed=True, note_ons=note_ons))
        # Prove the score controls the output: one deliberate piano pitch edit.
        edited = copy.deepcopy(source)
        edited["tracks"][0]["events"][1]["pitch"] = "D4"
        changed_score = directory / "edited score.json"
        write_json(changed_score, edited)
        edited_output = directory / "edited render"
        command(["render", str(changed_score), "--output", str(edited_output)])
        assert fingerprint(edited_output/"stems/piano.wav") != fingerprint(output_a/"stems/piano.wav")
        synth_difference = float(np.max(np.abs(read_wav(edited_output/"stems/synth.wav")[0] - read_wav(output_a/"stems/synth.wav")[0])))
        assert synth_difference <= 4/8388608, synth_difference
        summary["checks"].append(dict(name="pitch edit changes piano, preserves synth within numerical tolerance", passed=True,
                                     synth_max_sample_difference=synth_difference, tolerance=4/8388608))
        master_before = fingerprint(output_a/"master.wav")
        command(["render", str(score_path), "--output", str(output_a)], "E_OUTPUT_EXISTS", success=False)
        assert fingerprint(output_a/"master.wav") == master_before
        invalid = copy.deepcopy(source)
        invalid["tracks"][0]["events"][1]["velocity"] = 200
        invalid_path = directory / "schema error.json"
        write_json(invalid_path, invalid)
        command(["validate", str(invalid_path)], "E_SCHEMA", success=False)
        missing = copy.deepcopy(source)
        missing["tracks"][0]["instrument"] = "not-installed"
        missing_path = directory / "missing resource.json"
        write_json(missing_path, missing)
        command(["validate", str(missing_path)], "E_RESOURCE_MISSING", success=False)
        unsupported = copy.deepcopy(source)
        unsupported["tracks"][0]["events"][0]["controller"] = 1
        unsupported_path = directory / "unsupported cc.json"
        write_json(unsupported_path, unsupported)
        command(["validate", str(unsupported_path)], "E_UNSUPPORTED", success=False)
        absolute_config = read_json(config)
        for instrument in absolute_config["instruments"].values():
            for asset in instrument["assets"].values():
                asset["path"] = str((ROOT/asset["path"]).resolve())
        absent_soundfont = copy.deepcopy(absolute_config)
        absent_soundfont["instruments"]["salamander-piano"]["assets"]["soundfont"]["path"] = str(directory/"absent.sf2")
        absent_config = directory/"absent sample config.json"
        write_json(absent_config, absent_soundfont)
        command(["validate", str(score_path)], "E_RESOURCE_MISSING", absent_config, success=False)
        broken = copy.deepcopy(absolute_config)
        invalid_dll = directory/"broken backend.dll"
        invalid_dll.write_bytes(b"not a native library")
        broken["instruments"]["salamander-piano"]["assets"]["library"] = dict(path=str(invalid_dll), sha256=fingerprint(invalid_dll))
        broken_config = directory/"broken config.json"
        write_json(broken_config, broken)
        command(["render", str(score_path), "--output", str(directory/"broken render")], "E_BACKEND_UNAVAILABLE", broken_config, success=False)
        assert not (directory/"broken render").exists()
        absent_backend = copy.deepcopy(absolute_config)
        absent_backend["instruments"]["surge-init"]["assets"]["plugin"]["path"] = str(directory/"missing.vst3")
        absent_backend_config = directory/"absent backend config.json"
        write_json(absent_backend_config, absent_backend)
        command(["validate", str(score_path)], "E_BACKEND_UNAVAILABLE", absent_backend_config, success=False)
        # Alternate sample rate, muted track, and disabled optional outputs.
        alternate = copy.deepcopy(source)
        alternate["output"].update(sample_rate=44100, stems=False, midi=False, intermediates=False)
        alternate["tracks"][1]["mute"] = True
        alternate_path = directory/"44100 muted.json"
        write_json(alternate_path, alternate)
        alternate_output = directory/"44100 render"
        command(["render", str(alternate_path), "--output", str(alternate_output)])
        assert not (alternate_output/"stems").exists() and not (alternate_output/"score.mid").exists()
        assert not (alternate_output/"intermediates").exists()
        alternate_report = read_json(alternate_output/"report.json")
        assert alternate_report["audio"]["sample_rate"] == 44100
        assert alternate_report["tracks"][1]["muted"] and "skipped" in alternate_report["tracks"][1]["backend"]
        summary["checks"].append(dict(name="44100, mute, disabled optional outputs", passed=True))
        # Real timeout: Windows venv launchers spawn a child interpreter. Prove
        # the whole native tree is gone, rather than just the launcher exiting.
        timeout_dir = evidence / "native-timeout"
        try:
            run_backend(catalog(config)["surge-init"], [], 48000, 48000, timeout_dir, timeout=.25)
            raise AssertionError("Native timeout did not trigger")
        except MusicError as exc:
            assert exc.code == "E_BACKEND_TIMEOUT", exc
        if os.name == "nt":
            literal = str(timeout_dir / "request.json").replace("'", "''")
            query = "$target = '" + literal + "'; @(Get-CimInstance Win32_Process | Where-Object { $_.Name -eq 'python.exe' -and $_.CommandLine -like ('*' + $target + '*') }).Count"
            process_count = subprocess.run(["powershell", "-NoProfile", "-Command", query], capture_output=True, check=True, timeout=20)
            assert int(process_count.stdout.decode().strip()) == 0, process_count.stdout
        summary["checks"].append(dict(name="native timeout terminates worker process tree", passed=True))
        # Exercise low/mid/high pitch, velocity endpoints and CC64 using the actual native adapters.
        for instrument in catalog(config).values():
            events = []
            segments = []
            index = 0
            for pitch in [21,60,108]:
                for velocity in [1,64,127]:
                    frame = index * 48000
                    events += [dict(frame=frame, data=[0x90,pitch,velocity]), dict(frame=frame+12000, data=[0x80,pitch,0])]
                    segments.append((pitch, velocity, frame))
                    index += 1
            audio, details = run_backend(instrument, events, 48000, index*48000, evidence/"capabilities"/instrument["id"])
            peaks = [dict(pitch=p, velocity=v, peak=float(np.max(np.abs(audio[:,frame:frame+12000])))) for p,v,frame in segments]
            assert all(x["peak"] > 1e-7 for x in peaks), peaks
            # MIDI delivery alone is insufficient: admitted velocity must
            # produce an audible amplitude response in each actual profile.
            for group in (peaks[0:3], peaks[3:6], peaks[6:9]):
                assert group[0]["peak"] < group[1]["peak"] < group[2]["peak"], group
            note_events = [dict(frame=0,data=[0x90,60,100]), dict(frame=12000,data=[0x80,60,0])]
            plain, _ = run_backend(instrument, note_events, 48000, 96000, evidence/"pedal"/instrument["id"]/"plain")
            pedal_events = [dict(frame=0,data=[0xB0,64,127]), *note_events, dict(frame=72000,data=[0xB0,64,0])]
            pedal, _ = run_backend(instrument, pedal_events, 48000, 96000, evidence/"pedal"/instrument["id"]/"pedal")
            off_rms = float(np.sqrt(np.mean(plain[:,48000:72000] ** 2)))
            held_rms = float(np.sqrt(np.mean(pedal[:,48000:72000] ** 2)))
            assert held_rms > max(off_rms*1.1,1e-7), (instrument["id"], off_rms, held_rms)
            summary["checks"].append(dict(name=f"capabilities:{instrument['id']}", passed=True, sampled_grid=peaks,
                                           velocity_response="Strictly increasing peak at velocities 1,64,127 for pitches 21,60,108",
                                           cc64=dict(note_off_rms=off_rms, held_rms=held_rms), backend=details))
        # Real native resource paths with both non-ASCII text and spaces.
        native_dir = directory / "本机 音源"
        native_dir.mkdir()
        piano_instrument = copy.deepcopy(catalog(config)["salamander-piano"])
        library = Path(piano_instrument["assets"]["library"]["path"])
        for dependency in library.parent.glob("*.dll"):
            os.link(dependency, native_dir/dependency.name)
        sf_path = native_dir / "真实 钢琴.sf2"
        os.link(piano_instrument["assets"]["soundfont"]["path"], sf_path)
        piano_instrument["assets"]["soundfont"]["path"] = str(sf_path)
        piano_instrument["assets"]["library"]["path"] = str(native_dir/library.name)
        audio, details = run_backend(piano_instrument, [dict(frame=0,data=[0x90,60,100]), dict(frame=24000,data=[0x80,60,0])],
                                     48000, 48000, evidence/"unicode-native")
        assert float(np.max(np.abs(audio))) > 1e-6
        summary["checks"].append(dict(name="non-ASCII/spaces in actual DLL and SF2 paths", passed=True, backend=details))
        summary["status"] = "passed"
    except Exception as exc:
        summary["status"] = "failed"
        summary["failure"] = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        write_json(evidence/"summary.json", summary)
        print(f"Evidence: {evidence/'summary.json'}", flush=True)


if __name__ == "__main__":
    main()
