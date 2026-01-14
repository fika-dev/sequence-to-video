#!/usr/bin/env python3
"""Text Overlay Generator 개별 테스트 스크립트"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.text_renderer import TextAnimationRenderer, TEXT_STYLES, ANIMATION_CSS


def main():
    parser = argparse.ArgumentParser(description="Test text overlay generation")
    parser.add_argument("text", help="Text to render")
    parser.add_argument("-d", "--duration", type=float, default=3.0, help="Duration in seconds")
    parser.add_argument("-W", "--width", type=int, default=720, help="Video width")
    parser.add_argument("-H", "--height", type=int, default=1280, help="Video height")
    parser.add_argument(
        "-s", "--style",
        default="bold_impact_white",
        choices=list(TEXT_STYLES.keys()),
        help="Text style",
    )
    parser.add_argument(
        "-a", "--animation",
        default="fade_in",
        choices=list(ANIMATION_CSS.keys()),
        help="Animation type",
    )
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("--list-styles", action="store_true", help="List available styles")
    parser.add_argument("--list-animations", action="store_true", help="List available animations")

    args = parser.parse_args()

    if args.list_styles:
        print("Available text styles:")
        for style_id in TEXT_STYLES.keys():
            print(f"  {style_id}")
        return

    if args.list_animations:
        print("Available animations:")
        for anim_id in ANIMATION_CSS.keys():
            print(f"  {anim_id}")
        return

    renderer = TextAnimationRenderer()

    print(f"Rendering text overlay...")
    print(f"  Text: {args.text[:50]}{'...' if len(args.text) > 50 else ''}")
    print(f"  Style: {args.style}")
    print(f"  Animation: {args.animation}")
    print(f"  Duration: {args.duration}s")
    print(f"  Size: {args.width}x{args.height}")

    asset = renderer.render_overlay(
        text=args.text,
        style_template=args.style,
        animation=args.animation,
        duration=args.duration,
        width=args.width,
        height=args.height,
        output_filename=args.output,
    )

    print(f"\nGenerated: {asset.file_path}")
    print(f"  Duration: {asset.duration}s")


if __name__ == "__main__":
    main()
