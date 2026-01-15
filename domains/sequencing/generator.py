import json
from pathlib import Path

from google import genai
from google.genai import types

from domains.sequencing.models import SequenceMetadata

PRESETS_DIR = Path("assets/presets")

SEQUENCE_GENERATION_PROMPT = """You are a video sequence planner for short-form vertical videos (9:16 aspect ratio).

Given a script/scenario, generate a detailed sequence JSON that can be used to create a video.

IMPORTANT: First, analyze the script to determine:
1. The language/locale (e.g., "ko-KR" for Korean, "en-US" for English)
2. The context/theme (e.g., "skincare advertisement", "tech review", "cooking tutorial")

Then generate a sequence with the following structure:

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
    "video_type": "ugc_centered|ai_generated|mixed"
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
        "type": "image_gen|existing_footage|motion_graphic_gen",
        "prompt": "detailed visual description for AI image/video generation",
        "query_tags": ["tag1", "tag2"],
        "fallback_gen_prompt": "fallback prompt if existing footage not found"
      }},
      "text_overlay": {{
        "content": "text to show on screen",
        "style": "bold_impact_white|bold_impact_red|subtitle_clean",
        "animation": "fade_in|fade_in_up|slide_in_left|bounce|typewriter",
        "position": "top|center|bottom"
      }},
      "lottie_overlays": [
        {{
          "lottie_name": "preset_name",
          "start_time": 0.0,
          "position": "center|top|bottom|top-left|top-right|bottom-left|bottom-right",
          "scale": 0.5
        }}
      ],
      "sound_effects": [
        {{
          "preset_name": "preset_name",
          "volume": 0.5,
          "start_time": 0.0,
          "fade_in": 0.0,
          "fade_out": 0.0
        }}
      ],
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

Voice presets available:
- chirp_v3_korean_female_confident (Korean, female, confident)
- chirp_v3_korean_female_cynical (Korean, female, cynical tone)
- chirp_v3_korean_female_emphasis (Korean, female, emphasis)
- chirp_v3_korean_female_whisper (Korean, female, whisper)
- chirp_v3_korean_male_confident (Korean, male, confident)

{lottie_presets_section}

{sfx_presets_section}

Guidelines:
1. Break the script into logical scenes (typically 3-10 seconds each)
2. Each scene should have clear visual direction
3. Text overlays should highlight key points
4. Use appropriate camera movements and transitions for engagement
5. Match the tone_voice to the script content
6. For visual_layer.type:
   - Use "image_gen" for static visuals that can be AI-generated
   - Use "motion_graphic_gen" for animated/dynamic content
   - Use "existing_footage" if referencing real video clips
7. For video_type (how to acquire visuals):
   - "ugc_centered": Prioritize existing footage library, use AI generation only as fallback
   - "ai_generated": Always use AI to generate images/videos, ignore existing footage
   - "mixed": Follow each scene's visual_layer.type setting (default)
8. lottie_overlays: Use sparingly for emphasis moments (success confirmations, warnings, etc.). Most scenes should have empty array.
9. sound_effects: Use sparingly for key moments. Most scenes should have empty array. Match SFX to visual/narrative beats.

SCRIPT/SCENARIO:
{script}

Generate the sequence JSON:"""


def _load_presets(filename: str) -> dict:
    preset_file = PRESETS_DIR / filename
    if preset_file.exists():
        with open(preset_file, encoding="utf-8") as f:
            return json.load(f)
    return {}


def _format_lottie_presets_section() -> str:
    presets = _load_presets("lottie_presets.json")
    if not presets:
        return "Lottie animation presets: (none available)"

    lines = ["Lottie animation presets available:"]
    for name, info in presets.items():
        desc = info.get("description", "")
        use_case = info.get("use_case", "")
        lines.append(f"- {name}: {desc} (use case: {use_case})")
    return "\n".join(lines)


def _format_sfx_presets_section() -> str:
    presets = _load_presets("sfx_presets.json")
    if not presets:
        return "Sound effect presets: (none available)"

    lines = ["Sound effect presets available:"]
    for name, info in presets.items():
        desc = info.get("description", "")
        use_case = info.get("use_case", "")
        lines.append(f"- {name}: {desc} (use case: {use_case})")
    return "\n".join(lines)


class SequenceGenerator:
    def __init__(
        self,
        project: str | None = None,
        location: str = "global",
        model: str = "gemini-3-flash-preview",
    ):
        self.project = project
        self.location = location
        self.model = model
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )

    def _build_prompt(self, script: str) -> str:
        return SEQUENCE_GENERATION_PROMPT.format(
            script=script,
            lottie_presets_section=_format_lottie_presets_section(),
            sfx_presets_section=_format_sfx_presets_section(),
        )

    def generate_from_script(
        self,
        script: str,
        output_path: Path | None = None,
        verbose: bool = False,
    ) -> tuple[dict, SequenceMetadata]:
        if verbose:
            print("Generating sequence from script...")
            print(f"  Model: {self.model}")
            print(f"  Script length: {len(script)} chars")

        prompt = self._build_prompt(script)

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.7,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )

        if verbose:
            print("  Response received, parsing...")

        if response.text is None:
            raise ValueError("Empty response from model")

        sequence_data = self._parse_response(response.text)

        metadata = SequenceMetadata(
            locale=sequence_data.get("metadata", {}).get("locale", "en-US"),
            context=sequence_data.get("metadata", {}).get("context", ""),
            title=sequence_data.get("metadata", {}).get("title", "Untitled"),
        )

        if verbose:
            print(f"  Detected locale: {metadata.locale}")
            print(f"  Detected context: {metadata.context}")
            print(f"  Scenes: {len(sequence_data.get('scenes', []))}")

        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(sequence_data, f, ensure_ascii=False, indent=2)
            if verbose:
                print(f"  Saved to: {output_path}")

        return sequence_data, metadata

    def generate_from_file(
        self,
        script_path: str | Path,
        output_path: Path | None = None,
        verbose: bool = False,
    ) -> tuple[dict, SequenceMetadata]:
        script_path = Path(script_path)

        if verbose:
            print(f"Reading script from: {script_path}")

        with open(script_path, encoding="utf-8") as f:
            script = f.read()

        if output_path is None:
            output_path = script_path.with_suffix(".sequence.json")

        return self.generate_from_script(script, output_path, verbose)

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
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse sequence JSON: {e}\nResponse: {text[:500]}")
