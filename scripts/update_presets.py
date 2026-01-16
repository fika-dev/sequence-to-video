#!/usr/bin/env python3
"""Update preset JSON files from provider definitions.

This script syncs the preset JSON files in assets/presets/ with the actual
presets defined in the provider classes. It will:
- Add new presets with placeholder descriptions
- Warn about presets that exist in JSON but not in providers (stale)
- Preserve existing descriptions for presets that still exist

Usage:
    uv run python scripts/update_presets.py
    uv run python scripts/update_presets.py --check  # Dry-run, only report differences
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.lottie_renderer import LottieRenderer
from domains.studio.sfx_provider import SFXProvider


PRESETS_DIR = Path("assets/presets")
SFX_PRESETS_FILE = PRESETS_DIR / "sfx_presets.json"
LOTTIE_PRESETS_FILE = PRESETS_DIR / "lottie_presets.json"


def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {path}")


def sync_presets(
    provider_presets: list[str],
    json_file: Path,
    preset_type: str,
    check_only: bool = False,
) -> tuple[list[str], list[str]]:
    existing = load_json(json_file)
    existing_names = set(existing.keys())
    provider_names = set(provider_presets)

    added = provider_names - existing_names
    stale = existing_names - provider_names

    if added:
        print(f"\n  New {preset_type} presets found:")
        for name in sorted(added):
            print(f"    + {name}")

    if stale:
        print(f"\n  Stale {preset_type} presets (in JSON but not in provider):")
        for name in sorted(stale):
            print(f"    - {name}")

    if not added and not stale:
        print(f"\n  {preset_type} presets are in sync")
        return [], []

    if check_only:
        return list(added), list(stale)

    updated = {}

    for name in sorted(provider_names):
        if name in existing:
            updated[name] = existing[name]
        else:
            updated[name] = {
                "description": f"[TODO: Add description for {name}]",
                "use_case": "[TODO: Add use case]",
            }

    save_json(json_file, updated)

    if stale:
        print(f"\n  Removed {len(stale)} stale preset(s)")
    if added:
        print(f"  Added {len(added)} new preset(s) - please update descriptions!")

    return list(added), list(stale)


def main():
    parser = argparse.ArgumentParser(
        description="Update preset JSON files from provider definitions"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check only, don't modify files",
    )
    args = parser.parse_args()

    print("Syncing preset files...")

    print(f"\n[SFX Presets] {SFX_PRESETS_FILE}")
    sfx_presets = SFXProvider.list_presets()
    sfx_added, sfx_stale = sync_presets(sfx_presets, SFX_PRESETS_FILE, "SFX", args.check)

    print(f"\n[Lottie Presets] {LOTTIE_PRESETS_FILE}")
    lottie_presets = LottieRenderer.list_presets()
    lottie_added, lottie_stale = sync_presets(
        lottie_presets, LOTTIE_PRESETS_FILE, "Lottie", args.check
    )

    total_added = len(sfx_added) + len(lottie_added)
    total_stale = len(sfx_stale) + len(lottie_stale)

    print("\n" + "=" * 50)
    if args.check:
        if total_added or total_stale:
            print(f"Changes needed: {total_added} to add, {total_stale} stale")
            print("Run without --check to apply changes")
            sys.exit(1)
        else:
            print("All presets are in sync!")
    else:
        if total_added:
            print(f"\nAction required: Update descriptions for {total_added} new preset(s)")
            print(f"  Edit: {SFX_PRESETS_FILE}")
            print(f"  Edit: {LOTTIE_PRESETS_FILE}")
        else:
            print("Done! All presets synced.")


if __name__ == "__main__":
    main()
