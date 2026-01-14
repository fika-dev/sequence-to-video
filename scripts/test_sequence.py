#!/usr/bin/env python3
"""Sequence Generator 개별 테스트 스크립트"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from domains.sequencing.generator import SequenceGenerator
from infrastructure.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Generate sequence JSON from script")
    parser.add_argument("script", help="Script text or path to script file")
    parser.add_argument("-o", "--output", help="Output JSON path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--env", help="Path to .env file")

    args = parser.parse_args()

    config = load_config(args.env)

    generator = SequenceGenerator(
        project=config.api.google_project_id,
        location="global",
        model="gemini-3-flash-preview",
    )

    script_path = Path(args.script)
    if script_path.exists():
        sequence_data, metadata = generator.generate_from_file(
            script_path=script_path,
            output_path=args.output,
            verbose=args.verbose,
        )
    else:
        sequence_data, metadata = generator.generate_from_script(
            script=args.script,
            output_path=args.output,
            verbose=args.verbose,
        )

    print(f"\nSequence generated:")
    print(f"  Locale: {metadata.locale}")
    print(f"  Context: {metadata.context}")
    print(f"  Title: {metadata.title}")
    print(f"  Scenes: {len(sequence_data.get('scenes', []))}")

    if args.output:
        print(f"\nSaved to: {args.output}")
    else:
        import json
        print(f"\nSequence JSON:")
        print(json.dumps(sequence_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
