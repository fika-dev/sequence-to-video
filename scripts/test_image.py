#!/usr/bin/env python3
"""Image Generator 개별 테스트 스크립트"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.image_generator import ImageGenerator
from infrastructure.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Test image generation")
    parser.add_argument("prompt", help="Image generation prompt")
    parser.add_argument("-W", "--width", type=int, default=720, help="Image width")
    parser.add_argument("-H", "--height", type=int, default=1280, help="Image height")
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("--context", default="", help="Context for generation")
    parser.add_argument("--env", help="Path to .env file")

    args = parser.parse_args()

    config = load_config(args.env)

    image_gen = ImageGenerator(
        project=config.api.google_project_id,
        location="global",
        context=args.context,
    )

    print(f"Generating image...")
    print(f"  Prompt: {args.prompt[:80]}{'...' if len(args.prompt) > 80 else ''}")
    print(f"  Size: {args.width}x{args.height}")
    if args.context:
        print(f"  Context: {args.context}")

    asset = image_gen.generate(
        prompt=args.prompt,
        width=args.width,
        height=args.height,
        output_filename=args.output,
    )

    print(f"\nGenerated: {asset.file_path}")
    print(f"  Actual size: {asset.width}x{asset.height}")


if __name__ == "__main__":
    main()
