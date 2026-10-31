import hashlib
import json
import logging
import os
from collections.abc import Iterable

logger = logging.getLogger(__name__)


def build_upload_signature(files: Iterable[tuple[str, bytes]]) -> list[dict[str, str]]:
    """Build stable per-file signatures from names and contents."""
    signature = []
    for name, content in files:
        content_hash = hashlib.sha256(content).hexdigest()
        file_key = hashlib.sha256(f"{name}\0{content_hash}".encode()).hexdigest()
        signature.append({
            "key": file_key,
            "name": name,
            "sha256": content_hash,
        })
    return sorted(signature, key=lambda item: (item["name"].casefold(), item["key"]))


def load_index_manifest(path: str) -> dict:
    try:
        with open(path, "r", encoding="utf-8") as manifest_file:
            manifest = json.load(manifest_file)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        logger.warning("Could not read the file index manifest at %s.", path, exc_info=True)
        return {}

    return manifest if isinstance(manifest, dict) else {}


def save_index_manifest(path: str, items: list[dict]) -> None:
    """Persist per-file collection and chat metadata atomically."""
    temporary_path = f"{path}.tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as manifest_file:
            json.dump(
                {"items": items},
                manifest_file,
                indent=2,
            )
        os.replace(temporary_path, path)
    except OSError:
        try:
            os.remove(temporary_path)
        except FileNotFoundError:
            pass
        logger.exception("Could not save the file index manifest at %s.", path)
        raise
