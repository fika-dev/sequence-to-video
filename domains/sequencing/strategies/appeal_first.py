import json
from typing import Any

from domains.sequencing.strategies.base import SequencingStrategy

STEP1_APPEAL_ANALYSIS_PROMPT = """You are a creative director analyzing UGC footage for a product advertisement.

## PRODUCT CONTEXT
{product_context}

## AVAILABLE UGC FOOTAGE (with appeal points)
{footage_catalog}

## YOUR TASK

Analyze the footage and create a **content strategy** that maximizes the appeal of the available clips.

For each compelling clip, determine:
1. **Why it's powerful** - what emotional/logical appeal does it trigger?
2. **How to frame it** - what narration/context amplifies its impact?
3. **Where in the narrative** - hook, problem, solution, proof, or CTA?

Output a JSON strategy document:

```json
{{
  "narrative_arc": {{
    "hook": "Brief description of the opening hook strategy",
    "problem": "How to present the pain point using footage",
    "solution": "How to introduce the product as the answer",
    "proof": "How to show credibility/results",
    "cta": "How to close with action"
  }},
  "key_clips": [
    {{
      "clip_id": "actual_clip_id_from_catalog",
      "appeal_type": "emotional|logical|social_proof|transformation|lifestyle",
      "narrative_role": "hook|problem|solution|proof|cta",
      "framing_suggestion": "How to present this clip - what narration, what emphasis",
      "priority": 1
    }}
  ],
  "tone_recommendation": "energetic|calm|professional|casual|urgent",
  "key_messages": ["message1", "message2", "message3"]
}}
```

Focus on:
- Clips with the strongest appeal_point in the catalog
- Before/after comparisons for transformation
- Relatable pain point moments
- Product usage that looks effortless
- Authentic reactions/testimonials

Select {scene_count} key clips maximum, prioritized by impact.

Generate the strategy JSON:"""

STEP2_SEQUENCE_GENERATION_PROMPT = """You are a video sequence planner creating a short-form vertical video (9:16).

## CONTENT STRATEGY (from creative director)
{content_strategy}

## PRODUCT CONTEXT
{product_context}

## AVAILABLE FOOTAGE
{footage_catalog}

## YOUR TASK

Based on the content strategy above, generate a detailed sequence JSON with exactly {scene_count} scenes.

Follow the narrative arc and use the key clips identified in the strategy.
Each scene should align with the framing suggestions provided.

Output format:

```json
{{
  "project_id": "unique_project_id",
  "metadata": {{
    "locale": "ko-KR",
    "context": "inferred_context",
    "title": "video_title"
  }},
  "scenario_meta": {{
    "title": "video_title",
    "tone_voice": "from_strategy_recommendation",
    "aspect_ratio": "9:16",
    "resolution": [720, 1280],
    "video_type": "ugc_centered"
  }},
  "scenes": [
    {{
      "scene_id": "s01",
      "sequence_order": 1,
      "audio_script": {{
        "text": "narration following the framing suggestion",
        "voice_preset_id": "chirp_v3_korean_female_confident",
        "speed": 1.0
      }},
      "visual_layer": {{
        "type": "existing_footage",
        "prompt": "visual description",
        "query_tags": ["tag1", "tag2"],
        "candidate_clips": ["clip_id_from_strategy"],
        "fallback_gen_prompt": "fallback if clip unavailable"
      }},
      "text_overlay": {{
        "content": "key text",
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
1. Follow the narrative_arc from the strategy
2. Use candidate_clips from the key_clips list
3. Write audio_script.text following the framing_suggestion
4. Match tone_voice to the strategy's tone_recommendation
5. Incorporate key_messages naturally into narration
6. Create exactly {scene_count} scenes

Generate the sequence JSON:"""


class AppealFirstStrategy(SequencingStrategy):
    @property
    def name(self) -> str:
        return "appeal_first"

    @property
    def is_multi_step(self) -> bool:
        return True

    def get_steps(self) -> list[str]:
        return ["analyze_appeal", "generate_sequence"]

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

        current_step = (step_context or {}).get("current_step", "analyze_appeal")

        if current_step == "analyze_appeal":
            return STEP1_APPEAL_ANALYSIS_PROMPT.format(
                product_context=context_block,
                footage_catalog=catalog_block,
                scene_count=scene_count,
            )
        else:
            content_strategy = (step_context or {}).get("content_strategy", "{}")
            return STEP2_SEQUENCE_GENERATION_PROMPT.format(
                content_strategy=content_strategy,
                product_context=context_block,
                footage_catalog=catalog_block,
                scene_count=scene_count,
                lottie_presets_section=lottie_presets_section,
                sfx_presets_section=sfx_presets_section,
            )

    def parse_step_output(self, step: str, output: str) -> dict[str, Any]:
        if step == "analyze_appeal":
            text = output.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            try:
                strategy = json.loads(text.strip())
                return {"content_strategy": json.dumps(strategy, ensure_ascii=False, indent=2)}
            except json.JSONDecodeError:
                return {"content_strategy": text}
        return {}
