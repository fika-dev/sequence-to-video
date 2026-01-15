#!/usr/bin/env python3
import argparse
import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from playwright.async_api import async_playwright


DEFAULT_LOTTIE_DIR = Path("assets/stock/lottie")
DEFAULT_OUTPUT_DIR = Path("assets/stock/lottie_mov")
DEFAULT_WIDTH = 720
DEFAULT_HEIGHT = 720
DEFAULT_FPS = 30


def get_lottie_info(lottie_path: Path) -> dict:
    with open(lottie_path) as f:
        data = json.load(f)
    return {
        "fps": data.get("fr", 60),
        "total_frames": data.get("op", 60) - data.get("ip", 0),
        "width": data.get("w", 512),
        "height": data.get("h", 512),
    }


async def convert_lottie_async(
    lottie_path: Path,
    output_path: Path,
    width: int,
    height: int,
    render_fps: int,
    verbose: bool = False,
) -> None:
    lottie_info = get_lottie_info(lottie_path)
    lottie_fps = lottie_info["fps"]
    lottie_frames = lottie_info["total_frames"]
    lottie_duration = lottie_frames / lottie_fps

    total_render_frames = int(lottie_duration * render_fps)

    lottie_json = lottie_path.read_text()

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <script src="https://cdnjs.cloudflare.com/ajax/libs/lottie-web/5.12.2/lottie.min.js"></script>
        <style>
            body {{
                margin: 0;
                padding: 0;
                width: {width}px;
                height: {height}px;
                background-color: transparent;
                display: flex;
                align-items: center;
                justify-content: center;
                overflow: hidden;
            }}
            #lottie-container {{
                width: 100%;
                height: 100%;
            }}
        </style>
    </head>
    <body>
        <div id="lottie-container"></div>
        <script>
            const animationData = {lottie_json};
            const anim = lottie.loadAnimation({{
                container: document.getElementById('lottie-container'),
                renderer: 'svg',
                loop: false,
                autoplay: false,
                animationData: animationData
            }});
            
            window.goToFrame = function(frame) {{
                anim.goToAndStop(frame, true);
            }};
        </script>
    </body>
    </html>
    """

    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html_content)
        html_path = Path(f.name)

    frames_dir = Path(tempfile.mkdtemp())

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": width, "height": height})
            await page.goto(f"file://{html_path}")
            await page.wait_for_function("typeof window.goToFrame === 'function'")

            for render_frame in range(total_render_frames):
                time_in_animation = render_frame / render_fps
                lottie_frame = int(time_in_animation * lottie_fps)

                await page.evaluate(f"window.goToFrame({lottie_frame})")
                frame_path = frames_dir / f"frame_{render_frame:05d}.png"
                await page.screenshot(path=str(frame_path), omit_background=True)

                if verbose and render_frame % 10 == 0:
                    print(f"    Frame {render_frame + 1}/{total_render_frames}")

            await browser.close()

        output_path.parent.mkdir(parents=True, exist_ok=True)

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(render_fps),
                "-i",
                str(frames_dir / "frame_%05d.png"),
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4444",
                "-pix_fmt",
                "yuva444p10le",
                str(output_path),
            ],
            check=True,
            capture_output=not verbose,
        )
    finally:
        html_path.unlink(missing_ok=True)
        for frame_file in frames_dir.glob("*.png"):
            frame_file.unlink()
        frames_dir.rmdir()


def convert_lottie(
    lottie_path: Path,
    output_path: Path,
    width: int,
    height: int,
    render_fps: int,
    verbose: bool = False,
) -> None:
    asyncio.run(
        convert_lottie_async(
            lottie_path=lottie_path,
            output_path=output_path,
            width=width,
            height=height,
            render_fps=render_fps,
            verbose=verbose,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="Convert Lottie JSON files to ProRes 4444 MOV with alpha channel"
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Single Lottie JSON file or directory (default: assets/stock/lottie)",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output directory (default: assets/stock/lottie_mov)",
    )
    parser.add_argument("-W", "--width", type=int, default=DEFAULT_WIDTH, help="Output width")
    parser.add_argument("-H", "--height", type=int, default=DEFAULT_HEIGHT, help="Output height")
    parser.add_argument("--fps", type=int, default=DEFAULT_FPS, help="Render FPS")
    parser.add_argument("--force", action="store_true", help="Overwrite existing MOV files")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    input_path = Path(args.input) if args.input else DEFAULT_LOTTIE_DIR
    output_dir = Path(args.output) if args.output else DEFAULT_OUTPUT_DIR

    if input_path.is_file():
        lottie_files = [input_path]
    elif input_path.is_dir():
        lottie_files = list(input_path.glob("*.json"))
    else:
        print(f"Error: {input_path} not found")
        sys.exit(1)

    if not lottie_files:
        print(f"No Lottie JSON files found in {input_path}")
        sys.exit(1)

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Converting {len(lottie_files)} Lottie file(s)...")
    print(f"  Output: {output_dir}")
    print(f"  Size: {args.width}x{args.height}")
    print(f"  FPS: {args.fps}")
    print()

    for lottie_path in lottie_files:
        output_path = output_dir / f"{lottie_path.stem}.mov"

        if output_path.exists() and not args.force:
            print(f"  [SKIP] {lottie_path.name} -> {output_path.name} (already exists)")
            continue

        lottie_info = get_lottie_info(lottie_path)
        duration = lottie_info["total_frames"] / lottie_info["fps"]

        print(f"  [CONVERT] {lottie_path.name} ({duration:.2f}s @ {lottie_info['fps']}fps)")

        try:
            convert_lottie(
                lottie_path=lottie_path,
                output_path=output_path,
                width=args.width,
                height=args.height,
                render_fps=args.fps,
                verbose=args.verbose,
            )
            print(f"    -> {output_path}")
        except Exception as e:
            print(f"    [ERROR] {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
