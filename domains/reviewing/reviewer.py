from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from PIL import Image

from domains.library.reference_store import ReferenceRepositoryAdapter, ReferenceStore
from domains.reviewing.models import (
    DeterministicCheckResult,
    ExtractionResult,
    SequenceReview,
)
from domains.reviewing.prompts import (
    EXTRACTION_PROMPT,
    JUDGEMENT_PROMPT,
    JUDGEMENT_PROMPT_WITH_VISUAL,
    REFERENCE_BENCHMARK_SECTION,
)
from domains.reviewing.thumbnail_grid import create_thumbnail_grid

REFERENCES_DIR = Path("assets/references")
LIBRARY_INDEX_DIR = Path("assets/library_index")
GENERATED_DIR = Path("assets/generated")


class SequenceReviewer:
    def __init__(
        self,
        project: str | None = None,
        location: str = "global",
        model: str = "gemini-3-flash-preview",
        library_index_dir: Path | None = None,
        generated_dir: Path | None = None,
    ):
        self.project = project
        self.location = location
        self.model = model
        self.library_index_dir = library_index_dir or LIBRARY_INDEX_DIR
        self.generated_dir = generated_dir or GENERATED_DIR
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self._reference_repo: Optional[ReferenceRepositoryAdapter] = None

    def review(
        self,
        sequence_path: Path | str,
        with_references: bool = False,
        with_visuals: bool = True,
        verbose: bool = False,
    ) -> SequenceReview:
        sequence_path = Path(sequence_path)

        if verbose:
            print(f"Reviewing sequence: {sequence_path}")
            print(f"  Model: {self.model}")

        with open(sequence_path, encoding="utf-8") as f:
            sequence_data = json.load(f)

        if verbose:
            print(f"  Scenes: {len(sequence_data.get('scenes', []))}")

        extraction = self._step1_extract(sequence_data, verbose)

        deterministic_result = self._run_deterministic_checks(extraction)

        if verbose and deterministic_result.issues:
            print(f"  Deterministic issues: {len(deterministic_result.issues)}")
            for issue in deterministic_result.issues:
                print(f"    - {issue}")

        reference_section = ""
        if with_references:
            reference_section = self._prepare_reference_section(sequence_data, verbose)

        thumbnail_grid = None
        if with_visuals:
            thumbnail_grid = self._generate_thumbnail_grid(sequence_data, verbose)

        review = self._step2_judge(
            extraction,
            deterministic_result,
            reference_section,
            thumbnail_grid,
            verbose,
        )

        review.deterministic_issues = deterministic_result.issues

        return review

    def _generate_thumbnail_grid(
        self,
        sequence_data: dict,
        verbose: bool = False,
    ) -> Image.Image | None:
        if verbose:
            print("  Generating thumbnail grid...")

        try:
            grid = create_thumbnail_grid(
                sequence_data=sequence_data,
                library_index_dir=self.library_index_dir,
                generated_dir=self.generated_dir,
                verbose=verbose,
            )

            if verbose:
                print(f"    Grid size: {grid.size[0]}x{grid.size[1]}")

            return grid
        except Exception as e:
            if verbose:
                print(f"    Failed to generate thumbnail grid: {e}")
            return None

    def _step1_extract(self, sequence_data: dict, verbose: bool = False) -> ExtractionResult:
        if verbose:
            print("  Step 1: Extraction...")

        sequence_json = json.dumps(sequence_data, ensure_ascii=False, indent=2)
        prompt = EXTRACTION_PROMPT.format(sequence_json=sequence_json)

        response_text = self._call_llm(prompt)
        extraction_data = self._parse_response(response_text)

        extraction = ExtractionResult(**extraction_data)

        if verbose:
            print(f"    Beats extracted: {len(extraction.beats)}")
            print(f"    Flow issues: {len(extraction.flow.flow_issues)}")
            if extraction.flow.core_message:
                print(f"    Core message: {extraction.flow.core_message[:50]}...")

        return extraction

    def _step2_judge(
        self,
        extraction: ExtractionResult,
        deterministic_result: DeterministicCheckResult,
        reference_section: str,
        thumbnail_grid: Image.Image | None,
        verbose: bool = False,
    ) -> SequenceReview:
        if verbose:
            print("  Step 2: Judgement...")
            if thumbnail_grid:
                print("    (with visual grid)")

        extraction_json = extraction.model_dump_json(indent=2)
        deterministic_issues = "\n".join(
            [f"- {issue}" for issue in deterministic_result.issues]
        ) or "(No issues detected)"

        if thumbnail_grid:
            prompt = JUDGEMENT_PROMPT_WITH_VISUAL.format(
                extraction_json=extraction_json,
                deterministic_issues=deterministic_issues,
                reference_section=reference_section,
            )
            response_text = self._call_llm_with_image(prompt, thumbnail_grid)
        else:
            prompt = JUDGEMENT_PROMPT.format(
                extraction_json=extraction_json,
                deterministic_issues=deterministic_issues,
                reference_section=reference_section,
            )
            response_text = self._call_llm(prompt)

        review_data = self._parse_response(response_text)

        if isinstance(review_data, list):
            review_data = review_data[0] if review_data else {}

        if "reviewed_at" not in review_data:
            review_data["reviewed_at"] = datetime.now().isoformat()

        review = SequenceReview(**review_data)

        if verbose:
            print(f"    Overall score: {review.persuasion_score.overall}/10")
            print(f"    Visual fixes: {len(review.visual_fixes)}")
            print(f"    Script fixes: {len(review.script_fixes)}")
            print(f"    Flow fixes: {len(review.flow_fixes)}")
            print(f"    Action items: {len(review.action_items)}")

        return review

    def _run_deterministic_checks(self, extraction: ExtractionResult) -> DeterministicCheckResult:
        result = DeterministicCheckResult()

        hook_beats = [b for b in extraction.beats if b.narrative_role == "hook"]
        if hook_beats:
            hook_duration = sum(b.duration for b in hook_beats)
            if hook_duration > 5.0:
                result.hook_too_long = True
                result.issues.append(f"Hook too long ({hook_duration:.1f}s > 5s)")

        cta_beats = [b for b in extraction.beats if b.narrative_role == "cta"]
        if not cta_beats:
            result.no_cta = True
            result.issues.append("No CTA (call-to-action) scene detected")

        proof_beats = [b for b in extraction.beats if b.proof_type and b.proof_type != "null"]
        if not proof_beats:
            result.no_proof = True
            result.issues.append("No proof/evidence scene detected (testimonial, demo, stats, etc.)")

        if extraction.first_product_time and extraction.first_product_time > 10:
            result.late_product_reveal = True
            result.issues.append(f"Product appears late ({extraction.first_product_time:.1f}s > 10s)")

        if extraction.first_cta_time:
            total = extraction.total_duration
            cta_position_ratio = extraction.first_cta_time / total if total > 0 else 0
            if cta_position_ratio < 0.5:
                result.warnings.append(f"CTA appears early ({cta_position_ratio:.0%} into video)")

        no_product_scenes = [b for b in extraction.beats if not b.product_visible]
        if len(no_product_scenes) == len(extraction.beats):
            result.issues.append("Product not visible in any scene")

        if not extraction.flow.logical_flow:
            result.warnings.append("Narrative flow has logical issues")

        if not extraction.flow.tone_consistent:
            result.warnings.append("Tone is inconsistent across scenes")

        if not extraction.flow.core_message_clear:
            result.warnings.append("Core message is unclear or competing messages detected")

        return result

    def _prepare_reference_section(self, sequence_data: dict, verbose: bool = False) -> str:
        repo = self._load_reference_repository()
        if not repo:
            if verbose:
                print("  Reference repository: (not available)")
            return ""

        metadata = sequence_data.get("metadata", {})
        context = metadata.get("context", "")
        title = metadata.get("title", "")

        scripts = []
        for scene in sequence_data.get("scenes", [])[:3]:
            audio = scene.get("audio_script", {})
            if isinstance(audio, dict):
                scripts.append(audio.get("text", ""))

        query = f"{context} {title} {' '.join(scripts)}".strip()[:500]
        references = repo.find_similar_references(query, max_results=3)

        if verbose:
            print(f"  Reference repository: {len(repo.get_all_analyses())} ads")
            print(f"  Selected references: {len(references)}")

        if not references:
            return ""

        summaries = []
        for ref in references:
            summary = f"""
Reference: {ref.ad_id}
Framework: {ref.framework}
Positioning: {ref.one_sentence_positioning}
Hook duration: {ref.pacing.hook_duration}s
First product: {ref.pacing.first_product_reveal_time}s
First CTA: {ref.pacing.first_cta_time}s
Patterns: {', '.join(ref.reusable_patterns[:3])}
"""
            summaries.append(summary.strip())

        return REFERENCE_BENCHMARK_SECTION.format(
            reference_summaries="\n\n".join(summaries)
        )

    def _load_reference_repository(self) -> Optional[ReferenceRepositoryAdapter]:
        if self._reference_repo is not None:
            return self._reference_repo

        if not REFERENCES_DIR.exists():
            return None

        store = ReferenceStore(REFERENCES_DIR)
        collections = store.list_collections()
        if not collections:
            return None

        self._reference_repo = ReferenceRepositoryAdapter(
            store=store,
            project=self.project,
        )
        return self._reference_repo

    def _call_llm(self, prompt: str) -> str:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[prompt],
            config=config,
        )

        if response.text is None:
            raise ValueError("Empty response from model")

        return response.text

    def _call_llm_with_image(self, prompt: str, image: Image.Image) -> str:
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        )

        response = self.client.models.generate_content(
            model=self.model,
            contents=[image, prompt],
            config=config,
        )

        if response.text is None:
            raise ValueError("Empty response from model")

        return response.text

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
            raise ValueError(f"Failed to parse response JSON: {e}\nResponse: {text[:500]}")


def review_sequence(
    sequence_path: Path | str,
    output_path: Path | str | None = None,
    project: str | None = None,
    with_references: bool = False,
    with_visuals: bool = True,
    verbose: bool = False,
) -> SequenceReview:
    reviewer = SequenceReviewer(project=project)
    review = reviewer.review(
        sequence_path,
        with_references=with_references,
        with_visuals=with_visuals,
        verbose=verbose,
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(review.model_dump_json(indent=2))
        if verbose:
            print(f"  Review saved to: {output_path}")

    return review
