"""On-disk response cache keyed on (provider, model, prompt, system, settings)."""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .adapters.base import Settings


def cache_key(provider: str, model: str, prompt: str, system: str | None, settings: Settings) -> str:
    blob = json.dumps(
        {"provider": provider, "model": model, "prompt": prompt, "system": system,
         "settings": asdict(settings)},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"),
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class ResponseCache:
    def __init__(self, root: Path):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / key[:2] / f"{key}.json"

    def get(self, key: str) -> str | None:
        try:
            return json.loads(self._path(key).read_text(encoding="utf-8"))["response"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            return None

    def put(self, key: str, response: str, **meta) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        record = {"response": response, "created": datetime.now(timezone.utc).isoformat(), **meta}
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False)
            os.replace(tmp, path)  # atomic: never leaves a half-written entry
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
