from pathlib import Path
import mido
from .score import Score, timeline


def write_midi(path: Path, score: Score, tracks: list[dict], instruments: dict) -> None:
    output = mido.MidiFile(type=1, ticks_per_beat=960)
    meta = mido.MidiTrack()
    meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(score.data["tempo"])))
    meta.append(mido.MetaMessage("time_signature", numerator=score.data["time_signature"][0], denominator=score.data["time_signature"][1]))
    meta.append(mido.MetaMessage("end_of_track", time=round(score.data["length_beats"] * 960)))
    output.tracks.append(meta)
    melodic_channels = iter([*range(9), *range(10, 16)])
    for track in tracks:
        if track.get("mute", False):
            continue
        channel = 9 if instruments[track["instrument"]].get("percussion", False) else next(melodic_channels)
        midi_track = mido.MidiTrack()
        midi_track.append(mido.MetaMessage("track_name", name=track["id"]))
        previous = 0
        for event in timeline(score, track):
            tick = round(event["frame"] / score.sample_rate / score.seconds_per_beat * 960)
            message = mido.Message.from_bytes([event["data"][0] | channel, *event["data"][1:]])
            message.time = tick - previous
            previous = tick
            midi_track.append(message)
        midi_track.append(mido.MetaMessage("end_of_track"))
        output.tracks.append(midi_track)
    output.save(str(path))
