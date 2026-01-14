import json
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

from domains.editing.effects import EffectApplier
from domains.editing.models import ComposedScene, Timeline
from domains.planning.models import CameraMovement


class FFmpegRenderer:
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = Path(output_dir) if output_dir else Path("assets/review_output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.effect_applier = EffectApplier()

    def render_scene(
        self,
        scene: ComposedScene,
        width: int,
        height: int,
        fps: float,
        output_path: Path,
    ) -> Path:
        inputs = []
        filter_complex = []
        
        video_label = "[v0]"
        if scene.video_path:
            inputs.extend(["-i", str(scene.video_path)])
            is_image = scene.video_path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
            if is_image:
                filter_complex.append(
                    f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={scene.duration},"
                    f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v0]"
                )
            else:
                filter_complex.append(
                    f"[0:v]trim=duration={scene.duration},fps={fps},"
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v0]"
                )
        else:
            inputs.extend(["-f", "lavfi", "-i", f"color=c=black:s={width}x{height}:d={scene.duration}:r={fps}"])
            video_label = "[0:v]"
            filter_complex.append(f"[0:v]copy[v0]")

        audio_input_idx = 1 if scene.video_path else 1
        if scene.audio_path:
            inputs.extend(["-i", str(scene.audio_path)])
            audio_label = f"[{audio_input_idx}:a]"
        else:
            inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={scene.duration}"])
            audio_label = f"[{audio_input_idx}:a]"

        if scene.text_overlay_path:
            overlay_idx = audio_input_idx + 1
            inputs.extend(["-i", str(scene.text_overlay_path)])
            is_prores = scene.text_overlay_path.suffix.lower() == ".mov"
            if is_prores:
                filter_complex.append(
                    f"[v0][{overlay_idx}:v]overlay=0:0:format=auto[vout]"
                )
            else:
                filter_complex.append(
                    f"[{overlay_idx}:v]chromakey=0x00FF00:0.1:0.2[txtkey];"
                    f"[v0][txtkey]overlay=0:0[vout]"
                )
            final_video = "[vout]"
        else:
            final_video = "[v0]"

        camera_movement = CameraMovement(scene.effects.get("camera_movement", "none"))
        if camera_movement != CameraMovement.NONE:
            camera_filter = self.effect_applier.get_camera_filter(
                camera_movement, scene.duration, width, height
            )
            if camera_filter:
                filter_complex.append(f"{final_video}{camera_filter}[vcam]")
                final_video = "[vcam]"

        filter_str = ";".join(filter_complex) if filter_complex else None

        cmd = ["ffmpeg", "-y"]
        cmd.extend(inputs)
        
        if filter_str:
            cmd.extend(["-filter_complex", filter_str])
            cmd.extend(["-map", final_video])
            cmd.extend(["-map", f"{audio_input_idx}:a"])
        
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(scene.duration),
            str(output_path),
        ])

        subprocess.run(cmd, check=True, capture_output=True)
        return output_path

    def render_timeline(
        self,
        timeline: Timeline,
        output_filename: str | None = None,
        save_individual_scenes: bool = True,
    ) -> Path:
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"{timeline.project_id}_final.mp4"

        scenes_dir = self.output_dir / timeline.project_id / "scenes"
        if save_individual_scenes:
            scenes_dir.mkdir(parents=True, exist_ok=True)

        scene_files = []
        for i, scene in enumerate(timeline.scenes):
            if save_individual_scenes:
                scene_path = scenes_dir / f"{scene.scene_id}.mp4"
            else:
                scene_path = self.output_dir / timeline.project_id / f"_temp_scene_{i:03d}.mp4"
                scene_path.parent.mkdir(parents=True, exist_ok=True)

            self.render_scene(
                scene=scene,
                width=timeline.width,
                height=timeline.height,
                fps=timeline.fps,
                output_path=scene_path,
            )
            scene_files.append(scene_path)

        concat_list = self.output_dir / timeline.project_id / "_concat.txt"
        with open(concat_list, "w") as f:
            for scene_file in scene_files:
                f.write(f"file '{scene_file}'\n")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

        concat_list.unlink()
        if not save_individual_scenes:
            for scene_file in scene_files:
                scene_file.unlink()

        self._save_composition_metadata(timeline, output_path, scenes_dir if save_individual_scenes else None)
        return output_path

    def render_single_scene(
        self,
        scene: ComposedScene,
        timeline: Timeline,
        output_path: Path | None = None,
    ) -> Path:
        scenes_dir = self.output_dir / timeline.project_id / "scenes"
        scenes_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            output_path = scenes_dir / f"{scene.scene_id}.mp4"

        self.render_scene(
            scene=scene,
            width=timeline.width,
            height=timeline.height,
            fps=timeline.fps,
            output_path=output_path,
        )
        return output_path

    def reassemble_from_scenes(
        self,
        timeline: Timeline,
        output_filename: str | None = None,
    ) -> Path:
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"{timeline.project_id}_final.mp4"

        scenes_dir = self.output_dir / timeline.project_id / "scenes"
        scene_files = []
        for scene in timeline.scenes:
            scene_path = scenes_dir / f"{scene.scene_id}.mp4"
            if not scene_path.exists():
                raise FileNotFoundError(f"Scene file not found: {scene_path}")
            scene_files.append(scene_path)

        concat_list = self.output_dir / timeline.project_id / "_concat.txt"
        with open(concat_list, "w") as f:
            for scene_file in scene_files:
                f.write(f"file '{scene_file}'\n")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_list),
                "-c:v", "libx264",
                "-preset", "medium",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

        concat_list.unlink()
        self._save_composition_metadata(timeline, output_path, scenes_dir)
        return output_path

    def _save_composition_metadata(
        self,
        timeline: Timeline,
        output_path: Path,
        scenes_dir: Path | None = None,
    ) -> None:
        scenes_metadata = []
        for scene in timeline.scenes:
            scene_meta = {
                "scene_id": scene.scene_id,
                "duration": scene.duration,
                "video_source": str(scene.video_path) if scene.video_path else None,
                "audio_source": str(scene.audio_path) if scene.audio_path else None,
                "text_overlay_source": str(scene.text_overlay_path) if scene.text_overlay_path else None,
                "effects": scene.effects,
            }
            if scenes_dir:
                scene_meta["rendered_file"] = str(scenes_dir / f"{scene.scene_id}.mp4")
            scenes_metadata.append(scene_meta)

        metadata = {
            "output_file": str(output_path),
            "project_id": timeline.project_id,
            "resolution": {"width": timeline.width, "height": timeline.height},
            "fps": timeline.fps,
            "total_duration": timeline.total_duration,
            "scene_count": len(timeline.scenes),
            "scenes": scenes_metadata,
            "scenes_dir": str(scenes_dir) if scenes_dir else None,
            "created_at": datetime.now().isoformat(),
        }

        metadata_path = output_path.with_suffix(".meta.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
