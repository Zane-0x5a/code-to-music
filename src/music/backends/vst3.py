"""Pinned state-only VST3 loading inside isolated, single-instrument workers."""
from importlib.metadata import version
import numpy as np


def render_frames(player, midi, frames: int, sample_rate: int):
    """Account for Pedalboard 0.9.26's float32 seconds -> unsigned frame count.

    Round the duration upward only when needed, render once, then retain exactly
    the requested frames. Never pad or accept a native output shorter than planned.
    """
    duration = np.float32(frames / sample_rate)
    native_frames = int(np.float32(duration * np.float32(sample_rate)))
    while native_frames < frames:
        duration = np.nextafter(duration, np.float32(np.inf))
        native_frames = int(np.float32(duration * np.float32(sample_rate)))
    audio = player(midi, duration=float(duration), sample_rate=sample_rate,
                   num_channels=2, buffer_size=512, reset=True)
    if audio.shape != (2, native_frames):
        raise RuntimeError(f"Native duration conversion produced {audio.shape}; expected (2, {native_frames})")
    return audio[:, :frames]


def load_state_plugin(path: str):
    from pedalboard import ExternalPlugin, load_plugin
    if version("pedalboard") != "0.9.26":
        raise RuntimeError("VST3 adapters require Pedalboard 0.9.26; reinstall requirements.lock")
    own_hook = ExternalPlugin.__dict__.get("__set_initial_parameter_values__")
    original = ExternalPlugin.__set_initial_parameter_values__

    def empty_initial_values(plugin, values):
        if values:
            raise RuntimeError("State-only adapter does not accept an initial parameter map")

    # 0.9.26 scans every control even for an empty map. Our fixed adapters
    # restore raw state directly, so neither name inference nor that scan is used.
    ExternalPlugin.__set_initial_parameter_values__ = empty_initial_values
    try:
        return load_plugin(path, initialization_timeout=15)
    finally:
        if own_hook is None:
            del ExternalPlugin.__set_initial_parameter_values__
        else:
            ExternalPlugin.__set_initial_parameter_values__ = original
