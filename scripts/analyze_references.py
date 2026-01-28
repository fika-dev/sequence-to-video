#!/usr/bin/env python3
"""
Analyze downloaded Facebook Ads reference videos using Gemini.

Usage:
    python scripts/analyze_references.py assets/references
    python scripts/analyze_references.py assets/references -w 2 -v
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from infrastructure.config import load_config
from domains.library.reference_analyzer import ReferenceAdAnalyzer
from domains.library.reference_models import ReferenceAdAnalysis, ReferenceAdsIndex


def load_fb_metadata(ad_dir: Path) -> Optional[dict]:
    metadata_path = ad_dir / "metadata.json"
    if metadata_path.exists():
        with open(metadata_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def find_video_file(ad_dir: Path) -> Optional[Path]:
    for ext in [".mp4", ".mov", ".webm", ".mkv"]:
        video_file = ad_dir / f"video{ext}"
        if video_file.exists():
            return video_file
    return None


def analyze_single_ad(
    analyzer: ReferenceAdAnalyzer,
    ad_dir: Path,
    verbose: bool = False,
) -> Optional[ReferenceAdAnalysis]:
    ad_id = ad_dir.name
    video_path = find_video_file(ad_dir)

    if not video_path:
        if verbose:
            print(f"  [{ad_id}] No video file found, skipping")
        return None

    fb_metadata = load_fb_metadata(ad_dir)

    try:
        if verbose:
            print(f"  [{ad_id}] Analyzing...")

        analysis = analyzer.analyze_reference_ad(
            video_path=video_path,
            ad_id=ad_id,
            fb_metadata=fb_metadata,
            verbose=verbose,
        )

        analysis = analyzer.generate_embeddings(analysis)

        return analysis

    except Exception as e:
        if verbose:
            print(f"  [{ad_id}] Error: {e}")
        return None


def save_analysis(
    analysis: ReferenceAdAnalysis,
    output_dir: Path,
) -> None:
    ad_analysis_dir = output_dir / analysis.ad_id
    ad_analysis_dir.mkdir(parents=True, exist_ok=True)

    analysis_dict = analysis.model_dump(mode="json")
    analysis_dict["source_file"] = str(analysis.source_file)

    analysis_path = ad_analysis_dir / "analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis_dict, f, ensure_ascii=False, indent=2)

    if analysis.ad_fingerprint_embedding:
        fingerprint_path = ad_analysis_dir / "fingerprint.npy"
        np.save(fingerprint_path, np.array(analysis.ad_fingerprint_embedding))
        analysis.ad_fingerprint_embedding_path = str(fingerprint_path)

    for beat in analysis.beats:
        if beat.embedding:
            beat_emb_path = ad_analysis_dir / f"{beat.beat_id}.npy"
            np.save(beat_emb_path, np.array(beat.embedding))
            beat.embedding_path = str(beat_emb_path)


def main():
    parser = argparse.ArgumentParser(description="Analyze Facebook Ads reference videos")
    parser.add_argument("references_dir", type=Path, help="Directory with downloaded references")
    parser.add_argument("-o", "--output", type=Path, default=None, help="Output index directory")
    parser.add_argument("-w", "--workers", type=int, default=1, help="Parallel workers (default: 1)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--force", action="store_true", help="Re-analyze already analyzed ads")

    args = parser.parse_args()

    if not args.references_dir.exists():
        print(f"Error: References directory not found: {args.references_dir}")
        sys.exit(1)

    output_dir = args.output or Path("assets/reference_index")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config()
    analyzer = ReferenceAdAnalyzer(
        project=config.api.google_project_id,
        gcs_bucket=config.api.gcs_bucket,
    )

    ad_dirs = [
        d for d in args.references_dir.iterdir()
        if d.is_dir() and not d.name.startswith(".")
    ]

    if not args.force:
        ad_dirs = [
            d for d in ad_dirs
            if not (output_dir / d.name / "analysis.json").exists()
        ]

    print(f"Found {len(ad_dirs)} ads to analyze")

    if not ad_dirs:
        print("Nothing to analyze")
        return

    results: list[ReferenceAdAnalysis] = []
    failed: list[str] = []

    if args.workers == 1:
        for i, ad_dir in enumerate(ad_dirs, 1):
            print(f"[{i}/{len(ad_dirs)}] {ad_dir.name}")
            analysis = analyze_single_ad(analyzer, ad_dir, args.verbose)
            if analysis:
                save_analysis(analysis, output_dir)
                results.append(analysis)
                print(f"  -> {analysis.framework}, {len(analysis.beats)} beats")
            else:
                failed.append(ad_dir.name)
    else:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {
                executor.submit(analyze_single_ad, analyzer, ad_dir, args.verbose): ad_dir
                for ad_dir in ad_dirs
            }

            for i, future in enumerate(as_completed(futures), 1):
                ad_dir = futures[future]
                try:
                    analysis = future.result()
                    if analysis:
                        save_analysis(analysis, output_dir)
                        results.append(analysis)
                        print(f"[{i}/{len(ad_dirs)}] ✓ {analysis.ad_id}: {analysis.framework}")
                    else:
                        failed.append(ad_dir.name)
                        print(f"[{i}/{len(ad_dirs)}] ✗ {ad_dir.name}")
                except Exception as e:
                    failed.append(ad_dir.name)
                    print(f"[{i}/{len(ad_dirs)}] ✗ {ad_dir.name}: {e}")

    index = ReferenceAdsIndex(
        analyzed_at=datetime.now().isoformat(),
        ads=results,
    )

    index_path = output_dir / "index.json"
    index_dict = {
        "analyzed_at": index.analyzed_at,
        "total_ads": len(results),
        "ads": [a.ad_id for a in results],
    }
    with open(index_path, "w", encoding="utf-8") as f:
        json.dump(index_dict, f, ensure_ascii=False, indent=2)

    print(f"\nResults: {len(results)} success, {len(failed)} failed")
    print(f"Index saved to: {index_path}")

    if failed:
        failed_path = output_dir / "failed.txt"
        with open(failed_path, "w", encoding="utf-8") as f:
            f.write(f"# Failed analysis - {datetime.now().isoformat()}\n")
            for ad_id in failed:
                f.write(f"{ad_id}\n")
        print(f"Failed ads logged to: {failed_path}")

    if results:
        print("\n=== Analysis Summary ===")
        frameworks = {}
        for r in results:
            frameworks[r.framework] = frameworks.get(r.framework, 0) + 1

        print("Frameworks:")
        for fw, count in sorted(frameworks.items(), key=lambda x: -x[1]):
            print(f"  {fw}: {count}")

        avg_beats = sum(len(r.beats) for r in results) / len(results)
        avg_duration = sum(r.total_duration for r in results) / len(results)
        print(f"\nAvg beats per ad: {avg_beats:.1f}")
        print(f"Avg duration: {avg_duration:.1f}s")


if __name__ == "__main__":
    main()
