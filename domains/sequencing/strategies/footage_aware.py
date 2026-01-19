from typing import Any

from domains.sequencing.strategies.base import SequencingStrategy

FOOTAGE_AWARE_PROMPT = """You are a video sequence planner for short-form vertical videos (9:16 aspect ratio).

You have access to existing UGC (User Generated Content) footage that should be prioritized in the video.
Your goal is to create a compelling video sequence that makes the best use of the available footage.

## PRODUCT CONTEXT
{product_context}

## AVAILABLE UGC FOOTAGE
Below is the footage library. Each clip has a unique ID that you should reference in candidate_clips.
Prioritize footage with strong appeal points and relevant content types.

{footage_catalog}

## OUTPUT FORMAT

Generate a sequence JSON with the following structure:

```json
{{
  "project_id": "unique_project_id",
  "metadata": {{
    "locale": "detected_locale",
    "context": "inferred_context_description",
    "title": "video_title"
  }},
  "scenario_meta": {{
    "title": "video_title",
    "tone_voice": "energetic|calm|professional|casual",
    "aspect_ratio": "9:16",
    "resolution": [720, 1280],
    "video_type": "ugc_centered"
  }},
  "scenes": [
    {{
      "scene_id": "s01",
      "sequence_order": 1,
      "audio_script": {{
        "text": "narration text for TTS",
        "voice_preset_id": "chirp_v3_korean_female_confident",
        "speed": 1.0
      }},
      "visual_layer": {{
        "type": "existing_footage",
        "prompt": "detailed visual description matching the candidate clips",
        "query_tags": ["tag1", "tag2"],
        "candidate_clips": ["clip_id_1", "clip_id_2"],
        "fallback_gen_prompt": "fallback prompt if no suitable footage found"
      }},
      "text_overlay": {{
        "content": "text to show on screen",
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
      "sync_mode": "audio|visual|beat",
      "duration": null
    }}
  ]
}}
```

## VOICE PRESETS
- chirp_v3_korean_female_confident (Korean, female, confident)
- chirp_v3_korean_female_cynical (Korean, female, cynical tone)
- chirp_v3_korean_female_emphasis (Korean, female, emphasis)
- chirp_v3_korean_female_whisper (Korean, female, whisper)
- chirp_v3_korean_male_confident (Korean, male, confident)

{lottie_presets_section}

{sfx_presets_section}

## GUIDELINES

### Footage-First Approach
1. **Analyze available footage first** - identify the most compelling clips with strong appeal points
2. **Build narrative around footage** - structure the story to showcase the best UGC moments
3. **Match narration to visuals** - write audio_script that complements the selected footage
4. **Use candidate_clips** - list 1-3 clip IDs that would work for each scene (in order of preference)

### Scene Construction
1. Break into logical scenes (typically 3-10 seconds each)
2. For visual_layer.type, prefer "existing_footage" when matching clips exist
3. Use "image_gen" or "motion_graphic_gen" only when no suitable footage available
4. candidate_clips should contain actual clip IDs from the footage catalog above
5. query_tags should help find the clips if candidate_clips don't match

### Content Strategy
1. Start with a hook that grabs attention (pain point or curiosity)
2. Use before/after clips to show transformation
3. Product showcase clips for credibility
4. Usage demo clips to show ease of use
5. End with a strong call-to-action

### Technical Notes
- video_type should be "ugc_centered" to prioritize existing footage
- Each scene's candidate_clips are suggestions - the renderer will verify availability
- fallback_gen_prompt is used if no candidate clips are suitable

## SCRIPT/SCENARIO
{script}

Generate the sequence JSON:"""


class FootageAwareStrategy(SequencingStrategy):
    @property
    def name(self) -> str:
        return "footage_aware"

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
        catalog_block = footage_catalog or "(No footage catalog available - use AI generation)"

        return FOOTAGE_AWARE_PROMPT.format(
            script=script,
            product_context=context_block,
            footage_catalog=catalog_block,
            lottie_presets_section=lottie_presets_section,
            sfx_presets_section=sfx_presets_section,
        )
