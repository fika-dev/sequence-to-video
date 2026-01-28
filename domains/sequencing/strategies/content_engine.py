"""Content Engine Strategy - Uses AI-generated script and visual outlay."""

from typing import Any

from domains.sequencing.strategies.base import SequencingStrategy


class ContentEngineStrategy(SequencingStrategy):
    """Strategy that uses content_engine to generate script and visual planning."""
    
    @property
    def name(self) -> str:
        return "content_engine"
    
    @property
    def is_multi_step(self) -> bool:
        return False  # Content engine handles multi-step internally
    
    def build_prompt(
        self,
        script: str,
        product_context: str | None = None,
        footage_catalog: str | None = None,
        lottie_presets_section: str = "",
        sfx_presets_section: str = "",
        scene_count: int = 10,
        step_context: dict[str, Any] | None = None,
        # New: Content engine specific input
        content_plan: dict | None = None,
    ) -> str:
        """
        Build prompt for sequence generation from content_engine output.
        
        Args:
            content_plan: FinalContentPlan dict with polished_script, directions, visual_outlay
        """
        if content_plan:
            return self._build_prompt_from_content_plan(
                content_plan=content_plan,
                footage_catalog=footage_catalog,
                product_context=product_context,
                lottie_presets_section=lottie_presets_section,
                sfx_presets_section=sfx_presets_section,
                scene_count=scene_count,
            )
        
        # Fallback: use script directly (backward compatibility)
        return self._build_prompt_from_script(
            script=script,
            footage_catalog=footage_catalog,
            product_context=product_context,
            lottie_presets_section=lottie_presets_section,
            sfx_presets_section=sfx_presets_section,
            scene_count=scene_count,
        )
    
    def _build_prompt_from_content_plan(
        self,
        content_plan: dict,
        footage_catalog: str | None,
        product_context: str | None,
        lottie_presets_section: str,
        sfx_presets_section: str,
        scene_count: int,
    ) -> str:
        """Build prompt using content_engine's visual outlay and directions."""
        
        polished_script = content_plan.get("polished_script", "")
        visual_outlay = content_plan.get("visual_outlay", {})
        directions = content_plan.get("directions", [])
        
        # Build visual outlay section
        visual_outlay_text = self._format_visual_outlay(visual_outlay)
        
        # Build directions section
        directions_text = self._format_directions(directions)
        
        prompt = f"""You are a video sequence planner for short-form vertical videos (9:16 aspect ratio).

You are generating a sequence JSON from an AI-generated script and visual outlay created by the content engine.

## SCRIPT
{polished_script}

## VISUAL OUTLAY
The content engine has already planned visual scenes. Use these as guidance:
{visual_outlay_text}

## DIRECTING INSTRUCTIONS
The content engine has provided these directing instructions:
{directions_text}

{f"## PRODUCT CONTEXT\n{product_context}\n" if product_context else ""}
{f"## AVAILABLE FOOTAGE\n{footage_catalog}\n" if footage_catalog else ""}

{lottie_presets_section}

{sfx_presets_section}

## TASK
Convert the script, visual outlay, and directions into a sequence JSON with the following structure:

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
    "video_type": "ai_generated|ugc_centered|mixed"
  }},
  "scenes": [
    {{
      "scene_id": "s01",
      "sequence_order": 1,
      "audio_script": {{
        "text": "narration text from script",
        "voice_preset_id": "chirp_v3_korean_female_confident",
        "speed": 1.0
      }},
      "visual_layer": {{
        "type": "image_gen|existing_footage|motion_graphic_gen",
        "prompt": "visual_generation_prompt from visual_outlay",
        "query_tags": ["tag1", "tag2"],
        "fallback_gen_prompt": "fallback prompt"
      }},
      "text_overlay": {{
        "content": "subtitles from visual_outlay",
        "style": "bold_impact_white|bold_impact_red|subtitle_clean",
        "animation": "fade_in|fade_in_up|slide_in_left|bounce|typewriter",
        "position": "top|center|bottom"
      }},
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

## GUIDELINES

1. **Map Visual Outlay to Scenes**: Each scene in visual_outlay should become a scene in the sequence
2. **Use Visual Prompts**: Use visual_generation_prompt from visual_outlay for visual_layer.prompt
3. **Map Visual Types**: 
   - visual_type: "image" → visual_layer.type: "image_gen"
   - visual_type: "video" → visual_layer.type: "motion_graphic_gen"
4. **Use Subtitles**: Map visual_outlay.subtitles to text_overlay.content
5. **Apply Directions**: Convert direction instructions to appropriate sequence fields:
   - "transition" → fx_beat.transition_next
   - "text_overlay" → text_overlay
   - "animation" → lottie_overlays
   - "effect" → fx_beat.effect
6. **Break Script**: Split polished_script into scenes matching visual_outlay scenes
7. **Match Audio to Visuals**: Ensure audio_script.text aligns with visual_outlay.subtitles

Generate the sequence JSON:"""
        
        return prompt
    
    def _format_visual_outlay(self, visual_outlay: dict) -> str:
        """Format visual outlay for prompt."""
        if not visual_outlay or not visual_outlay.get("scenes"):
            return "No visual outlay provided."
        
        lines = ["Visual scenes planned:"]
        for scene in visual_outlay.get("scenes", []):
            lines.append(f"\nScene {scene.get('scene_number', '?')}:")
            lines.append(f"  Description: {scene.get('scene_description', '')}")
            lines.append(f"  Subtitles: {scene.get('subtitles', '')}")
            lines.append(f"  Visual Type: {scene.get('visual_type', 'image')}")
            lines.append(f"  Generation Prompt: {scene.get('visual_generation_prompt', '')}")
        
        return "\n".join(lines)
    
    def _format_directions(self, directions: list) -> str:
        """Format directions for prompt."""
        if not directions:
            return "No directing instructions provided."
        
        lines = ["Directing instructions:"]
        for direction in directions:
            inst_type = direction.get("instruction_type", "general")
            instruction = direction.get("instruction", "")
            lines.append(f"  [{inst_type}]: {instruction}")
        
        return "\n".join(lines)
    
    def _build_prompt_from_script(
        self,
        script: str,
        footage_catalog: str | None,
        product_context: str | None,
        lottie_presets_section: str,
        sfx_presets_section: str,
        scene_count: int,
    ) -> str:
        """Fallback: build prompt from script only (backward compatibility)."""
        # Similar to DefaultStrategy for backward compatibility
        from domains.sequencing.strategies.default import SEQUENCE_GENERATION_PROMPT
        
        return SEQUENCE_GENERATION_PROMPT.format(
            script=script,
            lottie_presets_section=lottie_presets_section,
            sfx_presets_section=sfx_presets_section,
        )
