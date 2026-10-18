"""Project-local, pinned Windows x64 assets. No system install, GUI or registry changes."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from urllib.parse import quote
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
         sha256="15edb061d7ba60d58332f72dba8f8ce40988048cc703f935e6320f37d650e213"),
]
SFZ_PACKAGES = [dict(name="sfizioso-player-windows.zip", directory="sfizioso-player-0.12.3",
                     url="https://github.com/rullopat/sfizioso-player/releases/download/v0.12.3/sfizioso-player-windows.zip",
                     sha256="aa92b54b650b3d738e36a32f0ed654a98cea1ff1bb190219f5cba178a4e4a640")]
SOUNDFONTS = [
    dict(name="Red_Zeppelin_4_LV2.sf2", directory="avl-red-zeppelin",
         url="https://www.bandshed.net/sounds/AVLDrumkits_SF2/Red_Zeppelin_4_LV2.sf2",
         sha256="289fc3e30a4859eb74ae14eb08ddef453e8bf8eab3e501772dcf96fd8328a71a"),
    dict(name="Black_Pearl_4_LV2.sf2", directory="avl-black-pearl",
         url="https://www.bandshed.net/sounds/AVLDrumkits_SF2/Black_Pearl_4_LV2.sf2",
         sha256="e0542ec19f2816ef4e0d00aeb087e7aa311e888d6f4805f971688bb267c6d405")
]
VSCO_COMMIT = "28092772094b2d9f1148d84cea97f4545b8c687d"
VSCO_TREE = "1a4a082c22c7692b0926e1f0033a2ab634b29dd4"
VSCO_PATCHES = {
    "vsco-flute-sustain": dict(sfz="FluteSusNV.sfz", blob="804ff4f34e4be7b4f7c0b238314e80884aeadc2d",
                               sample_dir="Woodwinds/Flute/susNV", pitch_range=[60, 96], probe_note=72,
                               name="VSCO 2 CE solo flute sustain"),
    "vsco-trumpet-sustain": dict(sfz="TrumpetSus.sfz", blob="2b9be543a5179638788f8766dc1c181956975025",
                                   sample_dir="Brass/Trumpet/sus", pitch_range=[52, 84], probe_note=72,
                                   name="VSCO 2 CE solo trumpet sustain"),
    "vsco-violin-ensemble": dict(sfz="ViolinEnsSusVib.sfz", blob="07f05f5ad2cccb0d19b1902bc67ffa49cf15bc68",
                                sample_dir="Strings/Violin Section/susVib", pitch_range=[55, 86], probe_note=69,
                                name="VSCO 2 CE violin ensemble sustain vibrato")
}
FACTORY_PATCHES = {
    "surge-dx-ep": dict(path="Keys/DX EP.fxp", name="Surge XT DX electric piano", pitch_range=[36, 96]),
    "surge-e-bass": dict(path="Basses/E-Bass.fxp", name="Surge XT electric bass", pitch_range=[24, 84]),
    "surge-nice-pluck": dict(path="Plucks/Nice Pluck 1.fxp", name="Surge XT Nice Pluck 1", pitch_range=[36, 96]),
    "surge-classic-lead": dict(path="Leads/Classic Lead 1.fxp", name="Surge XT Classic Lead 1", pitch_range=[36, 96]),
    "surge-fm-pad": dict(path="Pads/FM Pad.fxp", name="Surge XT FM Pad", pitch_range=[36, 96]),
}


def git_blob(path: Path) -> str:
    digest = hashlib.sha1()
    digest.update(f"blob {path.stat().st_size}\0".encode("ascii"))
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def install_vsco(offline: bool) -> dict:
    cache = ROOT / "work/downloads/vsco-2-ce"
    directory = ROOT / "resources/vsco-2-ce"
    tree_cache = cache / "tree.json"
    cache.mkdir(parents=True, exist_ok=True)
    if not tree_cache.exists():
        if offline:
            raise RuntimeError(f"Offline VSCO tree missing: {tree_cache}; run without --offline once.")
        url = f"https://api.github.com/repos/sgossner/VSCO-2-CE/git/trees/{VSCO_TREE}?recursive=1"
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "code-to-music"}), timeout=60) as response:
            tree = json.load(response)
        if tree.get("sha") != VSCO_TREE or tree.get("truncated"):
            raise RuntimeError("VSCO Git tree response differs from pinned complete tree")
        write_json(tree_cache, tree)
    tree = json.loads(tree_cache.read_text(encoding="utf-8"))
    if tree.get("sha") != VSCO_TREE or tree.get("truncated"):
        raise RuntimeError(f"VSCO cached tree differs from pinned complete tree: {tree_cache}")
    blobs = {entry["path"]: entry["sha"] for entry in tree["tree"] if entry["type"] == "blob"}

    def obtain(relative: str, expected: str) -> Path:
        if blobs.get(relative) != expected:
            raise RuntimeError(f"VSCO pinned tree does not contain expected blob: {relative}")
        installed = directory / relative
        if installed.exists():
            if git_blob(installed) != expected:
                raise RuntimeError(f"VSCO installed file changed: {installed}; restore the pinned file.")
            return installed
        source = cache / relative
        if not source.exists():
            if offline:
                raise RuntimeError(f"Offline VSCO file missing: {source}; run without --offline once.")
            source.parent.mkdir(parents=True, exist_ok=True)
            partial = source.with_suffix(source.suffix + ".partial")
            url = f"https://raw.githubusercontent.com/sgossner/VSCO-2-CE/{VSCO_COMMIT}/{quote(relative, safe='/')}"
            urllib.request.urlretrieve(url, partial)
            if git_blob(partial) != expected:
                raise RuntimeError(f"VSCO download differs from pinned Git blob: {relative}")
            partial.replace(source)
        if git_blob(source) != expected:
            raise RuntimeError(f"VSCO cached file changed: {source}; restore the pinned file.")
        installed.parent.mkdir(parents=True, exist_ok=True)
        partial = installed.with_suffix(installed.suffix + ".partial")
        shutil.copyfile(source, partial)
        partial.replace(installed)
        return installed

    installed = {}
    for key, patch in VSCO_PATCHES.items():
        sfz = obtain(patch["sfz"], patch["blob"])
        content = sfz.read_text(encoding="utf-8-sig")
        samples = set(re.findall(r"(?m)^\s*sample\s*=\s*([^\r\n]+?)\s*$", content))
        if not samples or any("/" in name or "\\" in name or name in {".", ".."} for name in samples):
            raise RuntimeError(f"Unexpected VSCO sample references in {sfz}")
        expected_dir = patch["sample_dir"] + "/"
        listed = {path for path in blobs if path.startswith(expected_dir) and path.lower().endswith(".wav")}
        referenced = {expected_dir + name for name in samples}
        if referenced != listed:
            raise RuntimeError(f"VSCO sample listing differs from SFZ references: {sfz}; missing={sorted(referenced-listed)}, extra={sorted(listed-referenced)}")
        for relative in sorted(referenced):
            obtain(relative, blobs[relative])
        installed[key] = (sfz, directory / patch["sample_dir"])
        print(f"Verified {key}: {len(referenced)} samples", flush=True)
    return installed


def make_profile(plugin: Path, path: Path):
    from music.backends.surge import load_init_plugin
    player = load_init_plugin(str(plugin))
    # Capture startup patch explicitly: later renders do not inherit user patch state.
    profile = dict(version=1, name="Surge init, phase retrigger, no oscillator drift, velocity VCA -24dB",
                   raw_state_hex=player.raw_state.hex(),
                   normalized_parameters={"a_osc_1_retrigger": 1.0, "a_osc_drift": 0.0, "a_velocity_vca_gain": 0.5})
    write_json(path, profile)


def install(offline: bool, prepare_sfz: bool = False):
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("Pinned installer is verified only on Windows x64. Supply your own verified config on other platforms.")
    download_dir = ROOT / "work/downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    for package in PACKAGES + SFZ_PACKAGES:
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
    for soundfont in SOUNDFONTS:
        target = ROOT / "resources" / soundfont["directory"] / soundfont["name"]
        if not target.exists():
            if offline:
                raise RuntimeError(f"Offline soundfont missing: {target}; run without --offline once.")
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_suffix(target.suffix + ".partial")
            urllib.request.urlretrieve(soundfont["url"], partial)
            if fingerprint(partial) != soundfont["sha256"]:
                raise RuntimeError(f"Downloaded soundfont SHA-256 differs: {partial}; no installation performed.")
            partial.replace(target)
        if fingerprint(target) != soundfont["sha256"]:
            raise RuntimeError(f"Soundfont SHA-256 differs: {target}; restore the pinned file.")
        print(f"Verified {soundfont['name']}", flush=True)
    sfz_assets = install_vsco(offline)
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
    drum_limitations = ["Stereo SoundFont playback only; no separate mic channels or round-robin control.",
                        "MIDI notes 36..61 produced audio in the pinned SF2; 62..64 were silent and are excluded.",
                        "Sound quality has not been auditioned."]
    def drum(name, directory):
        return dict(backend="fluidsynth", name=name, version="AVL Drumkits 1.1 / LV2 SF2 (2023-09-05)",
            license="CC-BY-SA-3.0 with recorded-music exception", source="https://bandshed.net/avldrumkits/",
            bank=0, program=0, probe_note=38, percussion=True,
            assets=dict(library=asset(fluid/"libfluidsynth-3.dll"), runtime=asset(fluid),
                        soundfont=asset(ROOT/"resources"/directory/("Red_Zeppelin_4_LV2.sf2" if directory == "avl-red-zeppelin" else "Black_Pearl_4_LV2.sf2"))),
            capabilities=dict(pitch_range=[36,61], controllers=[]), verification=verification,
            limitations=drum_limitations)
    config = dict(version=1, instruments={
        "salamander-piano": dict(backend="fluidsynth", name="Salamander Grand Piano (FreePats SF2)", version="V3+20200602",
            license="CC-BY-3.0", source="https://freepats.zenvoid.org/Piano/acoustic-grand-piano.html", bank=0, program=0,
            assets=dict(library=asset(fluid/"libfluidsynth-3.dll"), runtime=asset(fluid), soundfont=asset(piano)),
            capabilities=dict(pitch_range=[21,108], controllers=[64]), verification=verification,
            limitations=["SF2 omits pedal/hammer/release-resonance noises and SFZ amp_veltrack.", "No sympathetic-resonance model; normal notes and CC64 only.", "Sound quality has not been auditioned."]),
        "avl-red-zeppelin": drum("AVL Red Zeppelin 4-piece sampled drums", "avl-red-zeppelin"),
        "avl-black-pearl": drum("AVL Black Pearl 4-piece sampled drums", "avl-black-pearl"),
        "surge-init": dict(backend="vst3", name="Surge XT phase-retriggered init patch", version="1.3.4",
            license="GPL-3.0-or-later (synth software)", source="https://surge-synthesizer.github.io/",
            assets=dict(plugin=asset(plugin), data=asset(surge/"SurgeXTData"), profile=asset(profile)),
            capabilities=dict(pitch_range=[21,108], controllers=[64]), verification=verification,
            limitations=["Only the captured init profile is admitted in this stage; arbitrary FXP preset loading is not verified.", "Only notes and CC64 are admitted; automation/program changes are rejected.", "General patches may include randomness; repeatability must be measured, not assumed.", "Software GPL does not itself impose GPL on rendered audio; external sample/preset rights need separate review."]),
    })
    sfz_plugin = ROOT / "resources/sfizioso-player-0.12.3/VST3/Sfizioso Player.vst3/Contents/x86_64-win/Sfizioso Player.vst3"
    for key, patch in VSCO_PATCHES.items():
        sfz_path, samples = sfz_assets[key]
        config["instruments"][key] = dict(backend="sfz", name=patch["name"],
            version="VSCO 2 CE 1.1.0 / sfizioso Player 0.12.3",
            license="CC0-1.0 samples; AGPL-3.0 player application, BSD-2-Clause engine",
            source=f"https://github.com/sgossner/VSCO-2-CE/tree/{VSCO_COMMIT}", probe_note=patch["probe_note"],
            assets=dict(plugin=asset(sfz_plugin), sfz=asset(sfz_path), samples=asset(samples)),
            capabilities=dict(pitch_range=patch["pitch_range"], controllers=[]), verification=verification,
            limitations=["Only this sustained articulation and its documented note/velocity range are admitted.",
                         "No keyswitches, expression CC or round-robin control is verified.",
                         "Sound quality has not been auditioned."])
    from music.backends.surge import factory_profile
    profile_dir = ROOT / "resources/surge-profiles"
    profile_dir.mkdir(parents=True, exist_ok=True)
    for key, patch in FACTORY_PATCHES.items():
        fxp_path = surge / "SurgeXTData/patches_factory" / patch["path"]
        factory = factory_profile(fxp_path)
        factory["source"] = dict(path=patch["path"], sha256=fingerprint(fxp_path))
        factory_path = profile_dir / (key + ".json")
        if factory_path.exists():
            if json.loads(factory_path.read_text(encoding="utf-8")) != factory:
                raise RuntimeError(f"Factory profile changed: {factory_path}; preserve it before regenerating.")
        else:
            write_json(factory_path, factory)
        config["instruments"][key] = dict(backend="vst3", name=patch["name"], version="Surge XT 1.3.4 factory / profile v1",
            license="GPL-3.0-or-later (synth software); bundled factory content by Claes",
            source="https://github.com/surge-synthesizer/releases-xt/releases/tag/1.3.4", probe_note=60,
            assets=dict(plugin=asset(plugin), data=asset(surge/"SurgeXTData"),
                        profile=asset(factory_path), factory=asset(fxp_path)),
            capabilities=dict(pitch_range=patch["pitch_range"], controllers=[]), verification=verification,
            limitations=["Curated factory profile: all oscillators retrigger, drift=0, velocity VCA=-24 dB.",
                         "Notes/velocity only; CC, automation and arbitrary FXP import are not admitted.",
                         "Factory effects and embedded wavetables are retained; sound quality has not been auditioned."])
    config_path = ROOT / "music.config.json"
    if config_path.exists():
        existing = json.loads(config_path.read_text(encoding="utf-8"))
        if existing.get("version") != 1 or not isinstance(existing.get("instruments"), dict):
            raise RuntimeError("Existing music.config.json has an unknown shape; preserve it before repair.")
        for key, instrument in config["instruments"].items():
            if key in existing["instruments"] and existing["instruments"][key] != instrument:
                old = existing["instruments"][key]
                prior_drum = dict(instrument)
                prior_drum.pop("percussion", None)
                prior_drum["capabilities"] = dict(pitch_range=[36, 64], controllers=[])
                prior_drum["limitations"] = ["Stereo SoundFont playback only; no separate mic channels or round-robin control.",
                                               "MIDI notes 36..64 follow the AVL keymap; verify each admitted note with a render.",
                                               "Sound quality has not been auditioned."]
                if key.startswith("avl-") and old == prior_drum:
                    existing["instruments"][key] = instrument
                else:
                    raise RuntimeError(f"Existing instrument {key} differs. Preserve the config and resolve that entry before syncing.")
        added = {key: value for key, value in config["instruments"].items() if key not in existing["instruments"]}
        if added or existing != json.loads(config_path.read_text(encoding="utf-8")):
            existing["instruments"].update(added)
            pending = config_path.with_suffix(".json.pending")
            write_json(pending, existing)
            pending.replace(config_path)
    else:
        write_json(config_path, config)
    write_json(ROOT / "resources/download-manifest.json", dict(version=1, packages=PACKAGES,
        soundfonts=SOUNDFONTS,
        sfz=dict(packages=SFZ_PACKAGES, commit=VSCO_COMMIT, tree=VSCO_TREE, patches=VSCO_PATCHES,
                 admitted=True, render_mode="freewheel, 1024 KiB preload"),
        factory_presets=FACTORY_PATCHES,
        checksum_origin="SHA-256 observed from upstream HTTPS downloads on 2026-10-12; not an upstream signature."))
    print(f"Ready: {config_path}. Next: music doctor --json", flush=True)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--create-profile":
        make_profile(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        parser = argparse.ArgumentParser(description=__doc__)
        parser.add_argument("--offline", action="store_true", help="Use only hash-verified archives in work/downloads.")
        parser.add_argument("--prepare-sfz", action="store_true", help="Compatibility flag; pinned SFZ instruments are now installed by default.")
        args = parser.parse_args()
        try:
            install(args.offline, args.prepare_sfz)
        except Exception as exc:
            print(f"E_INSTALL: {exc}\nFix: inspect work/downloads and README.md; rerun after repairing the named resource.", file=sys.stderr)
            raise SystemExit(2)
