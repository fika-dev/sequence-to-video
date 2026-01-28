from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Optional

import numpy as np
from google import genai

from domains.library.reference_models import ReferenceAdAnalysis, ReferenceAdPacing, ReferenceAdStyleGuide, ReferenceAdBeat


class ReferenceRepository:
    def __init__(
        self,
        index_dir: Path,
        project: Optional[str] = None,
        embedding_model: str = "text-embedding-005",
    ):
        self.index_dir = Path(index_dir)
        self.project = project
        self.embedding_model = embedding_model
        self._analyses: dict[str, ReferenceAdAnalysis] = {}
        self._embedding_client: Optional[genai.Client] = None
        self._load_existing_analyses()

    @property
    def embedding_client(self) -> genai.Client:
        if self._embedding_client is None:
            self._embedding_client = genai.Client(
                vertexai=True,
                project=self.project,
                location="global",
            )
        return self._embedding_client

    def _load_existing_analyses(self) -> None:
        if not self.index_dir.exists():
            return

        for ad_dir in self.index_dir.iterdir():
            if not ad_dir.is_dir():
                continue
            analysis_file = ad_dir / "analysis.json"
            if not analysis_file.exists():
                continue

            with open(analysis_file, encoding="utf-8") as f:
                data = json.load(f)

            analysis = self._build_analysis_from_dict(data)
            self._load_embeddings_for_analysis(analysis, ad_dir)
            self._analyses[analysis.ad_id] = analysis

    def _build_analysis_from_dict(self, data: dict) -> ReferenceAdAnalysis:
        pacing_data = data.get("pacing", {})
        pacing = ReferenceAdPacing(**pacing_data) if pacing_data else ReferenceAdPacing()

        style_data = data.get("style_guide", {})
        style_guide = ReferenceAdStyleGuide(**style_data) if style_data else ReferenceAdStyleGuide()

        beats = [ReferenceAdBeat(**b) for b in data.get("beats", [])]

        return ReferenceAdAnalysis(
            ad_id=data["ad_id"],
            source_file=Path(data["source_file"]),
            analyzed_at=data["analyzed_at"],
            total_duration=data.get("total_duration", 0),
            raw_response=data.get("raw_response"),
            platform=data.get("platform"),
            locale=data.get("locale"),
            product_category=data.get("product_category"),
            brand_or_product_guess=data.get("brand_or_product_guess"),
            framework=data.get("framework", "other"),
            one_sentence_positioning=data.get("one_sentence_positioning", ""),
            target_audience=data.get("target_audience"),
            core_pain_point=data.get("core_pain_point"),
            core_promise=data.get("core_promise"),
            pacing=pacing,
            beats=beats,
            ctas=data.get("ctas", []),
            offers=data.get("offers", []),
            reusable_patterns=data.get("reusable_patterns", []),
            style_guide=style_guide,
            fb_metadata=data.get("fb_metadata"),
        )

    def _load_embeddings_for_analysis(self, analysis: ReferenceAdAnalysis, ad_dir: Path) -> None:
        fingerprint_file = ad_dir / "fingerprint.npy"
        if fingerprint_file.exists():
            analysis.ad_fingerprint_embedding = np.load(fingerprint_file).tolist()

        for beat in analysis.beats:
            beat_file = ad_dir / f"{beat.beat_id}.npy"
            if beat_file.exists():
                beat.embedding = np.load(beat_file).tolist()

    def get_all_analyses(self) -> list[ReferenceAdAnalysis]:
        return list(self._analyses.values())

    def get_analysis_by_id(self, ad_id: str) -> Optional[ReferenceAdAnalysis]:
        return self._analyses.get(ad_id)

    def find_similar_references(
        self,
        query: str,
        max_results: int = 5,
        product_category: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> list[ReferenceAdAnalysis]:
        query_embedding = self._generate_query_embedding(query)
        if not query_embedding:
            return self._filter_analyses(product_category, framework)[:max_results]

        scored: list[tuple[float, ReferenceAdAnalysis]] = []
        for analysis in self._analyses.values():
            if product_category and analysis.product_category != product_category:
                continue
            if framework and analysis.framework != framework:
                continue
            if not analysis.ad_fingerprint_embedding:
                continue

            similarity = self._cosine_similarity(query_embedding, analysis.ad_fingerprint_embedding)
            scored.append((similarity, analysis))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        frameworks_seen: dict[str, int] = {}
        for _, analysis in scored:
            fw = analysis.framework
            if frameworks_seen.get(fw, 0) >= 2:
                continue
            frameworks_seen[fw] = frameworks_seen.get(fw, 0) + 1
            results.append(analysis)
            if len(results) >= max_results:
                break

        return results

    def find_similar_beats(
        self,
        query: str,
        narrative_role: Optional[str] = None,
        max_results: int = 10,
    ) -> list[tuple[ReferenceAdAnalysis, ReferenceAdBeat]]:
        query_embedding = self._generate_query_embedding(query)
        if not query_embedding:
            return []

        scored: list[tuple[float, ReferenceAdAnalysis, ReferenceAdBeat]] = []
        for analysis in self._analyses.values():
            for beat in analysis.beats:
                if narrative_role and beat.narrative_role != narrative_role:
                    continue
                if not beat.embedding:
                    continue

                similarity = self._cosine_similarity(query_embedding, beat.embedding)
                scored.append((similarity, analysis, beat))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [(a, b) for _, a, b in scored[:max_results]]

    def _filter_analyses(
        self,
        product_category: Optional[str] = None,
        framework: Optional[str] = None,
    ) -> list[ReferenceAdAnalysis]:
        results = []
        for analysis in self._analyses.values():
            if product_category and analysis.product_category != product_category:
                continue
            if framework and analysis.framework != framework:
                continue
            results.append(analysis)
        return results

    def _generate_query_embedding(self, text: str) -> list[float]:
        try:
            response = self.embedding_client.models.embed_content(
                model=self.embedding_model,
                contents=[text],
            )
            return response.embeddings[0].values
        except Exception:
            return []

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b) or not a:
            return 0.0
        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def to_prompt_format(self, analyses: list[ReferenceAdAnalysis], max_beats: int = 4) -> str:
        if not analyses:
            return "(No reference ads available)"

        lines = []
        for i, analysis in enumerate(analyses, 1):
            lines.append(f"## Reference Ad {i}: {analysis.ad_id}")
            lines.append(f"- Framework: {analysis.framework}")
            lines.append(f"- Positioning: {analysis.one_sentence_positioning}")
            if analysis.target_audience:
                lines.append(f"- Target Audience: {analysis.target_audience}")
            if analysis.core_pain_point:
                lines.append(f"- Pain Point: {analysis.core_pain_point}")
            if analysis.core_promise:
                lines.append(f"- Promise: {analysis.core_promise}")

            pacing = analysis.pacing
            lines.append(f"- Pacing: hook={pacing.hook_duration}s, first_product={pacing.first_product_reveal_time}s, first_cta={pacing.first_cta_time}s")

            if analysis.reusable_patterns:
                lines.append("- Patterns:")
                for pattern in analysis.reusable_patterns[:5]:
                    lines.append(f"  * {pattern}")

            lines.append("- Beats:")
            for beat in analysis.beats[:max_beats]:
                lines.append(f"  * [{beat.start_time:.1f}-{beat.end_time:.1f}s] {beat.narrative_role}: {beat.visual_summary[:80]}")
                if beat.on_screen_text:
                    lines.append(f"    Text: {', '.join(beat.on_screen_text[:3])}")

            lines.append("")

        return "\n".join(lines)
