from pathlib import Path

import pytest

from domains.editing.renderer import FFmpegRenderer


class TestFFmpegRendererGetOverlayPosition:
    def test_center_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("center", 0.5, 720, 1280)

        assert x == "(W-w)/2"
        assert y == "(H-h)/2"

    def test_top_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("top", 0.5, 720, 1280)

        assert x == "(W-w)/2"
        assert y == "100"

    def test_bottom_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("bottom", 0.5, 720, 1280)

        assert x == "(W-w)/2"
        assert y == "H-h-200"

    def test_top_left_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("top-left", 0.5, 720, 1280)

        assert x == "100"
        assert y == "100"

    def test_top_right_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("top-right", 0.5, 720, 1280)

        assert x == "W-w-100"
        assert y == "100"

    def test_bottom_left_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("bottom-left", 0.5, 720, 1280)

        assert x == "100"
        assert y == "H-h-200"

    def test_bottom_right_position(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("bottom-right", 0.5, 720, 1280)

        assert x == "W-w-100"
        assert y == "H-h-200"

    def test_unknown_position_defaults_to_center(self):
        renderer = FFmpegRenderer.__new__(FFmpegRenderer)

        x, y = renderer._get_overlay_position("unknown_position", 0.5, 720, 1280)

        assert x == "(W-w)/2"
        assert y == "(H-h)/2"


class TestFFmpegRendererInit:
    def test_creates_output_directory(self, tmp_path: Path):
        output_dir = tmp_path / "render_output"

        renderer = FFmpegRenderer(output_dir=output_dir)

        assert output_dir.exists()

    def test_defaults_to_review_output_directory(self):
        renderer = FFmpegRenderer()

        assert "review_output" in str(renderer.output_dir)


class TestFFmpegRendererReassembleFromSceneIds:
    def test_raises_when_scene_file_not_found(self, tmp_path: Path):
        renderer = FFmpegRenderer(output_dir=tmp_path)

        project_dir = tmp_path / "test_project" / "scenes"
        project_dir.mkdir(parents=True)

        with pytest.raises(FileNotFoundError, match="Scene file not found"):
            renderer.reassemble_from_scene_ids(
                project_id="test_project",
                scene_ids=["s01", "s02"],
            )
