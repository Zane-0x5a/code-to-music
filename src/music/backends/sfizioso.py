"""Restore a pinned SFZ path through sfizioso Player's JUCE VST3 state."""
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

from .vst3 import load_state_plugin
from .juce_state import component_state, wrap_component


def load_sfz_plugin(plugin_path: str, sfz_path: str):
    player = load_state_plugin(plugin_path)
    if not player.is_instrument:
        raise RuntimeError("Sfizioso Player VST3 did not expose a MIDI instrument")
    inner = component_state(player.raw_state)
    if len(inner) < 8:
        raise RuntimeError("Truncated Sfizioso Player JUCE state")
    marker, length = struct.unpack_from("<II", inner)
    if marker != 0x21324356 or length > len(inner) - 8:
        raise RuntimeError("Unsupported Sfizioso Player JUCE state")
    parameters = ET.fromstring(inner[8:8 + length].rstrip(b"\0"))
    if parameters.tag != "PARAMETERS" or "sfzPath" not in parameters.attrib:
        raise RuntimeError("Sfizioso Player state has no SFZ path property")
    sfz = Path(sfz_path).resolve(strict=True)
    # PlayerProcessor v0.12.3 exposes real (not normalized) APVTS values.
    # Real-time streaming cannot keep up with a faster-than-wall-clock host.
    # Freewheel makes sample reads synchronous; preload index 8 is 1024 KiB.
    for key, value in {"freewheel": "1.0", "preloadSize": "8.0"}.items():
        parameter = parameters.find(f"PARAM[@id='{key}']")
        if parameter is None:
            raise RuntimeError(f"Sfizioso Player state lacks required offline control: {key}")
        parameter.set("value", value)
    parameters.set("sfzPath", str(sfz))
    xml = ET.tostring(parameters, encoding="utf-8") + b"\0"
    object.__setattr__(player, "raw_state", wrap_component(inner[:4] + struct.pack("<I", len(xml)) + xml))
    return player
