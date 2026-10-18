"""Pinned Surge XT 1.3.4 state and factory FXP adapters."""
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
from .juce_state import component_state, wrap_component
from .vst3 import load_state_plugin


def load_init_plugin(path: str):
    return load_state_plugin(path)


def patch_xml(component: bytes):
    if len(component) < 32 or component[:4] != b"sub3":
        raise RuntimeError("Unsupported Surge patch header")
    xml_size, *wave_sizes = struct.unpack_from("<7I", component, 4)
    expected_size = 32 + xml_size + sum(wave_sizes)
    if len(component) < expected_size or component[expected_size:] not in (b"", b"\0" * 16 + b"JUCEPrivateData"):
        raise RuntimeError("Invalid Surge patch XML/wavetable lengths")
    xml = ET.fromstring(component[32:32 + xml_size])
    if xml.tag != "patch" or xml.find("parameters") is None or xml.find("meta") is None:
        raise RuntimeError("Invalid Surge patch structure")
    return xml, xml_size


def factory_profile(path: Path) -> dict:
    """Import official FPCh payload, retaining embedded wavetables and vendor voice.

    Phase retrigger/drift and velocity sensitivity changes are recorded explicitly.
    FXP is not renamed to vstpreset, and no plugin GUI is involved.
    """
    fxp = path.read_bytes()
    if (len(fxp) < 92 or fxp[:4] != b"CcnK" or fxp[8:12] != b"FPCh" or
            fxp[16:20] != b"cjs3" or struct.unpack_from(">I", fxp, 56)[0] != len(fxp) - 60):
        raise RuntimeError(f"Invalid Surge factory FXP: {path}")
    component = fxp[60:]
    xml, xml_size = patch_xml(component)
    parameters = xml.find("parameters")
    edits = {}
    for scene in ("a", "b"):
        for key, value in {f"{scene}_osc{n}_retrigger": "1" for n in (1, 2, 3)}.items():
            node = parameters.find(key)
            if node is not None:
                node.set("value", value)
                edits[key] = value
        key = f"{scene}_drift"
        node = parameters.find(key)
        if node is not None:
            node.set("value", "0.000000")
            edits[key] = "0.000000"
        key = f"{scene}_vca_velsense"
        node = parameters.find(key)
        if node is not None:
            node.set("value", "-24.000000")
            edits[key] = "-24.000000"
    body = ET.tostring(xml, encoding="utf-8", xml_declaration=True)
    component = component[:4] + struct.pack("<I", len(body)) + component[8:32] + body + component[32 + xml_size:]
    return dict(version=1, name=xml.find("meta").get("name"), author=xml.find("meta").get("author"),
                raw_state_hex=wrap_component(component).hex(), normalized_parameters={},
                factory_edits=edits)


def verify_restored_patch(player, profile: dict) -> None:
    expected, _ = patch_xml(component_state(bytes.fromhex(profile["raw_state_hex"])))
    actual, _ = patch_xml(component_state(player.raw_state))
    if expected.find("meta").get("name") != actual.find("meta").get("name"):
        raise RuntimeError("Surge restored a different patch; preset initialization failed")
    keys = {f"{s}_osc{n}_type" for s in ("a", "b") for n in (1, 2, 3)} | set(profile.get("factory_edits", {}))
    for key in keys:
        source = expected.find(f"parameters/{key}")
        restored = actual.find(f"parameters/{key}")
        if source is not None and (restored is None or float(source.get("value")) != float(restored.get("value"))):
            raise RuntimeError(f"Surge did not restore expected control: {key}")
