"""JUCE VST3 component-state container (pinned host contract, no GUI)."""
import struct
import xml.etree.ElementTree as ET

_ALPHABET = ".ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+"


def decode_memory_block(text: str) -> bytes:
    size_text, encoded = text.split(".", 1)
    if not size_text.isdecimal() or len(encoded) != (int(size_text) * 8 + 5) // 6:
        raise RuntimeError("Invalid JUCE state block length")
    data = bytearray(int(size_text))
    for index, char in enumerate(encoded):
        value = _ALPHABET.index(char)
        for bit in range(6):
            position = index * 6 + bit
            if position < len(data) * 8 and value & (1 << bit):
                data[position // 8] |= 1 << (position % 8)
    return bytes(data)


def encode_memory_block(data: bytes) -> str:
    encoded = []
    for index in range((len(data) * 8 + 5) // 6):
        value = 0
        for bit in range(6):
            position = index * 6 + bit
            if position < len(data) * 8 and data[position // 8] & (1 << (position % 8)):
                value |= 1 << bit
        encoded.append(_ALPHABET[value])
    return f"{len(data)}." + "".join(encoded)


def component_state(state: bytes) -> bytes:
    if len(state) < 8 or state[:4] != b"VC2!":
        raise RuntimeError("Unsupported JUCE VST3 state header")
    length = struct.unpack_from("<I", state, 4)[0]
    if length > len(state) - 8:
        raise RuntimeError("Invalid JUCE VST3 state length")
    outer = ET.fromstring(state[8:8 + length])
    component = outer.find("IComponent")
    if outer.tag != "VST3PluginState" or component is None or not component.text:
        raise RuntimeError("Missing JUCE VST3 component state")
    return decode_memory_block(component.text)


def wrap_component(data: bytes) -> bytes:
    outer = ET.Element("VST3PluginState")
    ET.SubElement(outer, "IComponent").text = encode_memory_block(data)
    xml = ET.tostring(outer, encoding="utf-8", xml_declaration=True)
    return b"VC2!" + struct.pack("<I", len(xml)) + xml + b"\0"
