from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
import re
from jsonschema import Draft202012Validator
from .errors import MusicError, read_json


@dataclass(frozen=True)
class Score:
    data: dict
    sample_rate: int
    frames: int
    seconds_per_beat: float
    output: dict


def pitch_number(value: int | str) -> int:
    if isinstance(value, int):
        return value
    match = re.fullmatch(r"([A-G])([#b]?)(-?\d)", value)
    note, accidental, octave = match.groups()
    return (int(octave) + 1) * 12 + {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[note] + {"": 0, "#": 1, "b": -1}[accidental]


def load_score(path: Path) -> Score:
    data = read_json(path)
    schema = read_json(Path(str(files("music").joinpath("schemas/score-v1.json"))))
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: str(e.json_path))
    if errors:
        detail = "; ".join(f"{e.json_path}: {e.message}" for e in errors[:8])
        raise MusicError("E_SCHEMA", detail, str(path), "Match score-v1.json; remove unsupported fields; version must be 1.")
    ids = set()
    for track in data["tracks"]:
        tid = track["id"]
        if tid.lower() in ids:
            raise MusicError("E_SCORE", "Duplicate track id (case insensitive).", tid, "Give each track a unique id.")
        ids.add(tid.lower())
        notes = []
        for event in track["events"]:
            end = event["beat"] + event.get("duration", 0)
            if end > data["length_beats"] or event["beat"] >= data["length_beats"]:
                raise MusicError("E_SCORE", "Event exceeds length_beats.", tid, "Extend length_beats or shorten/move this event.")
            if event["type"] == "note":
                note = pitch_number(event["pitch"])
                if not 0 <= note <= 127:
                    raise MusicError("E_SCORE", f"Pitch resolves to MIDI {note}.", tid, "Use MIDI 0..127; C4=60.")
                for start, stop, previous in notes:
                    if event["beat"] < stop and end > start and (previous == note or track.get("overlap") == "reject"):
                        raise MusicError("E_OVERLAP", "Ambiguous overlapping notes.", tid,
                                         "Separate same-pitch notes; use overlap=polyphonic for different pitches.")
                notes.append((event["beat"], end, note))
    output = dict(sample_rate=48000, tail_seconds=2, master_gain_db=-6, stems=True, midi=True, intermediates=False)
    output.update(data.get("output", {}))
    spb = 60 / data["tempo"]
    frames = round((data["length_beats"] * spb + output["tail_seconds"]) * output["sample_rate"])
    if frames < 1:
        raise MusicError("E_SCORE", "Score duration rounds to zero audio frames.", str(path),
                         "Increase length_beats or output.tail_seconds to produce at least one frame at the selected sample_rate.")
    if frames / output["sample_rate"] > 300:
        raise MusicError("E_LIMIT", "Duration exceeds the stage-one 300-second limit.", str(path), "Split the score into sections.")
    return Score(data, output["sample_rate"], frames, spb, output)


def timeline(score: Score, track: dict) -> list[dict]:
    """Sample-addressed MIDI. Order at a shared boundary: note-off, CC, note-on."""
    result = []
    def append(beat, order, data):
        result.append(dict(frame=round(beat * score.seconds_per_beat * score.sample_rate), order=order, data=data))
    for event in track["events"]:
        if event["type"] == "cc":
            append(event["beat"], 1, [0xB0, event["controller"], event["value"]])
        else:
            note = pitch_number(event["pitch"])
            append(event["beat"], 2, [0x90, note, event["velocity"]])
            append(event["beat"] + event["duration"], 0, [0x80, note, 0])
    append(score.data["length_beats"], 1, [0xB0, 64, 0])
    return sorted(result, key=lambda e: (e["frame"], e["order"]))
