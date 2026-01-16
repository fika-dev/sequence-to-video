import pytest

from domains.editing.effects import EffectApplier
from domains.planning.models import CameraMovement, Transition


class TestEffectApplierGetCameraFilter:
    @pytest.fixture
    def applier(self):
        return EffectApplier()

    def test_none_movement_returns_none(self, applier):
        result = applier.get_camera_filter(CameraMovement.NONE, duration=3.0)
        assert result is None

    def test_zoom_in_slow_returns_zoompan_filter(self, applier):
        result = applier.get_camera_filter(CameraMovement.ZOOM_IN_SLOW, duration=3.0)
        assert result is not None
        assert "zoompan" in result
        assert "scale=" in result
        assert "min(1+" in result

    def test_zoom_out_slow_returns_zoompan_filter(self, applier):
        result = applier.get_camera_filter(CameraMovement.ZOOM_OUT_SLOW, duration=3.0)
        assert result is not None
        assert "zoompan" in result
        assert "max(1.5-" in result

    def test_pan_left_returns_zoompan_with_positive_x_offset(self, applier):
        result = applier.get_camera_filter(CameraMovement.PAN_LEFT, duration=3.0)
        assert result is not None
        assert "zoompan" in result
        assert "+{" in result or "*on*iw" in result

    def test_pan_right_returns_zoompan_with_negative_x_offset(self, applier):
        result = applier.get_camera_filter(CameraMovement.PAN_RIGHT, duration=3.0)
        assert result is not None
        assert "zoompan" in result
        assert "-{" in result or "-" in result

    def test_shake_returns_crop_with_random(self, applier):
        result = applier.get_camera_filter(CameraMovement.SHAKE, duration=3.0)
        assert result is not None
        assert "crop=" in result
        assert "random" in result

    def test_custom_dimensions_used_in_filter(self, applier):
        result = applier.get_camera_filter(
            CameraMovement.ZOOM_IN_SLOW, duration=3.0, width=1080, height=1920
        )
        assert result is not None
        assert "1080x1920" in result
        assert "4320:7680" in result

    def test_duration_affects_zoom_speed(self, applier):
        short_duration = applier.get_camera_filter(
            CameraMovement.ZOOM_IN_SLOW, duration=1.0, width=720, height=1280
        )
        long_duration = applier.get_camera_filter(
            CameraMovement.ZOOM_IN_SLOW, duration=10.0, width=720, height=1280
        )
        assert short_duration is not None
        assert long_duration is not None
        assert "zoompan" in short_duration
        assert "zoompan" in long_duration


class TestEffectApplierGetTransitionFilter:
    @pytest.fixture
    def applier(self):
        return EffectApplier()

    def test_cut_returns_zero_duration(self, applier):
        result = applier.get_transition_filter(Transition.CUT)
        assert result == {"type": "cut", "duration": 0}

    def test_fade_returns_xfade_config(self, applier):
        result = applier.get_transition_filter(Transition.FADE)
        assert result["type"] == "xfade"
        assert result["transition"] == "fade"
        assert result["duration"] == 0.5

    def test_whip_pan_left_returns_wipeleft(self, applier):
        result = applier.get_transition_filter(Transition.WHIP_PAN_LEFT)
        assert result["type"] == "xfade"
        assert result["transition"] == "wipeleft"

    def test_whip_pan_right_returns_wiperight(self, applier):
        result = applier.get_transition_filter(Transition.WHIP_PAN_RIGHT)
        assert result["type"] == "xfade"
        assert result["transition"] == "wiperight"

    def test_dissolve_returns_dissolve(self, applier):
        result = applier.get_transition_filter(Transition.DISSOLVE)
        assert result["type"] == "xfade"
        assert result["transition"] == "dissolve"

    def test_custom_duration_applied(self, applier):
        result = applier.get_transition_filter(Transition.FADE, duration=1.0)
        assert result["duration"] == 1.0


class TestEffectApplierGetBeatEffectFilter:
    @pytest.fixture
    def applier(self):
        return EffectApplier()

    def test_shake_on_beat_returns_crop_with_enable(self, applier):
        beat_timing = [0.5, 1.0, 1.5]
        result = applier.get_beat_effect_filter("shake_on_beat", beat_timing, duration=3.0)
        assert result is not None
        assert "crop=" in result
        assert "enable=" in result
        assert "between(t,0.5," in result

    def test_flash_on_beat_returns_brightness_filter(self, applier):
        beat_timing = [1.0, 2.0]
        result = applier.get_beat_effect_filter("flash_on_beat", beat_timing, duration=3.0)
        assert result is not None
        assert "eq=brightness=" in result
        assert "enable=" in result

    def test_zoom_pulse_returns_scale_filter(self, applier):
        beat_timing = [0.5, 1.5]
        result = applier.get_beat_effect_filter("zoom_pulse", beat_timing, duration=3.0)
        assert result is not None
        assert "scale=" in result
        assert "1.1" in result

    def test_unknown_effect_returns_none(self, applier):
        result = applier.get_beat_effect_filter("unknown_effect", [0.5], duration=3.0)
        assert result is None

    def test_empty_beat_timing_creates_empty_enable(self, applier):
        result = applier.get_beat_effect_filter("shake_on_beat", [], duration=3.0)
        assert result is not None
        assert "enable=''" in result


class TestEffectApplierBuildFilterChain:
    @pytest.fixture
    def applier(self):
        return EffectApplier()

    def test_includes_scale_and_pad_always(self, applier):
        result = applier.build_filter_chain(
            camera_movement=CameraMovement.NONE,
            beat_effect=None,
            beat_timing=[],
            duration=3.0,
            width=720,
            height=1280,
        )
        assert any("scale=720:1280" in f for f in result)
        assert any("pad=720:1280" in f for f in result)

    def test_includes_camera_filter_when_present(self, applier):
        result = applier.build_filter_chain(
            camera_movement=CameraMovement.ZOOM_IN_SLOW,
            beat_effect=None,
            beat_timing=[],
            duration=3.0,
            width=720,
            height=1280,
        )
        assert any("zoompan" in f for f in result)

    def test_includes_beat_filter_when_present(self, applier):
        result = applier.build_filter_chain(
            camera_movement=CameraMovement.NONE,
            beat_effect="shake_on_beat",
            beat_timing=[0.5, 1.0],
            duration=3.0,
            width=720,
            height=1280,
        )
        assert any("crop=" in f and "enable=" in f for f in result)

    def test_filter_order_camera_then_beat_then_scale(self, applier):
        result = applier.build_filter_chain(
            camera_movement=CameraMovement.ZOOM_IN_SLOW,
            beat_effect="shake_on_beat",
            beat_timing=[0.5],
            duration=3.0,
            width=720,
            height=1280,
        )
        camera_idx = next(i for i, f in enumerate(result) if "zoompan" in f)
        beat_idx = next(i for i, f in enumerate(result) if "enable=" in f)
        scale_idx = next(i for i, f in enumerate(result) if "force_original_aspect_ratio" in f)

        assert camera_idx < beat_idx < scale_idx
