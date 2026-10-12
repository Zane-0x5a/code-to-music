"""Project-local, pinned Windows x64 assets. No system install, GUI or registry changes."""
from pathlib import Path
import argparse
import json
import os
import platform
import subprocess
import sys
import tarfile
import urllib.request
import zipfile
from music.errors import fingerprint, write_json

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = [
    dict(name="fluidsynth-v2.6.1-win10-x64-cpp11.zip", directory="fluidsynth-2.6.1",
         url="https://github.com/FluidSynth/fluidsynth/releases/download/v2.6.1/fluidsynth-v2.6.1-win10-x64-cpp11.zip",
         sha256="fab7a2e4b85675b66970f97a39bbc239729c5e0f237198b5922a6a73cbc8677c"),
    dict(name="surge-xt-win64-1.3.4-portable-install.zip", directory="surge-xt-1.3.4",
         url="https://github.com/surge-synthesizer/releases-xt/releases/download/1.3.4/surge-xt-win64-1.3.4-portable-install.zip",
         sha256="a5f2376702ad218c0382640ed0c7b9ebb222ba2410a210879899c0f726859d8e"),
    dict(name="SalamanderGrandPiano-SF2-V3+20200602.tar.xz", directory="salamander",
         url="https://freepats.zenvoid.org/Piano/SalamanderGrandPiano/SalamanderGrandPiano-SF2-V3+20200602.tar.xz",
         sha256="15edb061d7ba60d58332f72dba8f8ce40988048cc703f935e6320f37d650e213")
]


def make_profile(plugin: Path, path: Path):
    from music.backends.surge import load_init_plugin
    player = load_init_plugin(str(plugin))
    # Capture startup patch explicitly: later renders do not inherit user patch state.
    profile = dict(version=1, name="Surge init, phase retrigger, no oscillator drift, velocity VCA -24dB",
                   raw_state_hex=player.raw_state.hex(),
                   normalized_parameters={"a_osc_1_retrigger": 1.0, "a_osc_drift": 0.0, "a_velocity_vca_gain": 0.5})
    write_json(path, profile)


def install(offline: bool):
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("Pinned installer is verified only on Windows x64. Supply your own verified config on other platforms.")
    download_dir = ROOT / "work/downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    for package in PACKAGES:
        archive = download_dir / package["name"]
        if not archive.exists():
            if offline:
                raise RuntimeError(f"Offline cache missing: {archive}; run without --offline once.")
            print(f"Downloading {package['name']}", flush=True)
            partial = archive.with_suffix(archive.suffix + ".partial")
            urllib.request.urlretrieve(package["url"], partial)
            partial.replace(archive)
        if fingerprint(archive) != package["sha256"]:
            raise RuntimeError(f"Checksum differs for {archive}; restore the pinned archive. No extraction performed.")
        directory = ROOT / "resources" / package["directory"]
        marker = directory / ".installed-sha256"
        if not marker.exists():
            directory.mkdir(parents=True, exist_ok=True)
            if archive.suffix == ".zip":
                with zipfile.ZipFile(archive) as zipped:
                    for info in zipped.infolist():
                        if not (directory / info.filename).resolve().is_relative_to(directory.resolve()):
                            raise RuntimeError("Archive path escapes install directory")
                    zipped.extractall(directory)
            else:
                with tarfile.open(archive) as tar:
                    tar.extractall(directory, filter="data")
            marker.write_text(package["sha256"], encoding="utf-8")
        print(f"Verified {package['name']}", flush=True)
    fluid = ROOT / "resources/fluidsynth-2.6.1/fluidsynth-v2.6.1-win10-x64-cpp11/bin"
    surge = ROOT / "resources/surge-xt-1.3.4/Surge Synth Team"
    piano = ROOT / "resources/salamander/SalamanderGrandPiano-SF2-V3+20200602/SalamanderGrandPiano-V3+20200602.sf2"
    plugin = surge / "Surge XT.vst3/Contents/x86_64-win/Surge XT.vst3"
    profile = ROOT / "resources/surge-profile.json"
    if not profile.exists():
        subprocess.run([sys.executable, str(Path(__file__)), "--create-profile", str(plugin), str(profile)],
                       check=True, timeout=90, stdin=subprocess.DEVNULL)
    def asset(path):
        return dict(path=path.relative_to(ROOT).as_posix(), sha256=fingerprint(path))
    verification = "Installed and hash-pinned; run music doctor and scripts/acceptance.py to verify on this machine."
    config = dict(version=1, instruments={
        "salamander-piano": dict(backend="fluidsynth", name="Salamander Grand Piano (FreePats SF2)", version="V3+20200602",
            license="CC-BY-3.0", source="https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html", bank=0, program=0,
            assets=dict(library=asset(fluid/"libfluidsynth-3.dll"), runtime=asset(fluid), soundfont=asset(piano)),
            capabilities=dict(pitch_range=[21,108], controllers=[64]), verification=verification,
            limitations=["SF2 omits pedal/hammer/release-resonance noises and SFZ amp_veltrack.", "No sympathetic-resonance model; normal notes and CC64 only.", "Sound quality has not been auditioned."]),
        "surge-init": dict(backend="vst3", name="Surge XT phase-retriggered init patch", version="1.3.4",
            license="GPL-3.0-or-later (synth software)", source="https://surge-synthesizer.github.io/",
            assets=dict(plugin=asset(plugin), data=asset(surge/"SurgeXTData"), profile=asset(profile)),
            capabilities=dict(pitch_range=[21,108], controllers=[64]), verification=verification,
            limitations=["Only the captured init profile is admitted in this stage; arbitrary FXP preset loading is not verified.", "Only notes and CC64 are admitted; automation/program changes are rejected.", "General patches may include randomness; repeatability must be measured, not assumed.", "Software GPL does not itself impose GPL on rendered audio; external sample/preset rights need separate review."])
    })
    config_path = ROOT / "music.config.json"
    if config_path.exists():
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if existing != config:
            raise RuntimeError("Existing music.config.json differs. Preserve it and rename it before regenerating; no automatic overwrite.")
    else:
        write_json(config_path, config)
    write_json(ROOT / "resources/download-manifest.json", dict(version=1, packages=PACKAGES,
        checksum_origin="SHA-256 observed from upstream HTTPS downloads on 2026-10-12; not an upstream signature."))
    print(f"Ready: {config_path}. Next: music doctor --json", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-profile":
        make_profile(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--offline", action="store_true", help="Use only hash-verified archives in work/downloads.")
        args = parser.parse_args()
        try:
            install(args.offline)
        except Exception as exc:
            print(f"E_INSTALL: {exc}\nFix: inspect work/downloads and README.md; rerun after repairing the named resource.", file=sys.stderr)
            raise SystemExit(2)
