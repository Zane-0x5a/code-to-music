"""One real acceptance run with machine-readable evidence; no mocked instruments."""
from pathlib import Path
import copy
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime
import numpy as np
import mido
from music import __version__
from music.audio import read_wav, write_wav, measure
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
    envelope_schema = read_json(Path(str(files("music").joinpath("schemas/cli-v3.json"))))
    legacy_schema = read_json(Path(str(files("music").joinpath("schemas/cli-v2.json"))))
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
        assert result["version"] == 3 and result["tool_version"] == __version__ and result["ok"] == success, record
        assert process.returncode == (0 if success else 2), record
        if expected_code:
            assert result["error"]["code"] == expected_code, record
            assert all(result["error"].get(key) for key in ("message", "resource", "fix")), record
        print(f"{args[0]}: {'OK' if success else expected_code} ({record['elapsed_seconds']}s)", flush=True)
        return result

    def check_instruments(inspection, report):
        snapshot = inspection["instruments"]
        assert snapshot["source"] == "render_report" and snapshot["current_assets_verified"] is False
        assert snapshot["total"] == len(report["instruments"]) and snapshot["omitted"] == 0
        expected = [dict(id=i["id"], version=i["version"],
                         assets={name: asset["sha256"] for name, asset in i["assets"].items()},
                         assets_total=len(i["assets"]), assets_omitted=0) for i in report["instruments"]]
        assert snapshot["items"] == expected
        assert len(json.dumps(snapshot).encode("utf-8")) <= 2048

    try:
        from music.backends.juce_state import encode_memory_block, decode_memory_block, component_state, wrap_component
        for size in (0, 1, 2, 3, 255, 1024):
            block = bytes((n * 37) % 256 for n in range(size))
            assert decode_memory_block(encode_memory_block(block)) == block
            assert component_state(wrap_component(block)) == block
        for damaged_state in (b"bad", b"VC2!\xff\xff\xff\xff", wrap_component(b"valid")[:12]):
            try:
                component_state(damaged_state)
            except Exception:
                pass
            else:
                raise AssertionError("Damaged state accepted")
        summary["checks"].append(dict(name="JUCE binary state round trips and corrupt-container rejection", passed=True))
        historical_inspect = read_json(ROOT/"scripts/fixtures/inspect-cli-v2.json")
        Draft202012Validator(legacy_schema).validate(historical_inspect)
        assert not Draft202012Validator(envelope_schema).is_valid(historical_inspect)
        summary["checks"].append(dict(name="unchanged CLI v2 schema validates captured 0.2.0 inspection; CLI v3 stays distinct", passed=True))
        missing_config = command(["doctor"], "E_CONFIG", directory/"missing config.json", success=False)
        assert "scripts/install_resources.py" in missing_config["error"]["fix"]
        assert "--config" in missing_config["error"]["fix"] and "MUSIC_CONFIG" in missing_config["error"]["fix"]
        missing_score = command(["validate", str(directory/"missing score.json")], "E_INPUT", success=False)
        assert missing_score["error"]["fix"] == "Create readable UTF-8 JSON with unique keys."
        summary["checks"].append(dict(name="missing config has setup guidance; missing score retains input semantics", passed=True))
        command(["doctor"])
        command(["instruments"])
        command(["validate", str(score_path)])
        dry = directory / "dry run"
        command(["render", str(score_path), "--dry-run", "--output", str(dry)])
        assert not dry.exists()
        output_a, output_b = directory / "render A", directory / "render B"
        command(["render", str(score_path), "--output", str(output_a)])
        # Inspect must use this render's snapshot, without consulting current config/assets.
        inspected = command(["inspect", str(output_a)], config_path=directory/"missing config.json")
        inspection = inspected["data"]
        assert inspection["version"] == 2
        mislabeled = copy.deepcopy(inspected)
        mislabeled["version"], mislabeled["data"]["version"] = 2, 1
        assert not Draft202012Validator(legacy_schema).is_valid(mislabeled)
        summary["checks"].append(dict(name="instrument summary uses CLI v3 / inspect v2; legacy strict contract rejects mislabeled shape", passed=True))
        assert inspection["status"] == "passed" and inspection["report_status"] == "passed"
        assert inspection["integrity_passed"] and inspection["audio_recheck"]["passed"]
        assert inspection["report_path"] == str(output_a/"report.json")
        assert "report" not in inspection and "score" not in inspection
        check_instruments(inspection, read_json(output_a/"report.json"))
        assert len(json.dumps(inspected).encode("utf-8")) < 4096
        summary["checks"].append(dict(name="inspect gives bounded passing summary and full-report pointer", passed=True))
        summary["checks"].append(dict(name="inspect includes selected instrument IDs, versions and every asset SHA-256 without current config", passed=True))
        Draft202012Validator(report_schema).validate(read_json(output_a/"report.json"))
        quiet = copy.deepcopy(source)
        quiet["tracks"][1]["instrument"] = "salamander-piano"
        quiet["tracks"][1]["gain_db"] = -15
        quiet["output"]["intermediates"] = False
        quiet_path = directory / "quiet accompaniment.json"
        write_json(quiet_path, quiet)
        quiet_output = directory / "quiet accompaniment render"
        command(["render", str(quiet_path), "--output", str(quiet_output)])
        quiet_report = read_json(quiet_output/"report.json")
        assert quiet_report["tracks"][1]["qa"]["passed"]
        assert quiet_report["tracks"][1]["qa"]["integrated_lufs"] < -45
        assert quiet_report["audio"]["passed"]
        summary["checks"].append(dict(name="quiet but audible stem does not inherit master loudness floor", passed=True,
                                     stem_lufs=quiet_report["tracks"][1]["qa"]["integrated_lufs"]))
        too_quiet = copy.deepcopy(quiet)
        too_quiet["output"]["master_gain_db"] = -50
        too_quiet_path = directory / "quiet master.json"
        write_json(too_quiet_path, too_quiet)
        failed_qa = command(["render", str(too_quiet_path), "--output", str(directory/"quiet master render")],
                            "E_AUDIO_QA", success=False)
        diagnostics = failed_qa["data"]["qa_failures"]
        assert diagnostics and any(item["scope"] == "master" and item["metric"] == "integrated_lufs" for item in diagnostics)
        qa_report = Path(failed_qa["data"]["report_path"])
        assert qa_report.is_file() and read_json(qa_report)["qa_failures"] == diagnostics
        failed_qa_inspect = command(["inspect", str(qa_report)], "E_RENDER_FAILED", success=False)
        assert any("integrated_lufs" in item for item in failed_qa_inspect["data"]["issues"])
        summary["checks"].append(dict(name="failed master names metric, actual, threshold and report in one response", passed=True))
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
        command(["render", str(score_path), "--dry-run", "--output", str(output_a)], "E_OUTPUT_EXISTS", success=False)
        command(["render", str(score_path), "--output", str(output_a)], "E_OUTPUT_EXISTS", success=False)
        assert fingerprint(output_a/"master.wav") == master_before
        summary["checks"].append(dict(name="dry-run and render both reject existing output without changes", passed=True))
        tiny = copy.deepcopy(source)
        tiny.update(tempo=300, length_beats=1e-10)
        tiny["output"]["tail_seconds"] = 0
        for track in tiny["tracks"]:
            track["events"] = []
        tiny_path = directory/"zero frames.json"
        write_json(tiny_path, tiny)
        command(["validate", str(tiny_path)], "E_SCORE", success=False)
        command(["render", str(tiny_path), "--dry-run"], "E_SCORE", success=False)
        tiny_output = directory/"zero frames render"
        command(["render", str(tiny_path), "--output", str(tiny_output)], "E_SCORE", success=False)
        assert not tiny_output.exists()
        summary["checks"].append(dict(name="zero-frame score rejected before native load or output creation", passed=True))
        for case in ["empty events", "all muted"]:
            silent = copy.deepcopy(source)
            for track in silent["tracks"]:
                if case == "empty events":
                    track["events"] = []
                else:
                    track["mute"] = True
            silent_path = directory/f"{case}.json"
            write_json(silent_path, silent)
            silent_output = directory/f"{case} render"
            command(["validate", str(silent_path)], "E_SCORE", success=False)
            command(["render", str(silent_path), "--dry-run", "--output", str(silent_output)], "E_SCORE", success=False)
            rejected = command(["render", str(silent_path), "--output", str(silent_output)], "E_SCORE", success=False)
            assert "unmuted" in rejected["error"]["fix"] and not silent_output.exists()
            summary["checks"].append(dict(name=f"{case}: whole silent work rejected before output creation", passed=True))
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
        failed_render = command(["render", str(score_path), "--output", str(directory/"broken render")], "E_BACKEND_UNAVAILABLE", broken_config, success=False)
        assert not (directory/"broken render").exists()
        failure_report = Path(failed_render["error"]["fix"].split("Failure evidence: ", 1)[1])
        failed_inspect = command(["inspect", str(failure_report)], "E_RENDER_FAILED", success=False)
        assert failed_inspect["data"]["status"] == "render_failed"
        assert failed_inspect["data"]["report_status"] == "failed"
        assert failed_inspect["data"]["integrity_passed"] is None
        assert failed_inspect["data"]["audio_recheck"] is None
        check_instruments(failed_inspect["data"], read_json(failure_report))
        summary["checks"].append(dict(name="inspect rejects real failed render with empty artifacts", passed=True, report_path=str(failure_report)))
        summary["checks"].append(dict(name="failed render retains recorded selection without claiming asset verification", passed=True))
        # Mutate a copy of a real passing render; leave original evidence intact.
        damaged = directory/"damaged artifact"
        shutil.copytree(output_a, damaged)
        original_master = (damaged/"master.wav").read_bytes()
        # A historical/modified passed report must not exempt a silent master from QA.
        silent_audio = np.zeros((2, read_json(damaged/"report.json")["audio"]["frames"]))
        write_wav(damaged/"master.wav", silent_audio, 48000)
        silent_report = read_json(damaged/"report.json")
        silent_report["audio"] = measure(damaged/"master.wav", silent_audio.shape[1], 48000, audible=False)
        for artifact in silent_report["artifacts"]:
            if artifact["path"] == "master.wav":
                artifact.update(sha256=fingerprint(damaged/"master.wav"), bytes=(damaged/"master.wav").stat().st_size)
        write_json(damaged/"report.json", silent_report)
        silent_inspect = command(["inspect", str(damaged)], "E_AUDIO_QA", success=False)
        assert silent_inspect["data"]["integrity_passed"] and not silent_inspect["data"]["audio_recheck"]["passed"]
        summary["checks"].append(dict(name="silent master cannot pass inspect even with matching hash and saved passing QA", passed=True))
        (damaged/"master.wav").write_bytes(original_master)
        write_json(damaged/"report.json", read_json(output_a/"report.json"))

        oversized = read_json(damaged/"report.json")
        oversized["instruments"][0]["version"] = "large version " * 500
        oversized["instruments"][1]["assets"]["large asset " * 500] = copy.deepcopy(oversized["instruments"][1]["assets"]["plugin"])
        write_json(damaged/"report.json", oversized)
        bounded = command(["inspect", str(damaged)])
        snapshot = bounded["data"]["instruments"]
        assert len(json.dumps(snapshot).encode("utf-8")) <= 2048 and snapshot["total"] == 2
        assert snapshot["omitted"] == 1 and len(snapshot["items"]) == 1
        assert snapshot["items"][0]["assets_omitted"] == 1
        assert snapshot["items"][0]["assets_total"] == 4
        assert len(json.dumps(bounded).encode("utf-8")) < 4096
        summary["checks"].append(dict(name="oversized recorded metadata has bounded projection and explicit omission counts", passed=True))
        oversized["instruments"][0]["assets"]["library"]["sha256"] = "invalid hash"
        write_json(damaged/"report.json", oversized)
        malformed = command(["inspect", str(damaged)], "E_ARTIFACT", success=False)
        assert malformed["data"]["instruments"] is None
        summary["checks"].append(dict(name="invalid instrument metadata is unknown, not a verified or empty selection", passed=True))
        write_json(damaged/"report.json", read_json(output_a/"report.json"))
        (damaged/"master.wav").unlink()
        missing_inspect = command(["inspect", str(damaged)], "E_ARTIFACT_MISSING", success=False)
        assert missing_inspect["data"]["status"] == "artifact_missing" and not missing_inspect["data"]["integrity_passed"]
        (damaged/"master.wav").write_bytes(b"broken WAV")
        changed_inspect = command(["inspect", str(damaged)], "E_ARTIFACT_CHANGED", success=False)
        assert changed_inspect["data"]["status"] == "artifact_changed" and not changed_inspect["data"]["integrity_passed"]
        damaged_report = read_json(damaged/"report.json")
        for artifact in damaged_report["artifacts"]:
            if artifact["path"] == "master.wav":
                artifact.update(sha256=fingerprint(damaged/"master.wav"), bytes=(damaged/"master.wav").stat().st_size)
        write_json(damaged/"report.json", damaged_report)
        invalid_audio = command(["inspect", str(damaged)], "E_ARTIFACT", success=False)
        assert invalid_audio["data"]["status"] == "artifact_invalid" and invalid_audio["data"]["integrity_passed"]
        summary["checks"].append(dict(name="matching artifact hash does not bypass WAV decoding", passed=True))
        (damaged/"master.wav").write_bytes(original_master)
        damaged_report = read_json(output_a/"report.json")
        damaged_report["status"] = "rendering"
        write_json(damaged/"report.json", damaged_report)
        incomplete = command(["inspect", str(damaged)], "E_RENDER_INCOMPLETE", success=False)
        assert incomplete["data"]["status"] == "render_incomplete" and incomplete["data"]["integrity_passed"] is None
        check_instruments(incomplete["data"], damaged_report)
        summary["checks"].append(dict(name="inspect rejects incomplete render without asserting integrity", passed=True))
        summary["checks"].append(dict(name="incomplete render exposes only recorded instrument selection", passed=True))
        damaged_report["status"] = "passed"
        damaged_report["artifacts"] = []
        write_json(damaged/"report.json", damaged_report)
        command(["inspect", str(damaged)], "E_ARTIFACT", success=False)
        (damaged/"report.json").write_text("{invalid", encoding="utf-8")
        command(["inspect", str(damaged)], "E_ARTIFACT", success=False)
        (damaged/"report.json").unlink()
        absent_report = command(["inspect", str(damaged)], "E_ARTIFACT_MISSING", success=False)
        assert absent_report["data"]["report_status"] is None and absent_report["data"]["integrity_passed"] is None
        assert absent_report["data"]["instruments"] is None
        shutil.rmtree(damaged)
        summary["checks"].append(dict(name="inspect distinguishes missing, changed and invalid reports without false success", passed=True))
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
        assert alternate_report["tracks"][0]["backend"]["command"] is None
        assert alternate_report["tracks"][0]["backend"]["log"] is None
        assert alternate_report["tracks"][0]["backend"]["intermediates_retained"] is False
        command(["inspect", str(alternate_output)])
        summary["checks"].append(dict(name="44100, mute, disabled optional outputs", passed=True))
        for track in read_json(output_a/"report.json")["tracks"]:
            assert track["backend"]["intermediates_retained"] is True
            assert Path(track["backend"]["command"][-1]).is_file()
            assert Path(track["backend"]["log"]).is_file()
        summary["checks"].append(dict(name="backend evidence paths exist only when intermediates retained", passed=True))
        single_empty = copy.deepcopy(source)
        single_empty["tracks"][1]["events"] = []
        single_empty_path = directory/"one empty track.json"
        write_json(single_empty_path, single_empty)
        single_empty_output = directory/"one empty track render"
        command(["render", str(single_empty_path), "--output", str(single_empty_output)])
        command(["inspect", str(single_empty_output)])
        single_empty_report = read_json(single_empty_output/"report.json")
        assert single_empty_report["tracks"][1]["backend"]["skipped"] == "muted or no notes"
        assert single_empty_report["tracks"][1]["qa"]["passed"] and single_empty_report["audio"]["passed"]
        summary["checks"].append(dict(name="one empty track remains legal when the whole work is audible", passed=True))
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
        # Exercise each instrument within its declared range using the actual native adapter.
        def isolated_peaks(instrument, pitches, rate):
            peaks = []
            for pitch in pitches:
                for velocity in (1, 64, 127):
                    events = [dict(frame=0, data=[0x90, pitch, velocity]),
                              dict(frame=round(rate*.25), data=[0x80, pitch, 0])]
                    audio, _ = run_backend(instrument, events, rate, rate,
                        evidence/"isolated-velocity"/instrument["id"]/str(rate)/f"{pitch}-{velocity}")
                    peaks.append(dict(pitch=pitch, velocity=velocity,
                                      peak=float(np.max(np.abs(audio[:, :round(rate*.25)])))))
            return peaks

        for instrument in catalog(config).values():
            is_drum = instrument["id"].startswith("avl-")
            is_sfz = instrument["backend"] == "sfz"
            low, high = instrument["capabilities"]["pitch_range"]
            pitches = [36, 38, 42] if is_drum else [low, instrument.get("probe_note", 60), high]
            events = []
            segments = []
            index = 0
            for pitch in pitches:
                for velocity in [1,64,127]:
                    frame = index * 48000
                    events += [dict(frame=frame, data=[0x90,pitch,velocity]), dict(frame=frame+12000, data=[0x80,pitch,0])]
                    segments.append((pitch, velocity, frame))
                    index += 1
            audio, details = run_backend(instrument, events, 48000, index*48000, evidence/"capabilities"/instrument["id"])
            peaks = [dict(pitch=p, velocity=v, peak=float(np.max(np.abs(audio[:,frame:frame+12000])))) for p,v,frame in segments]
            if "factory" in instrument["assets"]:
                peaks = isolated_peaks(instrument, pitches, 48000)
            assert all(x["peak"] > 1e-7 for x in peaks), peaks
            for group in (peaks[0:3], peaks[3:6], peaks[6:9]):
                if is_drum:
                    assert group[0]["peak"] != group[2]["peak"], group
                else:
                    assert group[0]["peak"] < group[1]["peak"] < group[2]["peak"], group
            result = dict(name=f"capabilities:{instrument['id']}", passed=True, sampled_grid=peaks,
                          velocity_response="Distinct endpoint peaks for sampled drum notes" if is_drum else
                          f"Strictly increasing peak at velocities 1,64,127 for pitches {pitches}", backend=details)
            if 64 in instrument["capabilities"]["controllers"]:
                note_events = [dict(frame=0,data=[0x90,60,100]), dict(frame=12000,data=[0x80,60,0])]
                plain, _ = run_backend(instrument, note_events, 48000, 96000, evidence/"pedal"/instrument["id"]/"plain")
                pedal_events = [dict(frame=0,data=[0xB0,64,127]), *note_events, dict(frame=72000,data=[0xB0,64,0])]
                pedal, _ = run_backend(instrument, pedal_events, 48000, 96000, evidence/"pedal"/instrument["id"]/"pedal")
                off_rms = float(np.sqrt(np.mean(plain[:,48000:72000] ** 2)))
                held_rms = float(np.sqrt(np.mean(pedal[:,48000:72000] ** 2)))
                assert held_rms > max(off_rms*1.1,1e-7), (instrument["id"], off_rms, held_rms)
                result["cc64"] = dict(note_off_rms=off_rms, held_rms=held_rms)
            summary["checks"].append(result)
            if "factory" in instrument["assets"]:
                for rate in (48000, 44100):
                    scaled_events = [dict(frame=round(e["frame"] * rate / 48000), data=e["data"]) for e in events]
                    reference, _ = run_backend(instrument, scaled_events, rate, index*rate,
                                              evidence/"factory-repeat"/instrument["id"]/str(rate)/"A")
                    repeated, _ = run_backend(instrument, scaled_events, rate, index*rate,
                                             evidence/"factory-repeat"/instrument["id"]/str(rate)/"B")
                    difference = float(np.max(np.abs(reference-repeated)))
                    assert difference <= 4/8388608, (instrument["id"], rate, difference)
                    rate_peaks = [p["peak"] for p in (peaks if rate == 48000 else isolated_peaks(instrument, pitches, rate))]
                    assert all(p > 1e-7 for p in rate_peaks), rate_peaks
                    for start in (0,3,6):
                        assert rate_peaks[start] < rate_peaks[start+1] < rate_peaks[start+2], (instrument["id"],rate,rate_peaks)
                    summary["checks"].append(dict(name=f"factory-grid-repeat:{instrument['id']}:{rate}", passed=True,
                                                  maximum_sample_difference=difference, peaks=rate_peaks))
            if is_drum:
                keys = list(range(low, high + 1))
                key_events = [dict(frame=i*24000, data=[0x90, key, 100]) for i, key in enumerate(keys)]
                key_audio, _ = run_backend(instrument, key_events, 48000, len(keys)*24000,
                                           evidence/"all-drum-keys"/instrument["id"])
                key_peaks = {str(key): float(np.max(np.abs(key_audio[:, i*24000:(i+1)*24000])))
                             for i, key in enumerate(keys)}
                assert all(peak > 1e-7 for peak in key_peaks.values()), key_peaks
                repeated, _ = run_backend(instrument, key_events, 48000, len(keys)*24000,
                                          evidence/"all-drum-keys-repeat"/instrument["id"])
                difference = float(np.max(np.abs(key_audio-repeated)))
                assert difference <= 4/8388608, (instrument["id"], difference)
                summary["checks"].append(dict(name=f"all-keys:{instrument['id']}", passed=True, peaks=key_peaks,
                                              maximum_sample_difference=difference))
            if is_sfz:
                keys = list(range(low, high + 1))
                key_events = [event for i, key in enumerate(keys) for event in
                              (dict(frame=i*24000, data=[0x90, key, 96]),
                               dict(frame=i*24000+12000, data=[0x80, key, 0]))]
                key_audio, _ = run_backend(instrument, key_events, 48000, len(keys)*24000,
                                           evidence/"all-sfz-keys"/instrument["id"])
                key_peaks = {str(key): float(np.max(np.abs(key_audio[:, i*24000:(i+1)*24000])))
                             for i, key in enumerate(keys)}
                assert all(peak > 1e-7 for peak in key_peaks.values()), key_peaks
                repeated, _ = run_backend(instrument, key_events, 48000, len(keys)*24000,
                                          evidence/"all-sfz-keys-repeat"/instrument["id"])
                difference = float(np.max(np.abs(key_audio-repeated)))
                assert difference <= 4/8388608, (instrument["id"], difference)
                summary["checks"].append(dict(name=f"all-keys:{instrument['id']}", passed=True, peaks=key_peaks,
                                              maximum_sample_difference=difference))
            write_json(evidence/"summary.json", summary)
            print(f"capabilities + repeatability: {instrument['id']} OK", flush=True)
        # Complete published scores: chords, tails, stems and a deliberate target-only edit.
        for example, rates in (("orchestra-sketch", (48000, 44100)), ("electronic-sketch", (48000, 44100))):
            for rate in rates:
                sketch = read_json(ROOT/"examples"/(example+".json"))
                sketch["output"]["sample_rate"] = rate
                sketch_path = directory/f"{example}-{rate}.json"
                write_json(sketch_path, sketch)
                outputs = [directory/f"{example}-{rate}-{n}" for n in (1, 2)]
                command(["validate", str(sketch_path)])
                for destination in outputs:
                    command(["render", str(sketch_path), "--output", str(destination)])
                    command(["inspect", str(destination)])
                differences = {}
                for filename in ["master.wav", *[f"stems/{track['id']}.wav" for track in sketch["tracks"]]]:
                    a, _ = read_wav(outputs[0]/filename)
                    b, _ = read_wav(outputs[1]/filename)
                    differences[filename] = float(np.max(np.abs(a-b)))
                    assert differences[filename] <= 4/8388608, (example, rate, filename, differences)
                if rate == 48000:
                    sketch["tracks"][0]["events"][0]["pitch"] += 2
                    write_json(sketch_path, sketch)
                    destination = directory/f"{example}-{rate}-edited"
                    command(["render", str(sketch_path), "--output", str(destination)])
                    command(["inspect", str(destination)])
                    for index, track in enumerate(sketch["tracks"]):
                        a, _ = read_wav(outputs[0]/f"stems/{track['id']}.wav")
                        b, _ = read_wav(destination/f"stems/{track['id']}.wav")
                        difference = float(np.max(np.abs(a-b)))
                        assert difference > 1e-5 if index == 0 else difference <= 4/8388608, (example, track["id"], difference)
                summary["checks"].append(dict(name=f"published-score:{example}:{rate}", passed=True,
                                              differences=differences, target_edit_verified=rate==48000))
        # A familiar beat-oriented score must pass the public CLI contract for both kits.
        for kit in ("avl-red-zeppelin", "avl-black-pearl"):
            beat = dict(version=1, title=f"Drum acceptance: {kit}", tempo=110,
                        time_signature=[4, 4], length_beats=8,
                        output=dict(sample_rate=48000, tail_seconds=2, master_gain_db=-6,
                                    stems=True, midi=True, intermediates=False),
                        tracks=[dict(id="drums", instrument=kit, events=[
                            *[dict(type="note", beat=n, duration=.2, pitch=36, velocity=105) for n in (0, 2, 4, 6)],
                            *[dict(type="note", beat=n, duration=.2, pitch=38, velocity=100) for n in (1, 3, 5, 7)],
                            *[dict(type="note", beat=n/2, duration=.1, pitch=42, velocity=65) for n in range(16)]])])
            beat_path = directory / f"{kit} beat.json"
            write_json(beat_path, beat)
            outputs = [directory / f"{kit} beat {n}" for n in (1, 2)]
            for destination in outputs:
                command(["validate", str(beat_path)])
                command(["render", str(beat_path), "--output", str(destination)])
                inspected_beat = command(["inspect", str(destination)])
                assert inspected_beat["data"]["status"] == "passed"
            drum_audio_a, _ = read_wav(outputs[0]/"master.wav")
            drum_audio_b, _ = read_wav(outputs[1]/"master.wav")
            difference = float(np.max(np.abs(drum_audio_a - drum_audio_b)))
            assert difference <= 4/8388608, (kit, difference)
            midi = mido.MidiFile(outputs[0]/"score.mid")
            note_ons = [msg.note for track in midi.tracks for msg in track if msg.type == "note_on" and msg.velocity > 0]
            assert len(note_ons) == 24 and set(note_ons) == {36, 38, 42}, note_ons
            assert all(msg.channel == 9 for track in midi.tracks for msg in track if not msg.is_meta)
            assert not any(msg.type == "control_change" for track in midi.tracks for msg in track)
            summary["checks"].append(dict(name=f"beat:{kit}", passed=True, midi_notes=len(note_ons),
                                           maximum_sample_difference=difference,
                                           output=str(outputs[0])))
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
