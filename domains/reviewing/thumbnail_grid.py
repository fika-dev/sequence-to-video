from __future__ import annotations

import subprocess
import tempfile
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

GRID_SIZE = 5
THUMB_SIZE = 300
GRID_PADDING = 10
LABEL_HEIGHT = 30
PLACEHOLDER_COLOR = (40, 40, 40)
LABEL_BG_COLOR = (0, 0, 0, 180)
LABEL_TEXT_COLOR = (255, 255, 255)


def extract_frame_from_video(video_path: Path, timestamp: float) -> Image.Image | None:
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name

    cmd = [
        "ffmpeg",
        "-ss", str(timestamp),
        "-i", str(video_path),
        "-vframes", "1",
        "-q:v", "2",
        "-y",
        tmp_path,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=10)
        if Path(tmp_path).exists() and Path(tmp_path).stat().st_size > 0:
            img = Image.open(tmp_path)
            img.load()
            Path(tmp_path).unlink(missing_ok=True)
            return img
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, Exception):
        pass

    Path(tmp_path).unlink(missing_ok=True)
    return None


def crop_to_square(img: Image.Image) -> Image.Image:
    width, height = img.size
    min_dim = min(width, height)

    left = (width - min_dim) // 2
    top = (height - min_dim) // 2
    right = left + min_dim
    bottom = top + min_dim

    return img.crop((left, top, right, bottom))


def create_placeholder(scene_id: str, message: str = "No visual") -> Image.Image:
    img = Image.new("RGB", (THUMB_SIZE, THUMB_SIZE), PLACEHOLDER_COLOR)
    draw = ImageDraw.Draw(img)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
    except (OSError, IOError):
        font = ImageFont.load_default()

    text = f"{scene_id}\n{message}"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    x = (THUMB_SIZE - text_width) // 2
    y = (THUMB_SIZE - text_height) // 2

    draw.text((x, y), text, fill=(128, 128, 128), font=font, align="center")

    return img


def add_label_to_thumbnail(img: Image.Image, label: str) -> Image.Image:
    img = img.copy()
    draw = ImageDraw.Draw(img, "RGBA")

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 18)
    except (OSError, IOError):
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), label, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    padding = 4
    rect_height = text_height + padding * 2

    draw.rectangle(
        [(0, 0), (img.width, rect_height)],
        fill=LABEL_BG_COLOR,
    )

    x = (img.width - text_width) // 2
    y = padding

    draw.text((x, y), label, fill=LABEL_TEXT_COLOR, font=font)

    return img


def get_thumbnail_for_scene(
    scene: dict,
    library_index_dir: Path,
    generated_dir: Path,
) -> Image.Image | None:
    scene_id = scene.get("scene_id", "???")

    selected_clip_id = scene.get("selected_clip_id")
    if selected_clip_id:
        thumb = _get_thumbnail_from_clip_id(selected_clip_id, library_index_dir)
        if thumb:
            return thumb

    prepared = scene.get("prepared", {})
    visual_path = prepared.get("visual_path")
    if visual_path:
        path = Path(visual_path)
        if path.exists():
            if path.suffix.lower() in [".jpg", ".jpeg", ".png", ".webp"]:
                try:
                    return Image.open(path)
                except Exception:
                    pass
            elif path.suffix.lower() in [".mp4", ".mov", ".webm"]:
                thumb = extract_frame_from_video(path, 0.5)
                if thumb:
                    return thumb

    visual_layer = scene.get("visual_layer", {})
    candidate_clips = visual_layer.get("candidate_clips", [])
    if candidate_clips:
        for clip_id in candidate_clips[:3]:
            thumb = _get_thumbnail_from_clip_id(clip_id, library_index_dir)
            if thumb:
                return thumb

    return None


def _get_thumbnail_from_clip_id(clip_id: str, library_index_dir: Path) -> Image.Image | None:
    import json

    for index_file in library_index_dir.glob("*.json"):
        try:
            with open(index_file, encoding="utf-8") as f:
                index_data = json.load(f)

            source_file = index_data.get("source_file")
            if not source_file:
                continue

            for clip in index_data.get("clips", []):
                if clip.get("clip_id") == clip_id:
                    video_path = Path(source_file)
                    if not video_path.exists():
                        video_path = library_index_dir.parent / "raw_footage" / video_path.name
                        if not video_path.exists():
                            continue

                    start = clip.get("start_time", 0)
                    end = clip.get("end_time", start + 1)
                    mid_time = (start + end) / 2

                    return extract_frame_from_video(video_path, mid_time)
        except (json.JSONDecodeError, Exception):
            continue

    return None


def create_thumbnail_grid(
    sequence_data: dict,
    library_index_dir: Path,
    generated_dir: Path,
    verbose: bool = False,
) -> Image.Image:
    scenes = sequence_data.get("scenes", [])

    cell_size = THUMB_SIZE + GRID_PADDING
    grid_width = GRID_SIZE * cell_size + GRID_PADDING
    grid_height = GRID_SIZE * cell_size + GRID_PADDING

    grid = Image.new("RGB", (grid_width, grid_height), (20, 20, 20))

    for i, scene in enumerate(scenes[:GRID_SIZE * GRID_SIZE]):
        row = i // GRID_SIZE
        col = i % GRID_SIZE

        scene_id = scene.get("scene_id", f"s{i+1:02d}")

        if verbose:
            print(f"    Processing {scene_id}...")

        thumb = get_thumbnail_for_scene(scene, library_index_dir, generated_dir)

        if thumb is None:
            thumb = create_placeholder(scene_id, "No visual")
        else:
            thumb = crop_to_square(thumb)
            thumb = thumb.resize((THUMB_SIZE, THUMB_SIZE), Image.Resampling.LANCZOS)

        thumb = add_label_to_thumbnail(thumb, scene_id)

        x = col * cell_size + GRID_PADDING
        y = row * cell_size + GRID_PADDING

        grid.paste(thumb, (x, y))

    return grid


def grid_to_bytes(grid: Image.Image, format: str = "JPEG") -> bytes:
    buffer = BytesIO()
    grid.save(buffer, format=format, quality=85)
    buffer.seek(0)
    return buffer.getvalue()
