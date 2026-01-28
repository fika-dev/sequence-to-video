from __future__ import annotations

import json
from typing import Any

from domains.sequencing.strategies.base import SequencingStrategy

STEP1_BLUEPRINT_PROMPT = """You are a performance creative director creating an ad BLUEPRINT from reference ads.

## PRODUCT CONTEXT
{product_context}

## SCRIPT (if provided)
{script}

## SELECTED REFERENCE ADS (abstract patterns, do not copy verbatim)
{references_summary}

## YOUR TASK

Create a reusable ad BLUEPRINT that:
1. Follows the most effective framework from references
2. Uses similar pacing and timing
3. Adapts the narrative structure to the new product

OUTPUT JSON ONLY:
{{
  "target_framework": "hook_body_cta|aida|pas|hpscpta|hook_story_offer",
  "pacing_targets": {{
    "hook_duration": 3.0,
    "first_product_reveal_time": 4.0,
    "first_cta_time": 12.0,
    "total_duration": 15.0
  }},
  "style_rules": {{
    "tone": "description of tone",
    "text_overlay_style": "description of text style",
    "music_mood": "description of music"
  }},
  "reusable_patterns": ["pattern1", "pattern2"],
  "beat_plan": [
    {{
      "beat_id": "bp01",
      "narrative_role": "hook|problem|agitate|solution|proof|offer|cta",
      "intent": "one sentence describing what this beat should achieve",
      "required_footage_type": "testimonial|before_after|usage_demo|product_showcase|lifestyle|any",
      "hook_technique": "question|bold_claim|pattern_interrupt|relatable_pain|null",
      "overlay_intent": ["short phrases for text overlay, not final copy"],
      "target_duration": 3.0
    }}
  ]
}}

CONSTRAINTS:
- Create exactly {scene_count} beats
- Match reference pacing targets as closely as possible
- Each beat should be 2-6 seconds
- Total duration should match reference average

Generate the blueprint JSON:"""

STEP2_CAST_BEATS_PROMPT = """You are a video editor selecting footage for each beat of an ad.

## BLUEPRINT
{blueprint}

## AVAILABLE UGC FOOTAGE
{footage_catalog}

## YOUR TASK

For each beat in the blueprint, select the best 1-3 clips from the footage catalog.
Match clips to the beat's narrative_role, intent, and required_footage_type.

OUTPUT JSON ONLY:
{{
  "beat_casting": [
    {{
      "beat_id": "bp01",
      "candidate_clips": ["clip_id_1", "clip_id_2"],
      "query_tags": ["tag1", "tag2"],
      "fallback_gen_prompt": "If no clip fits, describe what to generate",
      "casting_notes": "Why these clips were selected"
    }}
  ]
}}

RULES:
- Only use clip_ids that exist in the footage catalog
- If no clip truly fits the beat, set candidate_clips to [] and provide a strong fallback_gen_prompt
- Prefer clips with matching content_type and appeal_point
- Consider clip duration vs beat target_duration
- Avoid reusing the same clip for multiple beats

Generate the casting JSON:"""

STEP3_SEQUENCE_PROMPT = """You are a video sequence planner creating a short-form vertical video (9:16).

## BLUEPRINT (structure and timing)
{blueprint}

## BEAT CASTING (selected footage per beat)
{beat_casting}

## PRODUCT CONTEXT
{product_context}

## YOUR TASK

Generate the final sequence JSON combining the blueprint structure with the casted footage.

OUTPUT FORMAT:
{{
  "project_id": "unique_project_id",
  "metadata": {{
    "locale": "ko-KR",
    "context": "inferred_context",
    "title": "video_title"
  }},
  "scenario_meta": {{
    "title": "video_title",
    "tone_voice": "from_blueprint_style_rules",
    "aspect_ratio": "9:16",
    "resolution": [720, 1280],
    "video_type": "ugc_centered"
  }},
  "scenes": [
    {{
      "scene_id": "s01",
      "sequence_order": 1,
      "audio_script": {{
        "text": "narration that achieves the beat intent",
        "voice_preset_id": "chirp_v3_korean_female_confident",
        "speed": 1.0
      }},
      "visual_layer": {{
        "type": "existing_footage",
        "prompt": "visual description matching the beat",
        "query_tags": ["from_casting"],
        "candidate_clips": ["from_casting"],
        "fallback_gen_prompt": "from_casting_fallback"
      }},
      "text_overlay": {{
        "content": "based on overlay_intent from blueprint",
        "style": "bold_impact_white|bold_impact_red|subtitle_clean",
        "animation": "fade_in|fade_in_up|slide_in_left|bounce|typewriter",
        "position": "top|center|bottom"
      }},
      "lottie_overlays": [],
      "sound_effects": [],
      "fx_beat": {{
        "camera_movement": "none|zoom_in_slow|zoom_out_slow|pan_left|pan_right|shake",
        "transition_next": "cut|fade|whip_pan_left|whip_pan_right|dissolve"
      }},
      "sync_mode": "audio",
      "duration": null
    }}
  ]
}}

## VOICE PRESETS
- chirp_v3_korean_female_confident (Korean, female, confident)
- chirp_v3_korean_female_cynical (Korean, female, cynical tone)
- chirp_v3_korean_female_emphasis (Korean, female, emphasis)
- chirp_v3_korean_female_whisper (Korean, female, whisper)
- chirp_v3_korean_male_confident (Korean, male, confident)

{lottie_presets_section}

{sfx_presets_section}

## GUIDELINES
1. Follow the blueprint's pacing_targets strictly (hook timing, CTA timing)
2. Use the beat_casting's candidate_clips for each scene
3. Write audio_script.text that achieves the beat's intent
4. Apply style_rules from blueprint to text overlays and tone
5. Use reusable_patterns to guide narration style
6. Create exactly {scene_count} scenes

Generate the sequence JSON:"""


class ReferenceGuidedStrategy(SequencingStrategy):
    @property
    def name(self) -> str:
        return "reference_guided"

    @property
    def is_multi_step(self) -> bool:
        return True

    def get_steps(self) -> list[str]:
        return ["build_blueprint", "cast_beats", "generate_sequence"]

    def build_prompt(
        self,
        script: str,
        product_context: str | None = None,
        footage_catalog: str | None = None,
        lottie_presets_section: str = "",
        sfx_presets_section: str = "",
        scene_count: int = 10,
        step_context: dict[str, Any] | None = None,
    ) -> str:
        context_block = product_context or "(No product context provided)"
        catalog_block = footage_catalog or "(No footage catalog available)"
        script_block = script if script.strip() else "(No script provided - generate based on product context)"

        current_step = (step_context or {}).get("current_step", "build_blueprint")
        references_summary = (step_context or {}).get("references_summary", "(No references available)")

        if current_step == "build_blueprint":
            return STEP1_BLUEPRINT_PROMPT.format(
                product_context=context_block,
                script=script_block,
                references_summary=references_summary,
                scene_count=scene_count,
            )
        elif current_step == "cast_beats":
            blueprint = (step_context or {}).get("blueprint", "{}")
            return STEP2_CAST_BEATS_PROMPT.format(
                blueprint=blueprint,
                footage_catalog=catalog_block,
            )
        else:
            blueprint = (step_context or {}).get("blueprint", "{}")
            beat_casting = (step_context or {}).get("beat_casting", "{}")
            return STEP3_SEQUENCE_PROMPT.format(
                blueprint=blueprint,
                beat_casting=beat_casting,
                product_context=context_block,
                scene_count=scene_count,
                lottie_presets_section=lottie_presets_section,
                sfx_presets_section=sfx_presets_section,
            )

    def parse_step_output(self, step: str, output: str) -> dict[str, Any]:
        text = output.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            parsed = json.loads(text.strip())
            formatted = json.dumps(parsed, ensure_ascii=False, indent=2)

            if step == "build_blueprint":
                return {"blueprint": formatted}
            elif step == "cast_beats":
                return {"beat_casting": formatted}
        except json.JSONDecodeError:
            if step == "build_blueprint":
                return {"blueprint": text}
            elif step == "cast_beats":
                return {"beat_casting": text}

        return {}
