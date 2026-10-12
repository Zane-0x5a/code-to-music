"""Pinned Pedalboard compatibility inside a single-instrument worker.

0.9.26 enumerates all controls even for an empty initial parameter map.
The scoped hook avoids that scan; raw profile controls are applied separately.
This module is internal and must not be used by concurrent in-process hosts.
"""
from importlib.metadata import version


def load_init_plugin(path: str):
    from pedalboard import ExternalPlugin, load_plugin
    if version("pedalboard") != "0.9.26":
        raise RuntimeError("Surge adapter requires pinned Pedalboard 0.9.26; reinstall requirements.lock")
    own_hook = ExternalPlugin.__dict__.get("__set_initial_parameter_values__")
    original = ExternalPlugin.__set_initial_parameter_values__

    def empty_initial_values(plugin, values):
        if values:
            raise RuntimeError("Surge adapter admits only captured raw state and normalized profile controls")

    ExternalPlugin.__set_initial_parameter_values__ = empty_initial_values
    try:
        return load_plugin(path, initialization_timeout=15)
    finally:
        if own_hook is None:
            del ExternalPlugin.__set_initial_parameter_values__
        else:
            ExternalPlugin.__set_initial_parameter_values__ = original
