from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Literal, Optional

import numpy as np
from pydantic import BaseModel, Field, field_validator

SourceType = Literal["facebook", "youtube"]
ItemStatus = Literal["pending", "analyzed", "failed"]

DEFAULT_DOMAINS = {
    "ads": ["supplements", "cosmetics", "food", "etc"],
    "content": ["education", "medical", "entertainment"],
}


class ReferenceItem(BaseModel):
    reference_id: str
    source_type: SourceType
    source_id: str
    original_title: Optional[str] = None
    status: ItemStatus = "pending"
    analyzed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())

    @field_validator("reference_id")
    @classmethod
    def validate_reference_id(cls, v: str) -> str:
        if ":" not in v:
            raise ValueError("reference_id must contain ':'")
        prefix, suffix = v.split(":", 1)
        if not prefix:
            raise ValueError("reference_id prefix cannot be empty")
        if not suffix:
            raise ValueError("reference_id suffix cannot be empty")
        return v

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"facebook", "youtube"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}")
        return v


class Collection(BaseModel):
    id: str
    title: str
    domain: str
    source_type: SourceType
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    schema_version: str = "1.0"

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        allowed = {"facebook", "youtube"}
        if v not in allowed:
            raise ValueError(f"source_type must be one of {allowed}")
        return v

    def to_slug(self) -> str:
        slug = self.title.lower()
        slug = re.sub(r"[^\w\s가-힣-]", "", slug)
        slug = re.sub(r"\s+", "_", slug)
        return slug


class CollectionSummary(BaseModel):
    id: str
    title: str
    domain: str
    source_type: SourceType
    item_count: int = 0
    analyzed_count: int = 0
    gcs_synced: bool = False


class ReferenceIndex(BaseModel):
    schema_version: str = "1.0"
    collections: list[CollectionSummary] = Field(default_factory=list)
    domains: dict[str, list[str]] = Field(default_factory=lambda: DEFAULT_DOMAINS.copy())
    last_updated: str = Field(default_factory=lambda: datetime.now().isoformat())

    def find_collection_by_id(self, collection_id: str) -> Optional[CollectionSummary]:
        for col in self.collections:
            if col.id == collection_id:
                return col
        return None

    def find_collections_by_domain(self, pattern: str) -> list[CollectionSummary]:
        if pattern == "*":
            return list(self.collections)

        results = []
        for col in self.collections:
            if pattern.endswith("/*"):
                category = pattern[:-2]
                if col.domain.startswith(f"{category}/"):
                    results.append(col)
            elif col.domain == pattern:
                results.append(col)
        return results


class ReferenceStore:
    def __init__(self, base_dir: Path | str):
        self.base_dir = Path(base_dir)
        self.collections_dir = self.base_dir / "collections"
        self.index_path = self.base_dir / "index.json"
        self._ensure_structure()

    def _ensure_structure(self) -> None:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.collections_dir.mkdir(exist_ok=True)

        if not self.index_path.exists():
            self._save_index(ReferenceIndex())
        else:
            try:
                self._load_index()
            except (json.JSONDecodeError, Exception):
                self._save_index(ReferenceIndex())

    def _load_index(self) -> ReferenceIndex:
        with open(self.index_path, encoding="utf-8") as f:
            data = json.load(f)
        return ReferenceIndex.model_validate(data)

    def _save_index(self, index: ReferenceIndex) -> None:
        index.last_updated = datetime.now().isoformat()
        self._write_json_atomic(self.index_path, index.model_dump(mode="json"))

    def _write_json_atomic(self, path: Path, data: dict) -> None:
        tmp_path = path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp_path.replace(path)

    def _load_collection(self, collection_dir: Path) -> Optional[Collection]:
        collection_json = collection_dir / "collection.json"
        if not collection_json.exists():
            return None
        with open(collection_json, encoding="utf-8") as f:
            data = json.load(f)
        return Collection.model_validate(data)

    def _save_collection(self, collection: Collection, collection_dir: Path) -> None:
        self._write_json_atomic(
            collection_dir / "collection.json",
            collection.model_dump(mode="json"),
        )

    def _get_collection_dir_by_id(self, collection_id: str) -> Optional[Path]:
        for d in self.collections_dir.iterdir():
            if not d.is_dir():
                continue
            collection_json = d / "collection.json"
            if collection_json.exists():
                with open(collection_json, encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == collection_id:
                    return d
        return None

    def create_collection(
        self,
        title: str,
        domain: str,
        source_type: SourceType,
        tags: Optional[list[str]] = None,
    ) -> Collection:
        collection_id = f"col_{uuid.uuid4().hex[:12]}"
        collection = Collection(
            id=collection_id,
            title=title,
            domain=domain,
            source_type=source_type,
            tags=tags or [],
        )

        collection_dir = self.collections_dir / collection.to_slug()
        collection_dir.mkdir(parents=True, exist_ok=True)
        (collection_dir / "items").mkdir(exist_ok=True)

        self._save_collection(collection, collection_dir)

        index = self._load_index()
        index.collections.append(
            CollectionSummary(
                id=collection.id,
                title=collection.title,
                domain=collection.domain,
                source_type=collection.source_type,
                item_count=0,
                analyzed_count=0,
            )
        )
        self._save_index(index)

        return collection

    def get_collection(self, collection_id: str) -> Optional[Collection]:
        collection_dir = self._get_collection_dir_by_id(collection_id)
        if collection_dir is None:
            return None
        return self._load_collection(collection_dir)

    def list_collections(self, domain: Optional[str] = None) -> list[CollectionSummary]:
        index = self._load_index()
        if domain is None:
            return index.collections
        return index.find_collections_by_domain(domain)

    def delete_collection(self, collection_id: str) -> bool:
        collection_dir = self._get_collection_dir_by_id(collection_id)
        if collection_dir is None:
            return False

        shutil.rmtree(collection_dir)

        index = self._load_index()
        index.collections = [c for c in index.collections if c.id != collection_id]
        self._save_index(index)

        return True

    def get_collection_path(self, collection_id: str) -> Path:
        collection_dir = self._get_collection_dir_by_id(collection_id)
        if collection_dir is None:
            raise ValueError(f"Collection not found: {collection_id}")
        return collection_dir

    def _get_item_dir(self, collection_id: str, reference_id: str) -> Path:
        collection_dir = self.get_collection_path(collection_id)
        safe_ref_id = reference_id.replace(":", "_")
        return collection_dir / "items" / safe_ref_id

    def add_item(
        self,
        collection_id: str,
        source_id: str,
        original_title: Optional[str] = None,
    ) -> ReferenceItem:
        collection = self.get_collection(collection_id)
        if collection is None:
            raise ValueError(f"Collection not found: {collection_id}")

        source_prefix_map = {"facebook": "fb", "youtube": "yt"}
        source_prefix = source_prefix_map.get(collection.source_type, collection.source_type[:2])
        reference_id = f"{source_prefix}:{source_id}"

        existing = self.get_item(collection_id, reference_id)
        if existing is not None:
            raise ValueError(f"Item already exists: {reference_id}")

        item = ReferenceItem(
            reference_id=reference_id,
            source_type=collection.source_type,
            source_id=source_id,
            original_title=original_title,
            status="pending",
        )

        item_dir = self._get_item_dir(collection_id, reference_id)
        item_dir.mkdir(parents=True, exist_ok=True)

        self._write_json_atomic(
            item_dir / "item.json",
            item.model_dump(mode="json"),
        )

        self._update_collection_counts(collection_id)

        return item

    def get_item(self, collection_id: str, reference_id: str) -> Optional[ReferenceItem]:
        try:
            item_dir = self._get_item_dir(collection_id, reference_id)
        except ValueError:
            return None

        item_json = item_dir / "item.json"
        if not item_json.exists():
            return None

        with open(item_json, encoding="utf-8") as f:
            data = json.load(f)
        return ReferenceItem.model_validate(data)

    def list_items(self, collection_id: str) -> list[ReferenceItem]:
        try:
            collection_dir = self.get_collection_path(collection_id)
        except ValueError:
            return []

        items_dir = collection_dir / "items"
        if not items_dir.exists():
            return []

        items = []
        for item_dir in items_dir.iterdir():
            if not item_dir.is_dir():
                continue
            item_json = item_dir / "item.json"
            if item_json.exists():
                with open(item_json, encoding="utf-8") as f:
                    data = json.load(f)
                items.append(ReferenceItem.model_validate(data))
        return items

    def update_item_status(
        self,
        collection_id: str,
        reference_id: str,
        status: ItemStatus,
        analyzed_at: Optional[str] = None,
    ) -> ReferenceItem:
        item = self.get_item(collection_id, reference_id)
        if item is None:
            raise ValueError(f"Item not found: {reference_id}")

        item.status = status
        if analyzed_at:
            item.analyzed_at = analyzed_at

        item_dir = self._get_item_dir(collection_id, reference_id)
        self._write_json_atomic(
            item_dir / "item.json",
            item.model_dump(mode="json"),
        )

        self._update_collection_counts(collection_id)

        return item

    def _update_collection_counts(self, collection_id: str) -> None:
        items = self.list_items(collection_id)
        item_count = len(items)
        analyzed_count = sum(1 for i in items if i.status == "analyzed")

        index = self._load_index()
        for col in index.collections:
            if col.id == collection_id:
                col.item_count = item_count
                col.analyzed_count = analyzed_count
                break
        self._save_index(index)

    def get_item_path(self, collection_id: str, reference_id: str) -> Path:
        return self._get_item_dir(collection_id, reference_id)

    def get_video_path(self, collection_id: str, reference_id: str) -> Path:
        return self._get_item_dir(collection_id, reference_id) / "video.mp4"

    def get_analysis_path(self, collection_id: str, reference_id: str) -> Path:
        return self._get_item_dir(collection_id, reference_id) / "analysis.json"


@dataclass
class MigrationResult:
    success: bool
    collection_id: Optional[str] = None
    items_migrated: int = 0
    items_failed: int = 0
    errors: list[str] = None
    dry_run: bool = False

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class MigrationHelper:
    def __init__(
        self,
        legacy_refs_dir: Path,
        legacy_index_dir: Path,
        new_refs_dir: Path,
    ):
        self.legacy_refs_dir = Path(legacy_refs_dir)
        self.legacy_index_dir = Path(legacy_index_dir)
        self.new_refs_dir = Path(new_refs_dir)

    def needs_migration(self) -> bool:
        if not self.legacy_refs_dir.exists() or not self.legacy_index_dir.exists():
            return False

        legacy_items = [
            d for d in self.legacy_refs_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]
        if not legacy_items:
            return False

        has_videos = any(
            (d / "video.mp4").exists() or (d / "video.mov").exists()
            for d in legacy_items
        )

        return has_videos

    def migrate(self, dry_run: bool = False) -> MigrationResult:
        if not self.needs_migration():
            return MigrationResult(success=True, items_migrated=0, dry_run=dry_run)

        if dry_run:
            items = self._count_legacy_items()
            return MigrationResult(
                success=True,
                items_migrated=items,
                dry_run=True,
            )

        store = ReferenceStore(self.new_refs_dir)

        collection = store.create_collection(
            title="Legacy Facebook Ads",
            domain="ads/etc",
            source_type="facebook",
            tags=["legacy", "migrated"],
        )

        migrated = 0
        failed = 0
        errors = []

        for legacy_item_dir in self.legacy_refs_dir.iterdir():
            if not legacy_item_dir.is_dir() or legacy_item_dir.name.startswith("."):
                continue

            ad_id = legacy_item_dir.name

            try:
                video_path = self._find_video_file(legacy_item_dir)
                if video_path is None:
                    continue

                metadata = self._load_legacy_metadata(legacy_item_dir)
                original_title = metadata.get("title") if metadata else None

                item = store.add_item(
                    collection_id=collection.id,
                    source_id=ad_id,
                    original_title=original_title,
                )

                new_item_dir = store.get_item_path(collection.id, item.reference_id)

                shutil.copy2(video_path, new_item_dir / "video.mp4")

                thumb_path = legacy_item_dir / "thumbnail.jpg"
                if thumb_path.exists():
                    shutil.copy2(thumb_path, new_item_dir / "thumbnail.jpg")

                if metadata:
                    store._write_json_atomic(new_item_dir / "source_meta.json", metadata)

                legacy_analysis_dir = self.legacy_index_dir / ad_id
                if legacy_analysis_dir.exists():
                    analysis_json = legacy_analysis_dir / "analysis.json"
                    if analysis_json.exists():
                        shutil.copy2(analysis_json, new_item_dir / "analysis.json")

                    fingerprint_npy = legacy_analysis_dir / "fingerprint.npy"
                    if fingerprint_npy.exists():
                        shutil.copy2(fingerprint_npy, new_item_dir / "fingerprint.npy")

                    for beat_file in legacy_analysis_dir.glob("b*.npy"):
                        shutil.copy2(beat_file, new_item_dir / beat_file.name)

                    store.update_item_status(
                        collection.id,
                        item.reference_id,
                        status="analyzed",
                        analyzed_at=datetime.now().isoformat(),
                    )

                migrated += 1

            except Exception as e:
                failed += 1
                errors.append(f"{ad_id}: {str(e)}")

        return MigrationResult(
            success=failed == 0,
            collection_id=collection.id,
            items_migrated=migrated,
            items_failed=failed,
            errors=errors,
        )

    def _count_legacy_items(self) -> int:
        count = 0
        for d in self.legacy_refs_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                if self._find_video_file(d) is not None:
                    count += 1
        return count

    def _find_video_file(self, directory: Path) -> Optional[Path]:
        for ext in [".mp4", ".mov", ".webm", ".mkv"]:
            video_path = directory / f"video{ext}"
            if video_path.exists():
                return video_path
        return None

    def _load_legacy_metadata(self, directory: Path) -> Optional[dict]:
        metadata_path = directory / "metadata.json"
        if not metadata_path.exists():
            return None
        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)


@dataclass
class SyncResult:
    success: bool
    files_uploaded: int = 0
    files_failed: int = 0
    errors: Optional[list[str]] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class GCSSyncManager:
    def __init__(
        self,
        store: ReferenceStore,
        storage_client: Any = None,
        bucket_name: Optional[str] = None,
    ):
        self.store = store
        self.storage_client = storage_client
        self.bucket_name = bucket_name
        self.state_path = store.base_dir / ".gcs_state.json"

    def generate_manifest(self) -> dict:
        files = []

        for path in self.store.base_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.name.startswith(".gcs"):
                continue
            if path.suffix == ".tmp":
                continue

            rel_path = path.relative_to(self.store.base_dir)
            file_hash = self._compute_hash(path)
            file_size = path.stat().st_size

            files.append({
                "path": str(rel_path),
                "hash": file_hash,
                "size": file_size,
            })

        return {
            "generated_at": datetime.now().isoformat(),
            "base_dir": str(self.store.base_dir),
            "files": files,
        }

    def _compute_hash(self, path: Path) -> str:
        hasher = hashlib.md5()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def push(self) -> SyncResult:
        if self.storage_client is None or self.bucket_name is None:
            return SyncResult(success=False, errors=["Storage client not configured"])

        manifest = self.generate_manifest()
        uploaded = 0
        failed = 0
        errors = []

        bucket = self.storage_client.bucket(self.bucket_name)

        for file_info in manifest["files"]:
            local_path = self.store.base_dir / file_info["path"]
            blob_name = f"references/{file_info['path']}"

            try:
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(local_path))
                uploaded += 1
            except Exception as e:
                failed += 1
                errors.append(f"{file_info['path']}: {str(e)}")

        self._save_state({
            "last_sync": datetime.now().isoformat(),
            "manifest": manifest,
        })

        return SyncResult(
            success=failed == 0,
            files_uploaded=uploaded,
            files_failed=failed,
            errors=errors if errors else None,
        )

    def _save_state(self, state: dict) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    def _load_state(self) -> Optional[dict]:
        if not self.state_path.exists():
            return None
        with open(self.state_path, encoding="utf-8") as f:
            return json.load(f)

    def get_last_sync_time(self, collection_id: Optional[str] = None) -> Optional[str]:
        state = self._load_state()
        if state is None:
            return None
        return state.get("last_sync")

    def has_local_changes(self, collection_id: str) -> bool:
        state = self._load_state()
        if state is None:
            return True

        last_sync = state.get("last_sync")
        if last_sync is None:
            return True

        last_sync_time = datetime.fromisoformat(last_sync)

        try:
            collection_dir = self.store.get_collection_path(collection_id)
        except ValueError:
            return False

        for path in collection_dir.rglob("*"):
            if path.is_file():
                mtime = datetime.fromtimestamp(path.stat().st_mtime)
                if mtime > last_sync_time:
                    return True

        return False


class ReferenceRepositoryAdapter:
    def __init__(self, store: ReferenceStore, project: Optional[str] = None):
        self.store = store
        self.project = project
        self._analyses: list[Any] = []
        self._load_analyses()

    def _load_analyses(self) -> None:
        from domains.library.reference_models import (
            ReferenceAdAnalysis,
            ReferenceAdBeat,
            ReferenceAdPacing,
            ReferenceAdStyleGuide,
        )

        self._analyses = []

        for col_summary in self.store.list_collections():
            for item in self.store.list_items(col_summary.id):
                if item.status != "analyzed":
                    continue

                item_dir = self.store.get_item_path(col_summary.id, item.reference_id)
                analysis_path = item_dir / "analysis.json"

                if not analysis_path.exists():
                    continue

                with open(analysis_path, encoding="utf-8") as f:
                    data = json.load(f)

                pacing_data = data.get("pacing", {})
                pacing = ReferenceAdPacing(**pacing_data) if pacing_data else ReferenceAdPacing()

                style_data = data.get("style_guide", {})
                style_guide = ReferenceAdStyleGuide(**style_data) if style_data else ReferenceAdStyleGuide()

                beats = [ReferenceAdBeat(**b) for b in data.get("beats", [])]

                analysis = ReferenceAdAnalysis(
                    ad_id=data.get("ad_id", item.source_id),
                    source_file=Path(data.get("source_file", str(item_dir / "video.mp4"))),
                    analyzed_at=data.get("analyzed_at", item.analyzed_at or ""),
                    total_duration=data.get("total_duration", 0),
                    raw_response=data.get("raw_response"),
                    platform=data.get("platform", "facebook"),
                    locale=data.get("locale"),
                    product_category=data.get("product_category"),
                    brand_or_product_guess=data.get("brand_or_product_guess"),
                    framework=data.get("framework", "other"),
                    one_sentence_positioning=data.get("one_sentence_positioning", ""),
                    target_audience=data.get("target_audience"),
                    core_pain_point=data.get("core_pain_point"),
                    core_promise=data.get("core_promise"),
                    pacing=pacing,
                    beats=beats,
                    ctas=data.get("ctas", []),
                    offers=data.get("offers", []),
                    reusable_patterns=data.get("reusable_patterns", []),
                    style_guide=style_guide,
                    fb_metadata=data.get("fb_metadata"),
                )

                fingerprint_path = item_dir / "fingerprint.npy"
                if fingerprint_path.exists():
                    analysis.ad_fingerprint_embedding = np.load(fingerprint_path).tolist()

                for beat in analysis.beats:
                    beat_path = item_dir / f"{beat.beat_id}.npy"
                    if beat_path.exists():
                        beat.embedding = np.load(beat_path).tolist()

                self._analyses.append(analysis)

    def get_all_analyses(self) -> list[Any]:
        return self._analyses

    def find_similar_references(
        self,
        query: str,
        max_results: int = 5,
        product_category: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> list[Any]:
        filtered = []
        for analysis in self._analyses:
            if product_category and analysis.product_category != product_category:
                continue
            if framework and analysis.framework != framework:
                continue
            filtered.append(analysis)

        return filtered[:max_results]
