#!/usr/bin/env python3
"""TTS Generator 개별 테스트 스크립트"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.studio.tts_generator import TTSGenerator, VOICE_PRESETS


def main():
    parser = argparse.ArgumentParser(description="Test TTS generation")
    parser.add_argument("text", help="Text to synthesize")
    parser.add_argument(
        "-p", "--preset",
        default="chirp_v3_korean_female_confident",
        choices=list(VOICE_PRESETS.keys()),
        help="Voice preset",
    )
    parser.add_argument("-s", "--speed", type=float, default=1.0, help="Speech speed (0.5-2.0)")
    parser.add_argument("-o", "--output", help="Output filename")
    parser.add_argument("--list-presets", action="store_true", help="List available presets")

    args = parser.parse_args()

    if args.list_presets:
        print("Available voice presets:")
        for preset_id, preset_config in VOICE_PRESETS.items():
            print(f"  {preset_id}")
            print(f"    - language: {preset_config['language_code']}")
            print(f"    - voice: {preset_config['name']}")
        return

    tts = TTSGenerator()

    print(f"Generating TTS...")
    print(f"  Text: {args.text[:50]}{'...' if len(args.text) > 50 else ''}")
    print(f"  Preset: {args.preset}")
    print(f"  Speed: {args.speed}")

    asset = tts.generate(
        text=args.text,
        preset_id=args.preset,
        speed=args.speed,
        output_filename=args.output,
    )

    print(f"\nGenerated: {asset.file_path}")
    print(f"  Duration: {asset.duration:.2f}s")
    print(f"  Sample rate: {asset.sample_rate}Hz")


if __name__ == "__main__":
    main()
