#!/usr/bin/env python3
"""Test footage selection for a single scene."""

import argparse
import json
from pathlib import Path

from domains.library.repository import AssetRepository
from domains.library.selector import FootageSelector
from infrastructure.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Test footage selection for a scene")
    parser.add_argument("--audio", "-a", required=True, help="Audio/narration text for the scene")
    parser.add_argument("--visual", "-p", default="", help="Visual prompt/description")
    parser.add_argument("--tags", "-t", nargs="*", default=[], help="Query tags")
    parser.add_argument("--duration", "-d", type=float, default=3.0, help="Minimum duration (seconds)")
    parser.add_argument("--env", help="Path to .env file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()

    config = load_config(args.env)

    asset_repo = AssetRepository(
        raw_footage_dir=config.paths.raw_footage,
        index_dir=config.paths.library_index,
    )

    all_clips = asset_repo.get_all_clips()
    if not all_clips:
        print("No indexed clips found. Run 'main.py index' first.")
        return

    print(f"\n=== Available Clips ({len(all_clips)}) ===")
    for clip in all_clips:
        print(f"  [{clip.clip_id}] {clip.duration:.1f}s - {clip.description[:60]}...")

    if args.tags:
        candidates = asset_repo.find_clips(args.tags, min_duration=0, max_results=20)
        print(f"\n=== Filtered by tags {args.tags} ({len(candidates)}) ===")
        for clip in candidates:
            print(f"  [{clip.clip_id}] {clip.duration:.1f}s - {clip.description[:60]}...")
    else:
        candidates = all_clips

    print(f"\n=== Scene Requirements ===")
    print(f"  Audio: {args.audio}")
    print(f"  Visual: {args.visual or '(none)'}")
    print(f"  Tags: {args.tags or '(none)'}")
    print(f"  Min Duration: {args.duration}s")

    print(f"\n=== Running LLM Selection ===")
    selector = FootageSelector(
        project=config.api.google_project_id,
        location="global",
    )

    selected = selector.select_clip(
        clips=candidates,
        audio_text=args.audio,
        visual_prompt=args.visual,
        query_tags=args.tags,
        min_duration=args.duration,
        verbose=True,
    )

    print(f"\n=== Result ===")
    if selected:
        print(f"  Selected: {selected.clip_id}")
        print(f"  Duration: {selected.duration:.1f}s")
        print(f"  Source: {selected.source_file}")
        print(f"  Time: {selected.start_time:.1f}s - {selected.end_time:.1f}s")
        print(f"  Description: {selected.description}")
        if selected.appeal_point:
            print(f"  Appeal: {selected.appeal_point}")
        if selected.content_type:
            print(f"  Type: {selected.content_type}")
    else:
        print("  No suitable clip found")


if __name__ == "__main__":
    main()
