#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.lottie_renderer import LottieRenderer


def main():
    parser = argparse.ArgumentParser(description="Test Lottie overlay loading")
    parser.add_argument("lottie", nargs="?", help="Lottie preset name or path to .mov file")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")

    args = parser.parse_args()

    renderer = LottieRenderer()

    if args.list_presets:
        print("Available Lottie presets:")
        for name, info in renderer.list_available().items():
            status = "OK" if info["exists"] else "MISSING"
            print(f"  {name}: {info['path']} [{status}]")
        print()
        print("To generate missing MOV files:")
        print("  uv run python scripts/convert_lottie_to_mov.py")
        return

    if not args.lottie:
        parser.error("lottie argument is required (or use --list-presets)")

    print(f"Loading Lottie overlay: {args.lottie}")

    asset = renderer.get_overlay(args.lottie)

    print(f"\nLoaded: {asset.file_path}")
    print(f"  Duration: {asset.duration:.2f}s")
    print(f"  Size: {asset.width}x{asset.height}")
    print(f"  FPS: {asset.fps}")


if __name__ == "__main__":
    main()
