"""FluidSynth C API; no audio/MIDI driver or device is created."""
import ctypes as c
import os
from pathlib import Path
import numpy as np


class Fluid:
    def __init__(self, library: str, sample_rate: int):
        self.directory = os.add_dll_directory(str(Path(library).parent)) if os.name == "nt" else None
        self.lib = c.CDLL(library)
        def function(name, result, args):
            value = getattr(self.lib, name)
            value.restype = result
            value.argtypes = args
            return value
        ptr, integer, string = c.c_void_p, c.c_int, c.c_char_p
        self.new_settings = function("new_fluid_settings", ptr, [])
        self.setnum = function("fluid_settings_setnum", integer, [ptr, string, c.c_double])
        self.setint = function("fluid_settings_setint", integer, [ptr, string, integer])
        self.new_synth = function("new_fluid_synth", ptr, [ptr])
        self.sfload = function("fluid_synth_sfload", integer, [ptr, string, integer])
        self.program = function("fluid_synth_program_select", integer, [ptr, integer, integer, integer, integer])
        self.noteon = function("fluid_synth_noteon", integer, [ptr, integer, integer, integer])
        self.noteoff = function("fluid_synth_noteoff", integer, [ptr, integer, integer])
        self.cc = function("fluid_synth_cc", integer, [ptr, integer, integer, integer])
        self.write = function("fluid_synth_write_float", integer, [ptr, integer, ptr, integer, integer, ptr, integer, integer])
        self.delete_synth = function("delete_fluid_synth", None, [ptr])
        self.delete_settings = function("delete_fluid_settings", None, [ptr])
        self.version = function("fluid_version_str", string, [])().decode()
        self.settings = self.new_settings()
        self.synth = None
        if not self.settings:
            raise RuntimeError("Cannot allocate FluidSynth settings")
        try:
            for key, value in [(b"synth.sample-rate", sample_rate), (b"synth.gain", 0.5)]:
                if self.setnum(self.settings, key, value) < 0:
                    raise RuntimeError(f"Cannot set {key!r}")
            for key, value in [(b"synth.reverb.active", 0), (b"synth.chorus.active", 0), (b"synth.cpu-cores", 1)]:
                if self.setint(self.settings, key, value) < 0:
                    raise RuntimeError(f"Cannot set {key!r}")
            self.synth = self.new_synth(self.settings)
            if not self.synth:
                raise RuntimeError("Cannot allocate FluidSynth")
        except BaseException:
            self.close()
            raise

    def load(self, instrument: dict) -> None:
        sfid = self.sfload(self.synth, os.fsencode(instrument["assets"]["soundfont"]["path"]), 0)
        if sfid < 0 or self.program(self.synth, 0, sfid, instrument.get("bank", 0), instrument.get("program", 0)) < 0:
            raise RuntimeError("Cannot load soundfont/bank/program; check SoundFont format and program.")

    def render(self, events: list[dict], frames: int) -> np.ndarray:
        audio = np.zeros((2, frames), dtype=np.float32)
        position = 0
        for event in [*events, dict(frame=frames, data=None)]:
            stop = event["frame"]
            if stop > position:
                left = audio[0, position:stop]
                right = audio[1, position:stop]
                if self.write(self.synth, stop-position, left.ctypes.data, 0, 1, right.ctypes.data, 0, 1) < 0:
                    raise RuntimeError("FluidSynth sample rendering failed")
                position = stop
            data = event["data"]
            if data:
                status, first, second = data
                if status == 0x90:
                    result = self.noteon(self.synth, 0, first, second)
                elif status == 0x80:
                    result = self.noteoff(self.synth, 0, first)
                    # One-shot samples may have ended before their scheduled note-off.
                    # FluidSynth reports no matching voice as a failure in that case.
                    if result < 0:
                        continue
                else:
                    result = self.cc(self.synth, 0, first, second)
                if result < 0:
                    raise RuntimeError(f"FluidSynth rejected MIDI {data}")
        return audio

    def close(self):
        if self.synth:
            self.delete_synth(self.synth)
            self.synth = None
        if self.settings:
            self.delete_settings(self.settings)
            self.settings = None
        if self.directory:
            self.directory.close()
            self.directory = None
