"""Check an installed wheel without downloading or playing instrument assets."""
from importlib import metadata, resources
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import tomllib

from jsonschema import Draft202012Validator
import music


ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def main():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    imported = Path(music.__file__).resolve()
    require(not imported.is_relative_to(ROOT / "src"),
            "Install the built wheel in a non-editable environment before checking the package.")
    package = metadata.metadata("code-to-music")
    require(package["Version"] == music.__version__ == project["version"], "Package version mismatch")
    require(package["Requires-Python"] == project["requires-python"], "Python metadata mismatch")
    require(package["License-Expression"] == project["license"], "License metadata mismatch")
    distribution = metadata.distribution("code-to-music")
    for name in project["license-files"]:
        matches = [path for path in distribution.files or []
                   if str(path).replace("\\", "/").endswith(".dist-info/licenses/" + name)]
        require(len(matches) == 1, f"Missing packaged license file: {name}")
        require(distribution.locate_file(matches[0]).read_bytes() == (ROOT / name).read_bytes(),
                f"Outdated packaged license file: {name}")
    require(package.get_payload().strip().replace("\r\n", "\n") ==
            (ROOT / "README.md").read_text(encoding="utf-8").strip(), "Packaged README mismatch")

    schemas = {}
    for path in sorted((ROOT / "src/music/schemas").glob("*.json")):
        content = resources.files("music").joinpath("schemas", path.name).read_text(encoding="utf-8")
        require(json.loads(content) == json.loads(path.read_text(encoding="utf-8")),
                f"Missing or outdated packaged schema: {path.name}")
        schemas[path.name] = json.loads(content)
        Draft202012Validator.check_schema(schemas[path.name])
    examples = sorted((ROOT / "examples").rglob("*.json"))
    require(bool(examples), "No examples found")
    for path in examples:
        Draft202012Validator(schemas["score-v1.json"]).validate(json.loads(path.read_text(encoding="utf-8")))

    # Exercise public CLI from another directory, with no developer config.
    base = ROOT / "work/package-check"
    base.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.pop("MUSIC_CONFIG", None)
    with tempfile.TemporaryDirectory(prefix="cli-", dir=base) as directory:
        def run(*args):
            return subprocess.run([sys.executable, "-m", "music", *args], cwd=directory,
                                  env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)

        version = run("--version")
        require(version.returncode == 0 and version.stdout.strip() == project["version"],
                f"Installed CLI failed: {version.stderr}")
        help_result = run("--help")
        require(help_result.returncode == 0 and "render" in help_result.stdout, "CLI help failed")
        failure = run("instruments", "--config", "missing-config.json", "--json")
        payload = json.loads(failure.stdout)
        Draft202012Validator(schemas["cli-v3.json"]).validate(payload)
        require(failure.returncode == 2 and payload["ok"] is False and
                payload["error"]["code"] == "E_CONFIG", "Missing-config contract failed")
        require("install_resources.py" in payload["error"]["fix"], "Installation guidance missing")

    print(json.dumps({"status": "passed", "version": music.__version__,
                      "schemas": len(schemas), "examples": len(examples),
                      "cli_checks": ["version", "help", "missing_config"],
                      "native_render_tested": False}))


if __name__ == "__main__":
    main()
