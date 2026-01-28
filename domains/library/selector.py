import json

from google import genai
from google.genai import types

from domains.library.models import VideoClip


SELECTION_PROMPT = """You are a video editor selecting the best footage clip for a specific scene.

SCENE REQUIREMENTS:
- Audio/Narration: {audio_text}
- Visual Description: {visual_prompt}
- Required Duration: {min_duration:.1f}+ seconds
- Tags: {query_tags}

AVAILABLE CLIPS:
{clips_summary}

INSTRUCTIONS:
1. Analyze the scene requirements (narration content, visual needs, mood)
2. Review each available clip's description, appeal point, and context
3. Select the SINGLE BEST clip that matches the scene's intent and message
4. If no clip is suitable, respond with "NONE"

Respond in JSON format:
{{
  "selected_clip_id": "clip_id or NONE",
  "reason": "Brief explanation of why this clip fits the scene"
}}"""


class FootageSelector:
    def __init__(
        self,
        project: str | None = None,
        location: str = "global",
        model: str = "gemini-2.5-flash-lite-preview-06-17",
    ):
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self.model = model

    def select_clip(
        self,
        clips: list[VideoClip],
        audio_text: str,
        visual_prompt: str,
        query_tags: list[str],
        min_duration: float,
        candidate_clip_ids: list[str] | None = None,
        verbose: bool = False,
    ) -> VideoClip | None:
        if not clips:
            return None

        eligible_clips = [c for c in clips if c.duration >= min_duration]
        if not eligible_clips:
            eligible_clips = clips

        if candidate_clip_ids:
            prioritized = self._prioritize_candidates(eligible_clips, candidate_clip_ids)
            if prioritized:
                eligible_clips = prioritized
                if verbose:
                    print(f"    [SELECTOR] Prioritizing {len(prioritized)} candidate clips")

        clips_summary = self._build_clips_summary(eligible_clips)

        prompt = SELECTION_PROMPT.format(
            audio_text=audio_text,
            visual_prompt=visual_prompt,
            min_duration=min_duration,
            query_tags=", ".join(query_tags) if query_tags else "(none)",
            clips_summary=clips_summary,
        )

        if verbose:
            print(f"    [SELECTOR] Evaluating {len(eligible_clips)} clips...")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )

        result = self._parse_response(response.text or "")

        selected_id = result.get("selected_clip_id")
        if not selected_id or selected_id == "NONE":
            if verbose:
                print(f"    [SELECTOR] No suitable clip found")
            return None

        if verbose:
            reason = result.get("reason", "")
            print(f"    [SELECTOR] Selected: {selected_id}")
            print(f"    [SELECTOR] Reason: {reason[:80]}...")

        normalized_id = selected_id.strip("[]")
        for clip in eligible_clips:
            if clip.clip_id == selected_id or clip.clip_id == normalized_id:
                return clip

        return None

    def _prioritize_candidates(
        self, clips: list[VideoClip], candidate_ids: list[str]
    ) -> list[VideoClip]:
        candidate_set = set(candidate_ids)
        candidates = [c for c in clips if c.clip_id in candidate_set]

        if not candidates:
            return []

        order_map = {cid: i for i, cid in enumerate(candidate_ids)}
        candidates.sort(key=lambda c: order_map.get(c.clip_id, len(candidate_ids)))

        return candidates

    def _build_clips_summary(self, clips: list[VideoClip]) -> str:
        summaries = []
        for clip in clips:
            summary_parts = [
                f"[{clip.clip_id}]",
                f"  Duration: {clip.duration:.1f}s",
                f"  Description: {clip.description}",
            ]
            if clip.appeal_point:
                summary_parts.append(f"  Appeal: {clip.appeal_point}")
            if clip.content_type:
                summary_parts.append(f"  Type: {clip.content_type}")
            if clip.usage_context:
                summary_parts.append(f"  Context: {clip.usage_context}")
            if clip.tags:
                summary_parts.append(f"  Tags: {', '.join(clip.tags)}")

            summaries.append("\n".join(summary_parts))

        return "\n\n".join(summaries)

    def _parse_response(self, response_text: str) -> dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            return {"selected_clip_id": "NONE", "reason": "Failed to parse response"}
