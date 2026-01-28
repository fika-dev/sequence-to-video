#!/usr/bin/env python3
"""
Migrate legacy reference ads structure to new collection-based system.

Legacy structure:
  assets/references/{ad_id}/
    - video.mp4
    - thumbnail.jpg
    - metadata.json
  assets/reference_index/{ad_id}/
    - analysis.json
    - fingerprint.npy
    - b01.npy, b02.npy, ...

New structure:
  assets/references/
    - index.json
    - collections/{slug}/
      - collection.json
      - source_links.txt
      - items/fb_{ad_id}/
        - item.json
        - video.mp4
        - thumbnail.jpg
        - source_meta.json (renamed from metadata.json)
        - analysis.json
        - fingerprint.npy
        - b01.npy, ...

Usage:
  # Dry run (show what would be done)
  uv run python scripts/migrate_references.py --dry-run -v

  # Backup to GCS first, then migrate
  uv run python scripts/migrate_references.py --backup-to-gcs -v

  # Just migrate (no backup)
  uv run python scripts/migrate_references.py -v

  # Custom collection name
  uv run python scripts/migrate_references.py --title "FB Ads 2026-01" --domain "ads/supplements" -v
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.config import load_config


def backup_to_gcs(
    refs_dir: Path,
    index_dir: Path,
    bucket_name: str,
    project_id: str,
    verbose: bool = False,
) -> bool:
    from google.cloud import storage

    if verbose:
        print(f"Backing up to GCS bucket: {bucket_name}")

    try:
        client = storage.Client(project=project_id)
        bucket = client.bucket(bucket_name)
    except Exception as e:
        print(f"Error: Could not connect to GCS: {e}")
        return False

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_prefix = f"reference_backup/{timestamp}"

    uploaded = 0
    failed = 0

    for source_dir, label in [(refs_dir, "references"), (index_dir, "reference_index")]:
        if not source_dir.exists():
            continue

        for file_path in source_dir.rglob("*"):
            if file_path.is_dir():
                continue
            if file_path.name.startswith("."):
                continue

            rel_path = file_path.relative_to(source_dir.parent)
            blob_name = f"{backup_prefix}/{rel_path}"

            try:
                blob = bucket.blob(blob_name)
                blob.upload_from_filename(str(file_path))
                uploaded += 1
                if verbose:
                    print(f"  [UPLOAD] {rel_path}")
            except Exception as e:
                failed += 1
                if verbose:
                    print(f"  [FAIL] {rel_path}: {e}")

    print(f"Backup complete: {uploaded} files uploaded, {failed} failed")
    print(f"Backup location: gs://{bucket_name}/{backup_prefix}/")
    return failed == 0


def discover_legacy_ads(refs_dir: Path, index_dir: Path) -> list[dict[str, Any]]:
    ads = []

    refs_ads = set()
    if refs_dir.exists():
        for d in refs_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                refs_ads.add(d.name)

    index_ads = set()
    if index_dir.exists():
        for d in index_dir.iterdir():
            if d.is_dir() and d.name.isdigit():
                index_ads.add(d.name)

    all_ad_ids = refs_ads | index_ads

    for ad_id in sorted(all_ad_ids):
        ad_info: dict[str, Any] = {
            "ad_id": ad_id,
            "has_video": False,
            "has_thumbnail": False,
            "has_metadata": False,
            "has_analysis": False,
            "has_fingerprint": False,
            "beat_count": 0,
            "original_title": None,
        }

        refs_path = refs_dir / ad_id
        if refs_path.exists():
            ad_info["has_video"] = (refs_path / "video.mp4").exists()
            ad_info["has_thumbnail"] = any(
                (refs_path / f"thumbnail{ext}").exists()
                for ext in [".jpg", ".jpeg", ".png", ".webp"]
            )
            metadata_path = refs_path / "metadata.json"
            ad_info["has_metadata"] = metadata_path.exists()
            if metadata_path.exists():
                try:
                    with open(metadata_path, encoding="utf-8") as f:
                        meta = json.load(f)
                    ad_info["original_title"] = meta.get("title")
                except Exception:
                    pass

        index_path = index_dir / ad_id
        if index_path.exists():
            ad_info["has_analysis"] = (index_path / "analysis.json").exists()
            ad_info["has_fingerprint"] = (index_path / "fingerprint.npy").exists()
            beat_files = list(index_path.glob("b*.npy"))
            ad_info["beat_count"] = len(beat_files)

        ads.append(ad_info)

    return ads


def migrate_ads(
    refs_dir: Path,
    index_dir: Path,
    output_dir: Path,
    collection_title: str,
    collection_domain: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    import re
    import uuid

    result = {
        "success": True,
        "collection_id": None,
        "items_migrated": 0,
        "items_skipped": 0,
        "items_failed": 0,
        "errors": [],
    }

    ads = discover_legacy_ads(refs_dir, index_dir)
    if not ads:
        print("No legacy ads found to migrate")
        return result

    if verbose:
        print(f"Found {len(ads)} legacy ads to migrate")
        analyzed = sum(1 for a in ads if a["has_analysis"])
        print(f"  - {analyzed} with analysis")
        print(f"  - {len(ads) - analyzed} pending analysis")

    collection_id = f"col_{uuid.uuid4().hex[:12]}"
    result["collection_id"] = collection_id

    slug = collection_title.lower()
    slug = re.sub(r"[^\w\s가-힣-]", "", slug)
    slug = re.sub(r"\s+", "_", slug)

    collection_dir = output_dir / "collections" / slug
    items_dir = collection_dir / "items"

    if verbose:
        print(f"\nMigrating to: {collection_dir}")

    if dry_run:
        print("\n[DRY RUN] Would create:")
        print(f"  - {output_dir / 'index.json'}")
        print(f"  - {collection_dir / 'collection.json'}")
        print(f"  - {collection_dir / 'source_links.txt'}")
        for ad in ads:
            item_dir = items_dir / f"fb_{ad['ad_id']}"
            print(f"  - {item_dir}/")
            if ad["has_video"]:
                print(f"    - video.mp4")
            if ad["has_thumbnail"]:
                print(f"    - thumbnail.*")
            if ad["has_metadata"]:
                print(f"    - source_meta.json")
            if ad["has_analysis"]:
                print(f"    - analysis.json")
            if ad["has_fingerprint"]:
                print(f"    - fingerprint.npy")
            if ad["beat_count"] > 0:
                print(f"    - b01.npy ... b{ad['beat_count']:02d}.npy")
            print(f"    - item.json")
        result["items_migrated"] = len(ads)
        return result

    output_dir.mkdir(parents=True, exist_ok=True)
    collection_dir.mkdir(parents=True, exist_ok=True)
    items_dir.mkdir(parents=True, exist_ok=True)

    collection_data = {
        "id": collection_id,
        "title": collection_title,
        "domain": collection_domain,
        "source_type": "facebook",
        "tags": ["migrated", "legacy"],
        "created_at": datetime.now().isoformat(),
        "schema_version": "1.0",
    }
    with open(collection_dir / "collection.json", "w", encoding="utf-8") as f:
        json.dump(collection_data, f, ensure_ascii=False, indent=2)

    source_links = []
    for ad in ads:
        source_links.append(f"https://www.facebook.com/ads/library/?id={ad['ad_id']}")
    with open(collection_dir / "source_links.txt", "w", encoding="utf-8") as f:
        f.write("# Migrated from legacy structure\n")
        for link in source_links:
            f.write(f"{link}\n")

    collection_summary = {
        "id": collection_id,
        "title": collection_title,
        "domain": collection_domain,
        "source_type": "facebook",
        "item_count": 0,
        "analyzed_count": 0,
        "gcs_synced": False,
    }

    for ad in ads:
        ad_id = ad["ad_id"]
        reference_id = f"fb:{ad_id}"
        item_dir = items_dir / f"fb_{ad_id}"

        try:
            item_dir.mkdir(parents=True, exist_ok=True)

            refs_path = refs_dir / ad_id
            index_path = index_dir / ad_id

            if refs_path.exists():
                video_src = refs_path / "video.mp4"
                if video_src.exists():
                    shutil.copy2(video_src, item_dir / "video.mp4")

                for ext in [".jpg", ".jpeg", ".png", ".webp"]:
                    thumb_src = refs_path / f"thumbnail{ext}"
                    if thumb_src.exists():
                        shutil.copy2(thumb_src, item_dir / f"thumbnail{ext}")
                        break

                meta_src = refs_path / "metadata.json"
                if meta_src.exists():
                    shutil.copy2(meta_src, item_dir / "source_meta.json")

            if index_path.exists():
                analysis_src = index_path / "analysis.json"
                if analysis_src.exists():
                    shutil.copy2(analysis_src, item_dir / "analysis.json")

                fingerprint_src = index_path / "fingerprint.npy"
                if fingerprint_src.exists():
                    shutil.copy2(fingerprint_src, item_dir / "fingerprint.npy")

                for beat_file in index_path.glob("b*.npy"):
                    shutil.copy2(beat_file, item_dir / beat_file.name)

            status = "analyzed" if ad["has_analysis"] else "pending"
            item_data = {
                "reference_id": reference_id,
                "source_type": "facebook",
                "source_id": ad_id,
                "original_title": ad["original_title"],
                "status": status,
                "analyzed_at": datetime.now().isoformat() if ad["has_analysis"] else None,
                "created_at": datetime.now().isoformat(),
            }
            with open(item_dir / "item.json", "w", encoding="utf-8") as f:
                json.dump(item_data, f, ensure_ascii=False, indent=2)

            collection_summary["item_count"] += 1
            if ad["has_analysis"]:
                collection_summary["analyzed_count"] += 1

            result["items_migrated"] += 1
            if verbose:
                print(f"  [OK] {reference_id} ({ad['original_title'][:30] if ad['original_title'] else 'untitled'}...)")

        except Exception as e:
            result["items_failed"] += 1
            result["errors"].append(f"{ad_id}: {e}")
            if verbose:
                print(f"  [FAIL] {ad_id}: {e}")

    index_data = {
        "schema_version": "1.0",
        "collections": [collection_summary],
        "domains": {
            "ads": ["supplements", "cosmetics", "food", "etc"],
            "content": ["education", "medical", "entertainment"],
        },
        "last_updated": datetime.now().isoformat(),
    }
    with open(output_dir / "index.json", "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)

    if result["items_failed"] > 0:
        result["success"] = False

    return result


def main():
    parser = argparse.ArgumentParser(
        description="Migrate legacy reference ads to new collection-based structure"
    )
    parser.add_argument(
        "--refs-dir",
        default="assets/references",
        help="Legacy references directory (default: assets/references)",
    )
    parser.add_argument(
        "--index-dir",
        default="assets/reference_index",
        help="Legacy index directory (default: assets/reference_index)",
    )
    parser.add_argument(
        "--output-dir",
        default="assets/references_new",
        help="Output directory for new structure (default: assets/references_new)",
    )
    parser.add_argument(
        "--title",
        default="Legacy Facebook Ads",
        help="Collection title (default: 'Legacy Facebook Ads')",
    )
    parser.add_argument(
        "--domain",
        default="ads/supplements",
        help="Collection domain (default: 'ads/supplements')",
    )
    parser.add_argument(
        "--backup-to-gcs",
        action="store_true",
        help="Backup to GCS before migrating",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace assets/references with new structure after migration",
    )

    args = parser.parse_args()

    refs_dir = Path(args.refs_dir)
    index_dir = Path(args.index_dir)
    output_dir = Path(args.output_dir)

    if not refs_dir.exists() and not index_dir.exists():
        print("Error: No legacy data found")
        print(f"  Checked: {refs_dir}")
        print(f"  Checked: {index_dir}")
        sys.exit(1)

    ads = discover_legacy_ads(refs_dir, index_dir)
    print(f"Discovered {len(ads)} legacy reference ads")

    if args.backup_to_gcs and not args.dry_run:
        config = load_config()
        if not config.api.gcs_bucket:
            print("Error: GCS_BUCKET not configured in .env")
            sys.exit(1)

        success = backup_to_gcs(
            refs_dir=refs_dir,
            index_dir=index_dir,
            bucket_name=config.api.gcs_bucket,
            project_id=config.api.google_project_id,
            verbose=args.verbose,
        )
        if not success:
            print("Backup failed. Aborting migration.")
            sys.exit(1)
        print()

    result = migrate_ads(
        refs_dir=refs_dir,
        index_dir=index_dir,
        output_dir=output_dir,
        collection_title=args.title,
        collection_domain=args.domain,
        dry_run=args.dry_run,
        verbose=args.verbose,
    )

    if args.dry_run:
        print(f"\n[DRY RUN] Would migrate {result['items_migrated']} items")
        return

    print(f"\nMigration complete!")
    print(f"  Collection: {result['collection_id']}")
    print(f"  Items migrated: {result['items_migrated']}")
    print(f"  Items failed: {result['items_failed']}")
    print(f"  Output: {output_dir}")

    if result["errors"]:
        print(f"\nErrors:")
        for error in result["errors"][:10]:
            print(f"  - {error}")

    if args.replace and result["success"]:
        print(f"\nReplacing {refs_dir} with new structure...")
        backup_dir = refs_dir.parent / f"{refs_dir.name}.bak"
        if backup_dir.exists():
            shutil.rmtree(backup_dir)
        shutil.move(refs_dir, backup_dir)
        shutil.move(output_dir, refs_dir)
        print(f"  Old structure backed up to: {backup_dir}")
        print(f"  New structure now at: {refs_dir}")
        print(f"\nTo clean up old data:")
        print(f"  rm -rf {backup_dir} {index_dir}")
    else:
        print(f"\nNext steps:")
        print(f"  1. Verify new structure: ls {output_dir}/collections/")
        print(f"  2. If OK, replace old:")
        print(f"     mv {refs_dir} {refs_dir}.bak")
        print(f"     mv {output_dir} {refs_dir}")
        print(f"  3. Clean up:")
        print(f"     rm -rf {refs_dir}.bak {index_dir}")


if __name__ == "__main__":
    main()
