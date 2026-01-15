#!/usr/bin/env python3
"""Video Generator 개별 테스트 스크립트"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.video_generator import VideoGenerator
from infrastructure.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Test video generation (Veo 3.1)")
    parser.add_argument("prompt", help="Video generation prompt")
    parser.add_argument("-d", "--duration", type=int, default=5, help="Duration in seconds (max 8)")
    parser.add_argument("-W", "--width", type=int, default=720, help="Video width")
    parser.add_argument("-H", "--height", type=int, default=1280, help="Video height")
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("--env", help="Path to .env file")

    args = parser.parse_args()

    config = load_config(args.env)

    if not config.api.gcs_bucket:
        print("Error: GCS_BUCKET environment variable is required for Vertex AI video generation")
        sys.exit(1)

    video_gen = VideoGenerator(
        project=config.api.google_project_id,
        location="us-central1",
        gcs_bucket=config.api.gcs_bucket,
    )

    print(f"Generating video with Veo 3.1...")
    print(f"  Prompt: {args.prompt[:80]}{'...' if len(args.prompt) > 80 else ''}")
    print(f"  Duration: {args.duration}s")
    print(f"  Size: {args.width}x{args.height}")
    print(f"  (This may take several minutes...)")

    asset = video_gen.generate(
        prompt=args.prompt,
        width=args.width,
        height=args.height,
        duration=min(args.duration, 8),
        output_filename=args.output,
    )

    print(f"\nGenerated: {asset.file_path}")
    print(f"  Duration: {asset.duration}s")


if __name__ == "__main__":
    main()
