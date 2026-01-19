import json
from pathlib import Path

from google import genai
from google.genai import types

from domains.library.catalog import FootageCatalog, load_catalog_from_directory
from domains.sequencing.models import SequenceMetadata
from domains.sequencing.strategies import SequencingStrategy, load_strategy

PRESETS_DIR = Path("assets/presets")
LIBRARY_INDEX_DIR = Path("assets/library_index")


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
        strategy: str = "default",
        scene_count: int = 10,
    ):
        self.project = project
        self.location = location
        self.model = model
        self.scene_count = scene_count
        self.strategy: SequencingStrategy = load_strategy(strategy)
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self._catalog: FootageCatalog | None = None

    def _load_footage_catalog(self) -> FootageCatalog | None:
        if self._catalog is not None:
            return self._catalog

        if not LIBRARY_INDEX_DIR.exists():
            return None

        json_files = list(LIBRARY_INDEX_DIR.glob("*.json"))
        if not json_files:
            return None

        self._catalog = load_catalog_from_directory(LIBRARY_INDEX_DIR)
        return self._catalog

    def _build_prompt(
        self,
        script: str,
        step_context: dict | None = None,
    ) -> str:
        catalog = self._load_footage_catalog()

        footage_catalog_text = catalog.to_prompt_format() if catalog else None
        product_context = catalog.get_product_context() if catalog else None

        return self.strategy.build_prompt(
            script=script,
            product_context=product_context,
            footage_catalog=footage_catalog_text,
            lottie_presets_section=_format_lottie_presets_section(),
            sfx_presets_section=_format_sfx_presets_section(),
            scene_count=self.scene_count,
            step_context=step_context,
        )

    def _call_llm(self, prompt: str, response_format: str = "application/json") -> str:
        config = types.GenerateContentConfig(
            response_mime_type=response_format,
            temperature=0.7,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )

        if response.text is None:
            raise ValueError("Empty response from model")

        return response.text

    def generate_from_script(
        self,
        script: str,
        output_path: Path | None = None,
        verbose: bool = False,
    ) -> tuple[dict, SequenceMetadata]:
        if verbose:
            print("Generating sequence from script...")
            print(f"  Model: {self.model}")
            print(f"  Strategy: {self.strategy.name}")
            print(f"  Scene count: {self.scene_count}")
            print(f"  Script length: {len(script)} chars")

            catalog = self._load_footage_catalog()
            if catalog:
                print(f"  Footage catalog: {len(catalog.all_clips)} clips")
            else:
                print("  Footage catalog: (not available)")

        if self.strategy.is_multi_step:
            response_text = self._run_multi_step(script, verbose)
        else:
            prompt = self._build_prompt(script)
            response_text = self._call_llm(prompt)

        if verbose:
            print("  Response received, parsing...")

        sequence_data = self._parse_response(response_text)

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

    def _run_multi_step(self, script: str, verbose: bool = False) -> str:
        steps = self.strategy.get_steps()
        step_context: dict = {}
        response_text = ""

        for i, step in enumerate(steps):
            if verbose:
                print(f"  Step {i + 1}/{len(steps)}: {step}")

            step_context["current_step"] = step
            prompt = self._build_prompt(script, step_context)
            response_text = self._call_llm(prompt)

            if i < len(steps) - 1:
                parsed = self.strategy.parse_step_output(step, response_text)
                step_context.update(parsed)
                if verbose and "content_strategy" in parsed:
                    print("    Content strategy generated")

        return response_text

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
