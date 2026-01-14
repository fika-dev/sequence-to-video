import json
from datetime import datetime
from pathlib import Path
from typing import Any


class MetadataManager:
    def __init__(self, metadata_dir: Path | None = None):
        self.metadata_dir = Path(metadata_dir) if metadata_dir else Path("assets/generated/.metadata")
        self.metadata_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        asset_type: str,
        asset_path: Path,
        prompt: str,
        params: dict[str, Any] | None = None,
    ) -> None:
        metadata = {
            "asset_type": asset_type,
            "asset_path": str(asset_path),
            "prompt": prompt,
            "params": params or {},
            "created_at": datetime.now().isoformat(),
        }

        metadata_filename = f"{asset_path.stem}.json"
        metadata_path = self.metadata_dir / asset_type / metadata_filename
        metadata_path.parent.mkdir(parents=True, exist_ok=True)

        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)

    def get(self, asset_type: str, asset_path: Path) -> dict | None:
        metadata_filename = f"{asset_path.stem}.json"
        metadata_path = self.metadata_dir / asset_type / metadata_filename

        if not metadata_path.exists():
            return None

        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)

    def list_all(self, asset_type: str | None = None) -> list[dict]:
        results = []

        if asset_type:
            type_dir = self.metadata_dir / asset_type
            if type_dir.exists():
                for meta_file in type_dir.glob("*.json"):
                    with open(meta_file, encoding="utf-8") as f:
                        results.append(json.load(f))
        else:
            for type_dir in self.metadata_dir.iterdir():
                if type_dir.is_dir():
                    for meta_file in type_dir.glob("*.json"):
                        with open(meta_file, encoding="utf-8") as f:
                            results.append(json.load(f))

        return results
