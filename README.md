# Sequence to Video

DDD-based video generation pipeline from sequence planning data.

## Features

- **Sequencing Domain**: Generate sequence JSON from scripts using Gemini
- **Planning Domain**: Parse sequence JSON into structured scenarios
- **Library Domain**: Index and search existing video footage using Gemini
- **Studio Domain**: Generate TTS (Chirp v3), images (Gemini 3 Pro), videos (Veo 3.1), text animations, Lottie overlays, sound effects
- **Editing Domain**: Compose final video with FFmpeg, apply effects and transitions

## Installation

```bash
uv sync
uv run playwright install chromium
```

## Configuration

```bash
cp .env.example .env
```

Required environment variables:
```
GOOGLE_PROJECT_ID=your-project-id
GCS_BUCKET=your-gcs-bucket
```

## Usage

### Full Pipeline

```bash
# 1. Generate sequence from script
uv run python main.py sequence examples/script.txt -o sequence.json -v

# 2. Render video from sequence
uv run python main.py render sequence.json -o output.mp4 -v

# Or directly from existing sequence JSON
uv run python main.py render examples/sample_sequence.json -o output.mp4
```

### Sequencing Strategies

The sequence generator supports multiple strategies for creating video sequences. Each strategy offers a different approach to utilizing available footage.

```bash
# Default: Script-driven, ignores footage library
uv run python main.py sequence script.txt -o seq.json -v

# Footage-Aware: Considers existing footage while following the script
uv run python main.py sequence script.txt -o seq.json --strategy footage_aware -v

# Appeal-First: Analyzes footage appeal points first, then builds narrative (2-step)
uv run python main.py sequence script.txt -o seq.json --strategy appeal_first -v

# Control scene count (default: 10)
uv run python main.py sequence script.txt --strategy appeal_first --scene-count 8 -v
```

#### Strategy Comparison

| Strategy | Approach | Best For |
|----------|----------|----------|
| `default` | Script-driven, footage-agnostic | AI-generated content, no existing footage |
| `footage_aware` | Script-driven with footage recommendations | Matching script to available UGC |
| `appeal_first` | Footage-driven, 2-step generation | Maximizing impact of existing UGC |

#### How Each Strategy Works

**`default`**
- Single LLM call
- Generates sequence purely from script content
- No awareness of footage library

**`footage_aware`**
- Single LLM call
- Injects footage catalog + product context into prompt
- Recommends `candidate_clips` for each scene based on script requirements
- Output includes clip IDs that best match each scene

**`appeal_first`** (Multi-step)
1. **Step 1 - Appeal Analysis**: Analyzes footage catalog to identify high-impact clips and their marketing appeal
2. **Step 2 - Sequence Generation**: Uses the content strategy from Step 1 to build a narrative that showcases the best footage

```
Footage Catalog → Content Strategy → Sequence JSON
     ↓                   ↓                ↓
 (appeal points)    (narrative arc)   (candidate_clips)
```

#### Output: candidate_clips

When using `footage_aware` or `appeal_first`, scenes include `candidate_clips`:

```json
{
  "scene_id": "s01",
  "visual_layer": {
    "type": "existing_footage",
    "prompt": "Woman checking bloated belly in mirror",
    "candidate_clips": ["비포 컷_clip_000", "비포컷_직장인_clip_001"],
    "query_tags": ["bloating", "body concern"],
    "fallback_gen_prompt": "..."
  }
}
```

During rendering, the `FootageSelector` prioritizes these candidate clips when selecting footage for each scene.

### Index Raw Footage

```bash
# Index all videos in assets/raw_footage (generic analysis)
uv run python main.py index -v

# Index as product UGC (with marketing-focused analysis)
uv run python main.py index --type product_ugc -v

# Index with explicit context file
uv run python main.py index --type product_ugc --context path/to/context.txt -v

# Index single file with context
uv run python main.py index path/to/video.mp4 --type product_ugc --context context.txt -v

# Force re-index all
uv run python main.py index --force -v
```

#### Product Context for UGC Analysis

When using `--type product_ugc`, provide product context via:

1. **`--context` flag** (explicit path):
```bash
uv run python main.py index --type product_ugc --context products/serum_info.txt -v
```

2. **Auto-detection** (place in footage folder):
```
assets/raw_footage/
├── my_product/
│   ├── context.txt      ← Auto-detected
│   ├── ugc_video1.mp4
│   └── ugc_video2.mp4
```

Auto-detected filenames (checked in order): `context.txt`, `product.txt`, `info.txt`

**context.txt example:**
```
Product: VitaC Brightening Serum
Category: Skincare / Serum
Key Ingredients: 15% Vitamin C, Niacinamide, Hyaluronic Acid
Benefits: Brightening, dark spot care, hydration
Target: 20-40s with dull skin tone concerns
USP: Fast absorption, non-sticky texture
```

The analyzer uses this context to:
- Generate product-relevant tags and descriptions
- Identify appeal points specific to the product's benefits
- Better match clips to scene requirements during rendering

### Scene-Level Editing

Individual scenes are automatically saved to `assets/review_output/{project_id}/scenes/` during rendering.

```bash
# Re-render a specific scene (e.g., after modifying sequence.json)
uv run python main.py rerender-scene sequence.json s03 -v

# Reassemble final video from existing scene files
uv run python main.py reassemble sequence.json -o output_v2.mp4 -v
```

Workflow example:
```bash
# 1. Initial render (scenes saved individually)
uv run python main.py render sequence.json -o output.mp4 -v

# 2. Review output, identify issues with scene s03

# 3. Modify sequence.json for s03, then re-render only that scene
uv run python main.py rerender-scene sequence.json s03 -v

# 4. Reassemble all scenes into final video
uv run python main.py reassemble sequence.json -o output_v2.mp4 -v
```

### Web Viewer

Launch an interactive web UI to preview and edit sequence JSON files. The viewer allows real-time editing of scenes, regeneration of individual assets, and scene re-rendering.

```bash
# Launch viewer with a sequence file pre-loaded
uv run python main.py viewer examples/sample_sequence.json

# Launch empty viewer (load file via UI)
uv run python main.py viewer

# Custom host/port
uv run python main.py viewer sequence.json --host 0.0.0.0 --port 8080
```

Open `http://127.0.0.1:8765` in your browser. The viewer provides:

- **Scene List**: Navigate between scenes, see asset status badges
- **Scene Editor**: Edit audio script, visual layer, text overlay, timing, effects
- **Text Overlay**: Toggle on/off, edit content/style/animation, customize font and background colors
- **Lottie Overlays**: Add/remove/edit Lottie animations with position, scale, and timing
- **Sound Effects**: Add/remove/edit SFX with volume, timing, and fade controls
- **Asset Preview**: View generated assets, regenerate individual components
- **Re-render**: Re-render individual scenes or the entire video

Changes are auto-saved to the sequence JSON file when you click "Save Changes".

### Generate Embeddings

Embeddings enable semantic search for footage selection. They are automatically generated during indexing, but you can regenerate them separately:

```bash
# Generate embeddings for all existing indexes (without re-analyzing videos)
uv run python main.py embed -v
```

Use this when:
- You updated the embedding model
- Embeddings were missing from older indexes
- You want to refresh embeddings without full re-indexing

### Convert MOV to MP4

```bash
uv run python scripts/convert_mov_to_mp4.py -v
uv run python scripts/convert_mov_to_mp4.py -v --delete  # Delete original after conversion
```

## Individual Domain Testing

Each domain can be tested independently for development and debugging.

### TTS Generation

```bash
# Generate TTS audio
uv run python scripts/test_tts.py "안녕하세요, 테스트입니다."

# With custom preset and speed
uv run python scripts/test_tts.py "텍스트" -p chirp_v3_korean_female_confident -s 1.2

# List available voice presets
uv run python scripts/test_tts.py --list-presets
```

### Image Generation

```bash
# Generate image with Gemini 3 Pro
uv run python scripts/test_image.py "A modern Korean skincare product on white background"

# Custom size and context
uv run python scripts/test_image.py "Product shot" -W 720 -H 1280 --context "skincare advertisement"
```

### Video Generation (Veo 3.1)

```bash
# Generate video (takes several minutes)
uv run python scripts/test_video.py "A woman applying skincare product" -d 5

# Custom duration (max 8 seconds)
uv run python scripts/test_video.py "Motion graphic animation" -d 8
```

### Text Overlay

```bash
# Generate text overlay video
uv run python scripts/test_text_overlay.py "강력한 효과!" -d 3

# With custom style and animation
uv run python scripts/test_text_overlay.py "텍스트" -s bold_impact_red -a bounce

# List available styles and animations
uv run python scripts/test_text_overlay.py --list-styles
uv run python scripts/test_text_overlay.py --list-animations
```

### Sequence Generation

```bash
# Generate sequence JSON from script file
uv run python scripts/test_sequence.py examples/script.txt -v

# Generate from inline text
uv run python scripts/test_sequence.py "첫 번째 장면: 제품 클로즈업. 두 번째 장면: 사용 후기" -v
```

#### Adding New Sequencing Strategies

To add a custom strategy:

1. Create a new file in `domains/sequencing/strategies/`:

```python
# domains/sequencing/strategies/my_strategy.py
from typing import Any
from domains.sequencing.strategies.base import SequencingStrategy

class MyStrategy(SequencingStrategy):
    @property
    def name(self) -> str:
        return "my_strategy"

    @property
    def is_multi_step(self) -> bool:
        return False  # Set True for multi-step strategies

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
        # Build your custom prompt here
        return f"Your prompt with {script}, {footage_catalog}, etc."
```

2. Register in `domains/sequencing/strategies/__init__.py`:

```python
from domains.sequencing.strategies.my_strategy import MyStrategy

STRATEGIES = {
    "default": DefaultStrategy,
    "footage_aware": FootageAwareStrategy,
    "appeal_first": AppealFirstStrategy,
    "my_strategy": MyStrategy,  # Add here
}
```

3. Update CLI choices in `main.py` (optional, for tab completion):

```python
sequence_parser.add_argument(
    "--strategy",
    choices=["default", "footage_aware", "appeal_first", "my_strategy"],
)
```

### Lottie Overlay

Lottie animations (checkmark, error, warning, etc.) are pre-rendered to ProRes 4444 MOV files with alpha channel for efficient runtime use.

```bash
# List available presets
uv run python scripts/test_lottie.py --list-presets

# Load a preset overlay
uv run python scripts/test_lottie.py success
```

### Sound Effects (SFX)

Pre-downloaded sound effects from Freesound for common UI feedback sounds.

```bash
# List available presets
uv run python scripts/test_sfx.py --list-presets

# Test a preset
uv run python scripts/test_sfx.py success
```

Available presets: `success`, `error`, `warning`, `loading`, `whoosh`, `click`

#### Using SFX in Sequence JSON

```json
{
  "scenes": [
    {
      "scene_id": "s01",
      "sound_effects": [
        {"preset_name": "success", "volume": 0.5, "start_time": 0.5},
        {"preset_name": "whoosh", "volume": 0.3, "start_time": 1.0, "fade_out": 0.2}
      ]
    }
  ]
}
```

SFX options:
- `preset_name`: Sound effect preset name (required)
- `volume`: Volume level 0.0-1.0 (default: 0.5)
- `start_time`: Start time in seconds (default: 0.0)
- `fade_in`: Fade in duration in seconds (default: 0.0)
- `fade_out`: Fade out duration in seconds (default: 0.0)

#### Adding New Lottie Animations

1. Download Lottie JSON files from [LottieFiles](https://lottiefiles.com) or [IconScout](https://iconscout.com/lottie-animations)
2. Place JSON files in `assets/stock/lottie/`
3. Convert to MOV:

```bash
# Convert all Lottie JSON files to MOV
uv run python scripts/convert_lottie_to_mov.py -v

# Convert with custom size
uv run python scripts/convert_lottie_to_mov.py -W 1080 -H 1080 -v

# Force re-convert existing files
uv run python scripts/convert_lottie_to_mov.py --force -v
```

Output MOV files are saved to `assets/stock/lottie_mov/` and can be used as overlays in video composition.

### Managing Presets

Preset definitions for Lottie overlays and sound effects are stored in `assets/presets/`. The sequence generator reads these files to include available presets in the generation prompt.

```
assets/presets/
├── lottie_presets.json   # Lottie animation presets with descriptions
└── sfx_presets.json      # Sound effect presets with descriptions
```

Each preset includes:
- `description`: What the preset is (shown to LLM during sequence generation)
- `use_case`: When to use it (helps LLM make appropriate selections)

#### Syncing Presets

When you add new Lottie animations or sound effects to the providers, sync the preset files:

```bash
# Check for differences without modifying files
uv run python scripts/update_presets.py --check

# Sync preset files (adds new presets, removes stale ones)
uv run python scripts/update_presets.py
```

The script will:
- Add new presets with placeholder descriptions (edit manually)
- Remove presets that no longer exist in providers
- Preserve existing descriptions for unchanged presets

After syncing, edit the JSON files to add meaningful descriptions for new presets.

## Project Structure

```
domains/
├── sequencing/  # Script → Sequence JSON (Gemini 3 Flash)
│   ├── generator.py           # SequenceGenerator with strategy support
│   └── strategies/            # Pluggable sequencing strategies
│       ├── base.py            # SequencingStrategy ABC
│       ├── default.py         # Script-driven (no footage awareness)
│       ├── footage_aware.py   # Script + footage catalog integration
│       └── appeal_first.py    # 2-step: appeal analysis → sequence
├── planning/    # Sequence JSON parsing
├── library/     # Video asset indexing & search (Gemini 3 Flash)
│   ├── catalog.py             # FootageCatalog for LLM-friendly summaries
│   └── ...
├── studio/      # Content generation
│   ├── tts_generator.py       # Google Cloud TTS (Chirp v3)
│   ├── image_generator.py     # Gemini 3 Pro Image
│   ├── video_generator.py     # Veo 3.1 (us-central1 only)
│   ├── text_renderer.py       # Playwright + FFmpeg text overlays
│   ├── lottie_renderer.py     # Pre-rendered Lottie MOV loader
│   ├── sfx_provider.py        # Pre-downloaded sound effects
│   └── fallback_generator.py  # Black screen fallback
└── editing/     # FFmpeg composition
    ├── composer.py   # Scene orchestration
    ├── renderer.py   # FFmpeg rendering
    └── effects.py    # Camera movements, transitions

infrastructure/
├── config.py    # Configuration management
├── cache.py     # Asset caching
└── metadata.py  # Generation metadata tracking

viewer/
└── server.py    # FastAPI web viewer for sequence editing

scripts/
├── test_tts.py              # TTS testing
├── test_image.py            # Image generation testing
├── test_video.py            # Video generation testing
├── test_text_overlay.py     # Text overlay testing
├── test_lottie.py           # Lottie overlay testing
├── test_sfx.py              # Sound effects testing
├── test_sequence.py         # Sequence generation testing
├── convert_lottie_to_mov.py # Lottie JSON → MOV conversion
├── convert_mov_to_mp4.py    # Format conversion
└── update_presets.py        # Sync preset JSON files from providers

assets/
├── presets/      # Preset definitions for sequence generation
│   ├── lottie_presets.json
│   └── sfx_presets.json
└── stock/
    ├── lottie/       # Source Lottie JSON files
    ├── lottie_mov/   # Pre-rendered MOV files (ProRes 4444 with alpha)
    └── sfx/          # Pre-downloaded sound effect MP3 files
```

## Model Configuration

| Purpose | Model | Location |
|---------|-------|----------|
| Sequence Generation | gemini-3-flash-preview | global |
| Video Analysis | gemini-3-flash-preview | global |
| Footage Selection | gemini-2.0-flash | global |
| Embedding | text-embedding-005 | global |
| Image Generation | gemini-3-pro-image-preview | global |
| Video Generation | veo-3.1-generate-preview | us-central1 (required) |
| TTS | Chirp3-HD (ko-KR) | - |

## Footage Selection

When rendering with existing footage (`video_type: ugc_centered` or `mixed`), the system uses a two-stage selection process:

### Stage 1: Embedding-Based Search

Clips are pre-filtered using semantic similarity:
- Each clip has an embedding generated from its description, appeal points, and tags
- Scene requirements (narration + visual prompt + query tags) are embedded as a query
- Top candidates are retrieved using cosine similarity

### Stage 2: LLM-Based Selection

The LLM evaluates the top candidates and selects the best match:
1. **Indexing**: Footage is analyzed and tagged with descriptions, appeal points, content types
2. **Selection**: For each scene, LLM evaluates candidate clips against scene requirements (narration, visual prompt, tags)
3. **Fallback**: If no suitable clip found, falls back to AI image generation

This two-stage approach balances speed (embedding search) with accuracy (LLM reasoning).

## Caching

Generated assets are cached by default in `assets/generated/.cache/`.

```bash
# Disable cache for render
uv run python main.py render input.json -o output.mp4 --no-cache
```

## Metadata

Generation metadata (prompts, parameters) is saved in `assets/generated/.metadata/` for each generated asset.

Composition metadata is saved alongside output videos as `{output}.meta.json`, containing:
- Project settings (resolution, fps, total duration)
- Per-scene details (sources, effects, rendered file paths)
- Creation timestamp
