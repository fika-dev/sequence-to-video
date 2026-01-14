import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


class AssetCache:
    def __init__(self, cache_dir: Path | None = None):
        self.cache_dir = Path(cache_dir) if cache_dir else Path(".cache/assets")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.cache_dir / "cache_index.json"
        self._index = self._load_index()

    def _load_index(self) -> dict:
        if self.index_file.exists():
            return json.loads(self.index_file.read_text())
        return {}

    def _save_index(self) -> None:
        self.index_file.write_text(json.dumps(self._index, indent=2))

    def _compute_hash(self, params: dict[str, Any]) -> str:
        serialized = json.dumps(params, sort_keys=True)
        return hashlib.sha256(serialized.encode()).hexdigest()[:16]

    def get(self, cache_type: str, params: dict[str, Any]) -> Path | None:
        cache_key = f"{cache_type}_{self._compute_hash(params)}"
        entry = self._index.get(cache_key)

        if entry is None:
            return None

        cached_path = Path(entry["path"])
        if not cached_path.exists():
            del self._index[cache_key]
            self._save_index()
            return None

        return cached_path

    def put(
        self,
        cache_type: str,
        params: dict[str, Any],
        source_path: Path,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        cache_key = f"{cache_type}_{self._compute_hash(params)}"
        suffix = source_path.suffix
        cached_path = self.cache_dir / f"{cache_key}{suffix}"

        shutil.copy2(source_path, cached_path)

        self._index[cache_key] = {
            "path": str(cached_path),
            "params": params,
            "metadata": metadata or {},
        }
        self._save_index()

        return cached_path

    def get_metadata(self, cache_type: str, params: dict[str, Any]) -> dict[str, Any] | None:
        cache_key = f"{cache_type}_{self._compute_hash(params)}"
        entry = self._index.get(cache_key)
        if entry:
            return entry.get("metadata")
        return None

    def clear(self) -> None:
        for file in self.cache_dir.iterdir():
            if file.is_file():
                file.unlink()
        self._index = {}
        self._save_index()

    def clear_type(self, cache_type: str) -> None:
        keys_to_delete = [k for k in self._index if k.startswith(f"{cache_type}_")]
        for key in keys_to_delete:
            entry = self._index.pop(key, None)
            if entry:
                path = Path(entry["path"])
                if path.exists():
                    path.unlink()
        self._save_index()
