"""Internal subprocess contract: request.json -> audio.npy + result.json.

Native plugin crashes/timeouts never terminate the CLI process.
"""
from pathlib import Path
import sys
import time
import numpy as np
from .errors import read_json, write_json


def run(request: dict) -> dict:
    instrument = request["instrument"]
    sample_rate, frames = request["sample_rate"], request["frames"]
    if instrument["backend"] == "fluidsynth":
        from .backends.fluid import Fluid
        player = Fluid(instrument["assets"]["library"]["path"], sample_rate)
        try:
            player.load(instrument)
            audio = player.render(request["events"], frames)
            backend_version = player.version
        finally:
            player.close()
    else:
        from pedalboard import AudioProcessorParameter
        from .backends.surge import load_init_plugin
        player = load_init_plugin(instrument["assets"]["plugin"]["path"])
        if not player.is_instrument:
            raise RuntimeError("VST3 is an effect, not a MIDI instrument")
        profile = read_json(Path(instrument["assets"]["profile"]["path"]))
        # Bypass the mixin's parameter-name lookup for this native descriptor;
        # ordinary assignment would enumerate every unrelated plugin control.
        object.__setattr__(player, "raw_state", bytes.fromhex(profile["raw_state_hex"]))
        # Surge restores patches asynchronously. A tight offline render can finish
        # before the patch loader has run. Prime with a discarded note and wait
        # for real audio, bounded independently of the outer worker timeout.
        deadline = time.monotonic() + 15
        attempts = 0
        while True:
            attempts += 1
            probe = player([([0x90,60,96],0), ([0x80,60,0],.03)], duration=.1,
                           sample_rate=sample_rate, num_channels=2, buffer_size=512, reset=True)
            if float(np.max(np.abs(probe))) > 1e-6:
                break
            if time.monotonic() >= deadline:
                raise RuntimeError("Surge preset initialization stayed silent after 15 seconds")
            time.sleep(.02)
        # Construct only the admitted public parameter wrappers. Enumerating
        # every parameter probes thousands of text values per control and can
        # take over 90s; no other controls are needed for this pinned profile.
        parameter_names = {"a_osc_1_retrigger": "A Osc 1 Retrigger", "a_osc_drift": "A Osc Drift",
                           "a_velocity_vca_gain": "A Velocity > VCA Gain"}
        for key, raw in profile["normalized_parameters"].items():
            if key not in parameter_names:
                raise RuntimeError(f"Preset parameter not available: {key}")
            # Only normalized raw values are used; label/range inference is
            # unnecessary, so inspect endpoints instead of 1000 text values.
            AudioProcessorParameter(player, parameter_names[key], search_steps=1).raw_value = raw
        # Host reset alone does not remove the first-render residue of the
        # readiness note. Advance the admitted init patch until its decay and
        # parameter smoothing have settled, without including this in output.
        settled_seconds = 0.0
        while settled_seconds < 10:
            decay = player([], duration=.5, sample_rate=sample_rate,
                           num_channels=2, buffer_size=512, reset=False)
            settled_seconds += .5
            settled_peak = float(np.max(np.abs(decay[:, -round(sample_rate * .1):])))
            if settled_seconds >= 2 and settled_peak <= 1e-12:
                break
        else:
            raise RuntimeError("Surge readiness note did not settle below 1e-12 within 10 audio seconds")
        midi = [(e["data"], e["frame"] / sample_rate) for e in request["events"]]
        audio = player(midi, duration=frames/sample_rate, sample_rate=sample_rate,
                       num_channels=2, buffer_size=512, reset=True)
        backend_version = str(player.version)
    if audio.shape != (2, frames) or not np.all(np.isfinite(audio)):
        raise RuntimeError(f"Invalid native audio shape/values: {audio.shape}; expected (2, {frames})")
    np.save(request["audio_path"], audio, allow_pickle=False)
    return dict(ok=True, backend_version=backend_version, frames=frames,
                initialization_attempts=attempts if instrument["backend"] == "vst3" else 1,
                initialization_settle_seconds=settled_seconds if instrument["backend"] == "vst3" else 0,
                peak=float(np.max(np.abs(audio))))


if __name__ == "__main__":
    request = read_json(Path(sys.argv[1]))
    try:
        result = run(request)
    except Exception as exc:
        result = dict(ok=False, reason=f"{type(exc).__name__}: {exc}")
    write_json(Path(request["result_path"]), result)
    raise SystemExit(0 if result["ok"] else 1)
