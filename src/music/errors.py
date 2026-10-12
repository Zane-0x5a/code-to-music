from dataclasses import dataclass
from pathlib import Path
import hashlib
import json


@dataclass
class MusicError(Exception):
    code: str
    message: str
    resource: str
    fix: str
    data: dict | None = None

    def as_dict(self) -> dict:
        return dict(code=self.code, message=self.message, resource=self.resource, fix=self.fix)


def read_json(path: Path) -> dict:
    try:
        def reject_constant(value: str):
            raise ValueError(f"Non-finite JSON value: {value}")
        def unique_pairs(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"Duplicate JSON key: {key}")
                result[key] = value
            return result
        return json.loads(path.read_text(encoding="utf-8-sig"),
                          parse_constant=reject_constant, object_pairs_hook=unique_pairs)
    except (OSError, ValueError) as exc:
        raise MusicError("E_INPUT", str(exc), str(path), "Create readable UTF-8 JSON with unique keys.") from exc


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def fingerprint(path: Path) -> str:
    if path.is_file():
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        if item.is_file():
            digest.update(item.relative_to(path).as_posix().encode("utf-8") + b"\0")
            digest.update(bytes.fromhex(fingerprint(item)))
    return digest.hexdigest()
