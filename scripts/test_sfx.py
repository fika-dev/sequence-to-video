#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.sfx_provider import SFXProvider


def main():
    parser = argparse.ArgumentParser(description="Test SFX provider")
    parser.add_argument("preset", nargs="?", help="SFX preset name (e.g., 'success', 'error')")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")

    args = parser.parse_args()

    sfx = SFXProvider()

    if args.list_presets or not args.preset:
        print("Available SFX presets:\n")
        for name, info in sfx.list_available().items():
            status = "OK" if info["exists"] else "MISSING"
            print(f"  {name:12} [{status}] {info['path']}")
        return 0

    try:
        asset = sfx.get_sfx(args.preset)
        print(f"SFX: {args.preset}")
        print(f"  Path: {asset.file_path}")
        print(f"  Duration: {asset.duration:.2f}s")
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
