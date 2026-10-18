# code-to-music

[简体中文](README.md) | **English**

Edit a JSON score with a coding agent, run `music validate` and `music render`, and get technically checked PCM24 stereo WAV, stems, MIDI, and machine-readable reports. The current release provides **12 fixed instruments**: Salamander piano, two AVL sampled drum kits, VSCO flute/trumpet/violin ensemble, Surge init, and electric piano/bass/pluck/lead/FM pad profiles. No DAW, GUI, or audio device is required.

Start with the [four demos](docs/DEMOS.md), then copy their JSON scores to change notes or arrangements. After installation, see the [Agent quickstart](docs/AGENT_QUICKSTART.md) and [0.5.0 release notes](docs/RELEASE_NOTES_0.5.0.md). Supporting documentation is currently primarily in Chinese; the installation and CLI instructions below are in English.

The instruments have not yet received documented listening approval. See [PALETTE_ACCEPTANCE.md](docs/PALETTE_ACCEPTANCE.md) for the scope and technical verification of 0.5.0, and [STAGE_ONE.md](docs/STAGE_ONE.md) for earlier evidence. A plugin loading successfully does not make it a verified instrument.

The current version is **0.5.0 / CLI JSON v3**. `inspect` returns status, the selected instruments' IDs, versions and asset SHA-256 hashes, and the full report path; failed reports never produce a success response. Scores with no events or with every track muted are rejected early with `E_SCORE`. The main WAV is always checked for silence. Since 0.4.0, the main mix and quiet stems have different loudness requirements; failures include measured values, thresholds, and the report path. CLI JSON v3, inspect summary v2, and score/full-report v1 contracts remain compatible. See the [migration history](docs/REVIEW_FOLLOWUP.md).

## Install on Windows x64

Use **64-bit Python 3.13** (tested with 3.13.7). Dependencies require at least Python 3.12, but instrument acceptance has not been completed on that version. You also need FFmpeg on `PATH` and at least 5 GB of project disk space; acceptance artifacts require additional space. Downloads for the pinned Windows x64 instruments total approximately 650 MB. Installation does not change system audio settings or global plugin directories.

Download and extract the source using **Code → Download ZIP**, or clone this repository. Open PowerShell in the directory containing `pyproject.toml`. The resource installer and examples are included in the source; installing the wheel alone does not include them.

After installing Python, confirm that `python --version` selects the intended version. Choose a Windows build from the [FFmpeg download page](https://ffmpeg.org/download.html), extract it, and add the `bin` directory containing `ffmpeg.exe` to `PATH`, or install it with your existing package manager. Open a new terminal after changing `PATH`. Desktop applications such as Codex may need to restart to inherit it.

Before downloading instruments, run:

```powershell
python --version
python -c "import struct, sys; print(sys.executable); assert sys.version_info >= (3, 12), 'Python 3.12+ required'; assert struct.calcsize('P') == 8, '64-bit Python required'"
ffmpeg -version
```

Once all three succeed, run the following commands one at a time. Fix any error before continuing. The render output directory must not already exist; use a new path such as `outputs\second` for another render.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.lock
.\.venv\Scripts\python.exe -m pip install --no-deps .
.\.venv\Scripts\python.exe scripts\install_resources.py
.\.venv\Scripts\music.exe doctor --json
.\.venv\Scripts\music.exe validate examples\first-score.json --json
.\.venv\Scripts\music.exe validate examples\drum-beat.json --json
.\.venv\Scripts\music.exe render examples\first-score.json --output outputs\first --json
.\.venv\Scripts\music.exe inspect outputs\first --json
```

Add `.venv\Scripts` to the current shell's `PATH` to call `music` directly. `python -m music` is equivalent to `music`, provided you use the Python environment where this package is installed. Network access is only needed during installation; rendering is fully offline. Use `scripts/install_resources.py --offline` with cached archives. Archives with mismatched SHA-256 hashes are rejected before extraction. These hashes are locally pinned values from upstream HTTPS downloads, not upstream signatures.

The installer preserves custom configuration entries and only adds missing fixed instruments. If an existing entry with the same name has been modified, it reports an error instead of overwriting it. The SFZ player, three VSCO sample sets, and five fixed Surge factory profiles are installed by default; `--prepare-sfz` remains available for compatibility. To update pinned sound profiles, preserve and move aside the old configuration and profiles, explicitly generate a new configuration, and rerun the relevant acceptance checks. See [STAGE_ONE.md](docs/STAGE_ONE.md).

## CLI at a glance

See the [Agent quickstart](docs/AGENT_QUICKSTART.md) for a minimal workflow. The full score format is defined in [score-v1.json](src/music/schemas/score-v1.json) and explained in [SCORE.md](docs/SCORE.md).

| Command | Behavior |
|---|---|
| `music doctor --json` | Checks resource SHA-256 hashes, loads every configured instrument and renders offline probe notes, and checks FFmpeg, runtime availability, and permissions. |
| `music instruments --json` | Lists instrument sources, licenses, versions, paths, capabilities, and recorded verification status. Does not play instruments. |
| `music validate score.json --json` | Checks score schema, semantics, instrument references, and hashes. Does not load native backends. |
| `music render score.json --output outputs\new --dry-run --json` | Resolves resources and the output plan, rejecting an existing output directory. Creates no output. |
| `music render score.json --output outputs\new --json` | Renders offline, checks the result, and atomically publishes a new output directory. |
| `music inspect outputs\new --json` | Returns status, selected instrument fingerprints, and `report_path`. Succeeds only if the report passed, artifacts are intact, and the main audio passes a fresh check. |

Each subcommand accepts `--config PATH`. Otherwise, configuration comes from the `MUSIC_CONFIG` environment variable or `music.config.json` in the current working directory. Relative paths inside the configuration resolve against its containing directory. Paths may contain spaces and Chinese characters; quote them or use argument arrays when invoking a shell.

With `--json`, stdout contains exactly one JSON object with `version/tool_version/command/ok/data/error`. The current `version` is `3`; its schema is [cli-v3.json](src/music/schemas/cli-v3.json). Exit codes are `0` for success, `1` for failed `doctor` health checks, and `2` for input, render, or inspect errors. Failures include a stable error code, affected resource, cause, and next step. Inspect diagnostics remain in `data`; unchecked integrity and audio results are `null`, which does not mean they passed. Command help remains plain text. Successful validation only confirms parsing and resource checks; `doctor` and `render` actually invoke native instruments.

## Files, caches, and local data

| Path | Contents |
|---|---|
| `src/music/` | Scores, resources, backend adapters, rendering, audio checks, MIDI, and CLI. Schemas are installed with the package. |
| `music.config.json` | Local paths and SHA-256 hashes; ignored by Git and contains no secrets. |
| `resources/` | Portable plugins, samples, generated instrument states, and download manifests; ignored by Git. |
| `work/downloads/` | Cached archives of pinned versions; ignored by Git. |
| `.music/doctor/` | Probe requests, native logs, and intermediate audio. |
| `.music/logs/` | CLI errors and failed render directories, retaining reports and native logs. |
| `outputs/` | User output and acceptance artifacts; ignored by Git. The default output is `outputs/render`; an existing directory causes failure rather than being overwritten. |

When intermediate files are retained, `request.json` records the staging paths used during execution. After atomic publication, these requests serve as provenance; their old absolute paths cannot be replayed directly. Log and command-request paths in reports are mapped to the final artifact directory. When intermediates are disabled, backend `command/log` fields are `null` and `intermediates_retained=false`, so reports do not point to deleted files.

## Verification

Version 0.5.0 completed **81 CLI calls and 65 checks**; see the [instrument acceptance summary](docs/PALETTE_ACCEPTANCE.md). The full local artifacts were later removed to free disk space. Their removal does not invalidate the completed acceptance results. Documentation or package metadata changes do not require rerunning instrument acceptance; changes to rendering, backends, dependencies, or instruments require regression checks for the affected behavior.

When a full regression run is needed, use the following command. It generates substantial audio and log output.

```powershell
.\.venv\Scripts\python.exe scripts\acceptance.py
```

The script invokes the real CLI in fresh paths containing Chinese characters and spaces. It covers piano/Surge rendering, repeat-render comparisons, pitch edits affecting the intended stem, MIDI, invalid resources and scores, failed reports, and artifact checks. It probes each key of the three SFZ instruments and repeats across processes. The five factory electronic profiles are checked across pitch/velocity grids at two sample rates, including reproducibility. Complete orchestral and electronic scores are checked for stems and isolation of targeted edits. Both drum kits are probed on keys 36–61 and checked with actual rhythms, MIDI percussion channels, and repeated renders. Results are written to `outputs/acceptance-*/summary.json`.

Version 0.3.0 also covered instrument fingerprints, explicit omission of oversized metadata, snapshot semantics for failed/incomplete reports, rejection of empty or fully muted scores, main-WAV silence rechecks, rendering an individual track with no notes, and installation guidance for missing configuration. Existing v2 responses continue to follow their old schema; the newer response shapes require CLI v3 / inspect v2.

## Scope and licensing

Only Windows x64 and the 12 pinned instruments have been verified. The added instruments use the existing score fields and commands; try `examples/orchestra-sketch.json` and `examples/electronic-sketch.json`. The piano is by Alexander Holm, adapted by FreePats, under CC-BY-3.0. AVL drum kits use CC-BY-SA-3.0 with an exception for recorded music. Software dependencies have separate LGPL/GPL/AGPL terms. Instrument assets, plugins, and installer archives are excluded from Git. See [third-party notices](THIRD_PARTY_NOTICES.md) for sources, licenses, and the distinction between assets and rendered music, and [instrument documentation](docs/INSTRUMENTS.md) for capabilities.

Project-owned code, documentation, and original examples use the [MIT License](LICENSE). Third-party software, samples, and presets retain their own licenses. MIT does not permit unrestricted closed-source redistribution of the entire runtime containing GPL/AGPL components. See the [licensing notes](docs/LICENSING.md).

The [instrument documentation](docs/INSTRUMENTS.md) records limitations, original license sources, backend choices, and verified capabilities. SFZ uses synchronous offline sample loading to avoid dropped samples from real-time disk streaming during fast rendering. Only the five tested Surge factory profiles are admitted alongside the init instrument. BBC Discover is excluded because its vendor installation process has not been completed. Third-party plugins may crash or hang. Render subprocesses have timeouts and process isolation, but this is not a security sandbox for malicious plugins; arbitrary VST3 plugins are not guaranteed to render reliably offline.

## Contributing and reporting issues

See [CONTRIBUTING.md](CONTRIBUTING.md) for development setup, checks appropriate to each change, and issue-reporting requirements. Include the tool version, command, error code, and a minimal score in reports. Remove personal paths from logs first, and do not upload complete instrument libraries or download caches.
