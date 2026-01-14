#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path


def convert_mov_to_mp4(
    input_dir: Path,
    output_dir: Path | None = None,
    delete_original: bool = False,
    verbose: bool = False,
) -> list[Path]:
    input_dir = Path(input_dir)
    output_dir = Path(output_dir) if output_dir else input_dir

    mov_files = list(input_dir.glob("**/*.mov")) + list(input_dir.glob("**/*.MOV"))

    if verbose:
        print(f"Found {len(mov_files)} MOV files in {input_dir}")

    converted = []

    for i, mov_file in enumerate(mov_files, 1):
        relative_path = mov_file.relative_to(input_dir)
        mp4_path = output_dir / relative_path.with_suffix(".mp4")

        mp4_path.parent.mkdir(parents=True, exist_ok=True)

        if mp4_path.exists():
            if verbose:
                print(f"[{i}/{len(mov_files)}] SKIP {mov_file.name} (mp4 already exists)")
            continue

        if verbose:
            print(f"[{i}/{len(mov_files)}] Converting {mov_file.name}...")

        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(mov_file),
                    "-c:v", "libx264",
                    "-preset", "medium",
                    "-crf", "23",
                    "-c:a", "aac",
                    "-b:a", "128k",
                    "-movflags", "+faststart",
                    "-y",
                    str(mp4_path),
                ],
                capture_output=True,
                check=True,
            )
            converted.append(mp4_path)

            if verbose:
                print(f"    -> {mp4_path.name}")

            if delete_original:
                mov_file.unlink()
                if verbose:
                    print(f"    Deleted original: {mov_file.name}")

        except subprocess.CalledProcessError as e:
            print(f"ERROR converting {mov_file.name}: {e.stderr.decode()}")

    return converted


def main():
    parser = argparse.ArgumentParser(description="Convert MOV files to MP4")
    parser.add_argument(
        "input_dir",
        nargs="?",
        default="assets/raw_footage",
        help="Input directory (default: assets/raw_footage)",
    )
    parser.add_argument(
        "-o", "--output",
        help="Output directory (default: same as input)",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete original MOV files after conversion",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    converted = convert_mov_to_mp4(
        input_dir=args.input_dir,
        output_dir=args.output,
        delete_original=args.delete,
        verbose=args.verbose,
    )

    print(f"\nConverted {len(converted)} files")


if __name__ == "__main__":
    main()
