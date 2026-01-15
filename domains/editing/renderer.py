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
                if scene.clip_start_time is not None:
                    trim_filter = f"trim=start={scene.clip_start_time}:duration={scene.duration},setpts=PTS-STARTPTS"
                else:
                    trim_filter = f"trim=duration={scene.duration}"
                filter_complex.append(
                    f"[0:v]{trim_filter},fps={fps},"
                    f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2[v0]"
                )
        else:
            inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=black:s={width}x{height}:d={scene.duration}:r={fps}",
                ]
            )
            video_label = "[0:v]"
            filter_complex.append(f"[0:v]copy[v0]")

        camera_movement = CameraMovement(scene.effects.get("camera_movement", "none"))
        if camera_movement != CameraMovement.NONE:
            camera_filter = self.effect_applier.get_camera_filter(
                camera_movement, scene.duration, width, height
            )
            if camera_filter:
                filter_complex.append(f"[v0]{camera_filter}[vcam]")
                current_video = "[vcam]"
            else:
                current_video = "[v0]"
        else:
            current_video = "[v0]"

        audio_input_idx = 1 if scene.video_path else 1
        if scene.audio_path:
            inputs.extend(["-i", str(scene.audio_path)])
            audio_label = f"[{audio_input_idx}:a]"
        else:
            inputs.extend(["-f", "lavfi", "-i", f"anullsrc=r=44100:cl=stereo:d={scene.duration}"])
            audio_label = f"[{audio_input_idx}:a]"

        next_input_idx = audio_input_idx + 1

        sfx_labels = []
        for i, sfx in enumerate(scene.sfx_assets):
            sfx_input_idx = next_input_idx
            next_input_idx += 1
            inputs.extend(["-i", str(sfx.file_path)])

            sfx_filter_parts = []
            if sfx.start_time > 0:
                sfx_filter_parts.append(
                    f"adelay={int(sfx.start_time * 1000)}|{int(sfx.start_time * 1000)}"
                )
            if sfx.fade_in > 0:
                sfx_filter_parts.append(f"afade=t=in:st=0:d={sfx.fade_in}")
            if sfx.fade_out > 0:
                sfx_filter_parts.append(
                    f"afade=t=out:st={scene.duration - sfx.fade_out}:d={sfx.fade_out}"
                )
            sfx_filter_parts.append(f"volume={sfx.volume}")

            sfx_label = f"[sfx{i}]"
            sfx_filter = ",".join(sfx_filter_parts)
            filter_complex.append(f"[{sfx_input_idx}:a]{sfx_filter}{sfx_label}")
            sfx_labels.append(sfx_label)

        if sfx_labels:
            all_audio_labels = [audio_label] + sfx_labels
            mix_input = "".join(all_audio_labels)
            filter_complex.append(
                f"{mix_input}amix=inputs={len(all_audio_labels)}:duration=longest:normalize=0[amixed]"
            )
            audio_label = "[amixed]"

        if scene.text_overlay_path:
            overlay_idx = next_input_idx
            next_input_idx += 1
            inputs.extend(["-i", str(scene.text_overlay_path)])
            is_prores = scene.text_overlay_path.suffix.lower() == ".mov"
            if is_prores:
                filter_complex.append(
                    f"{current_video}[{overlay_idx}:v]overlay=0:0:format=auto[vtxt]"
                )
            else:
                filter_complex.append(
                    f"[{overlay_idx}:v]chromakey=0x00FF00:0.1:0.2[txtkey];"
                    f"{current_video}[txtkey]overlay=0:0[vtxt]"
                )
            current_video = "[vtxt]"

        for i, lottie_overlay in enumerate(scene.lottie_overlays):
            overlay_idx = next_input_idx
            next_input_idx += 1
            inputs.extend(["-i", str(lottie_overlay.file_path)])

            overlay_x, overlay_y = self._get_overlay_position(
                lottie_overlay.position, lottie_overlay.scale, width, height
            )
            scale_filter = f"scale=iw*{lottie_overlay.scale}:ih*{lottie_overlay.scale}"
            delay_frames = int(lottie_overlay.start_time * fps)
            out_label = f"[vlottie{i}]"

            filter_complex.append(
                f"[{overlay_idx}:v]{scale_filter},setpts=PTS+{lottie_overlay.start_time}/TB[lottie{i}scaled];"
                f"{current_video}[lottie{i}scaled]overlay={overlay_x}:{overlay_y}:enable='gte(t,{lottie_overlay.start_time})':shortest=0{out_label}"
            )
            current_video = out_label

        final_video = current_video

        filter_str = ";".join(filter_complex) if filter_complex else None

        cmd = ["ffmpeg", "-y"]
        cmd.extend(inputs)

        has_sfx = len(scene.sfx_assets) > 0
        if filter_str:
            cmd.extend(["-filter_complex", filter_str])
            cmd.extend(["-map", final_video])
            if has_sfx:
                cmd.extend(["-map", "[amixed]"])
            else:
                cmd.extend(["-map", f"{audio_input_idx}:a"])

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-t",
                str(scene.duration),
                str(output_path),
            ]
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(
                f"FFmpeg failed for scene {scene.scene_id}:\n"
                f"Command: {' '.join(cmd)}\n"
                f"stderr: {result.stderr}"
            )
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
                f.write(f"file '{scene_file.resolve()}'\n")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

        concat_list.unlink()
        if not save_individual_scenes:
            for scene_file in scene_files:
                scene_file.unlink()

        self._save_composition_metadata(
            timeline, output_path, scenes_dir if save_individual_scenes else None
        )
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
        scene_ids = [scene.scene_id for scene in timeline.scenes]
        return self.reassemble_from_scene_ids(
            project_id=timeline.project_id,
            scene_ids=scene_ids,
            output_filename=output_filename,
        )

    def reassemble_from_scene_ids(
        self,
        project_id: str,
        scene_ids: list[str],
        output_filename: str | None = None,
    ) -> Path:
        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"{project_id}_final.mp4"

        scenes_dir = self.output_dir / project_id / "scenes"
        scene_files = []
        for scene_id in scene_ids:
            scene_path = scenes_dir / f"{scene_id}.mp4"
            if not scene_path.exists():
                raise FileNotFoundError(f"Scene file not found: {scene_path}")
            scene_files.append(scene_path)

        concat_list = self.output_dir / project_id / "_concat.txt"
        with open(concat_list, "w") as f:
            for scene_file in scene_files:
                f.write(f"file '{scene_file.resolve()}'\n")

        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c:v",
                "libx264",
                "-preset",
                "medium",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                str(output_path),
            ],
            check=True,
            capture_output=True,
        )

        concat_list.unlink()
        return output_path

    def _get_overlay_position(
        self, position: str, scale: float, width: int, height: int
    ) -> tuple[str, str]:
        positions = {
            "center": ("(W-w)/2", "(H-h)/2"),
            "top": ("(W-w)/2", "100"),
            "bottom": ("(W-w)/2", "H-h-200"),
            "top-left": ("100", "100"),
            "top-right": ("W-w-100", "100"),
            "bottom-left": ("100", "H-h-200"),
            "bottom-right": ("W-w-100", "H-h-200"),
        }
        return positions.get(position, positions["center"])

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
                "text_overlay_source": str(scene.text_overlay_path)
                if scene.text_overlay_path
                else None,
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
