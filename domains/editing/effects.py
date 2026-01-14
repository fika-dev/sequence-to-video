from domains.planning.models import CameraMovement, Transition


class EffectApplier:
    def get_camera_filter(
        self,
        movement: CameraMovement,
        duration: float,
        width: int = 720,
        height: int = 1280,
    ) -> str | None:
        if movement == CameraMovement.NONE:
            return None

        total_frames = int(duration * 30)
        zoom_speed = 0.5 / total_frames
        scaled_w = width * 4
        scaled_h = height * 4

        if movement == CameraMovement.ZOOM_IN_SLOW:
            return (
                f"scale={scaled_w}:{scaled_h},"
                f"zoompan=z='min(1+{zoom_speed}*on,1.5)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height},fps=30"
            )

        if movement == CameraMovement.ZOOM_OUT_SLOW:
            return (
                f"scale={scaled_w}:{scaled_h},"
                f"zoompan=z='max(1.5-{zoom_speed}*on,1)':d=1:"
                f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={width}x{height},fps=30"
            )

        if movement == CameraMovement.PAN_LEFT:
            pan_speed = 0.3 / total_frames
            return (
                f"scale={scaled_w}:{scaled_h},"
                f"zoompan=z='1.2':d=1:"
                f"x='iw/2-(iw/zoom/2)+{pan_speed}*on*iw':y='ih/2-(ih/zoom/2)':s={width}x{height},fps=30"
            )

        if movement == CameraMovement.PAN_RIGHT:
            pan_speed = 0.3 / total_frames
            return (
                f"scale={scaled_w}:{scaled_h},"
                f"zoompan=z='1.2':d=1:"
                f"x='iw/2-(iw/zoom/2)-{pan_speed}*on*iw':y='ih/2-(ih/zoom/2)':s={width}x{height},fps=30"
            )

        if movement == CameraMovement.SHAKE:
            return "crop=iw-10:ih-10:5+random(0)*5:5+random(1)*5"

        return None

    def get_transition_filter(self, transition: Transition, duration: float = 0.5) -> dict:
        if transition == Transition.CUT:
            return {"type": "cut", "duration": 0}

        if transition == Transition.FADE:
            return {"type": "xfade", "transition": "fade", "duration": duration}

        if transition == Transition.WHIP_PAN_LEFT:
            return {"type": "xfade", "transition": "wipeleft", "duration": duration}

        if transition == Transition.WHIP_PAN_RIGHT:
            return {"type": "xfade", "transition": "wiperight", "duration": duration}

        if transition == Transition.DISSOLVE:
            return {"type": "xfade", "transition": "dissolve", "duration": duration}

        return {"type": "cut", "duration": 0}

    def get_beat_effect_filter(
        self,
        effect: str,
        beat_timing: list[float],
        duration: float,
    ) -> str | None:
        if effect == "shake_on_beat":
            enable_expr = "+".join([f"between(t,{t},{t + 0.2})" for t in beat_timing])
            return f"crop=iw-20:ih-20:10+random(0)*10:10+random(1)*10:enable='{enable_expr}'"

        if effect == "flash_on_beat":
            enable_expr = "+".join([f"between(t,{t},{t + 0.1})" for t in beat_timing])
            return f"eq=brightness=0.2:enable='{enable_expr}'"

        if effect == "zoom_pulse":
            enable_expr = "+".join([f"between(t,{t},{t + 0.3})" for t in beat_timing])
            return f"scale=iw*1.1:ih*1.1:enable='{enable_expr}'"

        return None

    def build_filter_chain(
        self,
        camera_movement: CameraMovement,
        beat_effect: str | None,
        beat_timing: list[float],
        duration: float,
        width: int,
        height: int,
    ) -> list[str]:
        filters = []

        camera_filter = self.get_camera_filter(camera_movement, duration, width, height)
        if camera_filter:
            filters.append(camera_filter)

        if beat_effect:
            beat_filter = self.get_beat_effect_filter(beat_effect, beat_timing, duration)
            if beat_filter:
                filters.append(beat_filter)

        filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
        filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2")

        return filters
