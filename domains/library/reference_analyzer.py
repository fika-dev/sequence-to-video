from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from google import genai
from google.genai import types
from google.cloud import storage

from domains.library.reference_models import (
    ReferenceAdAnalysis,
    ReferenceAdBeat,
    ReferenceAdCTA,
    ReferenceAdOffer,
    ReferenceAdPacing,
    ReferenceAdStyleGuide,
    ReferenceAdsIndex,
)


REFERENCE_AD_PROMPT = """You are an expert performance creative analyst for short-form product ads.
Return ONLY valid JSON. Do not include markdown fences.

CRITICAL RULES:
- Do NOT invent facts. Only use what is visible/audible.
- Copy ALL on-screen text EXACTLY (including prices, % off, URLs, ratings).
- Provide timestamps in seconds (float).
- If you are unsure, omit the field or set it to null.

TASK:
Analyze this finished product advertisement (a complete ad, not raw footage).
Extract narrative structure, pacing, visual techniques, hook strategy, proof, and CTA timing.

SEGMENTATION:
- Break the ad into 2-6 second BEATS based on meaning (hook/problem/solution/proof/offer/cta), not every cut.
- Each beat must include start_time, end_time, narrative_role, visual_summary.
- Identify: first_product_reveal_time, first_cta_time, hook_duration, cta_repetitions.

OUTPUT JSON SCHEMA (follow exactly):
{
  "framework": "hook_body_cta|hpscpta|aida|pas|hook_story_offer|other",
  "one_sentence_positioning": "string",
  "target_audience": "string or null",
  "core_pain_point": "string or null",
  "core_promise": "string or null",
  "product_category": "string or null",
  "brand_or_product_guess": "string or null",
  "locale": "string or null",
  "total_duration": "float in seconds",
  "pacing": {
    "cuts_per_minute": "number or null",
    "avg_shot_length": "number or null",
    "hook_duration": "number or null",
    "first_product_reveal_time": "number or null",
    "first_cta_time": "number or null",
    "cta_repetitions": "integer or null"
  },
  "beats": [
    {
      "beat_id": "b01",
      "start_time": 0.0,
      "end_time": 3.2,
      "narrative_role": "hook|problem|agitate|solution|proof|offer|cta|brand|other",
      "hook_technique": "question|bold_claim|pattern_interrupt|shock_visual|relatable_pain|curiosity_gap|social_proof_open|null",
      "persuasion_devices": ["social_proof", "scarcity", "authority", "before_after", "demo", "testimonial", "comparison", "price_anchor"],
      "visual_summary": "string",
      "primary_subject": "creator_talking|hands_demo|product_packshot|ugc_lifestyle|screen_recording|motion_graphics|null",
      "shot_size": "ECU|CU|MCU|MS|FS|WS|null",
      "camera_movement": "static|handheld|pan|tilt|zoom|tracking|null",
      "editing_notes": "jump_cuts|speed_ramp|match_cut|whip_pan|smash_cut|null",
      "on_screen_text": ["verbatim text strings"],
      "spoken_transcript": "verbatim or null",
      "product_presence": "none|implied|shown|hero|null",
      "proof_element": "rating|testimonial|stat|before_after|ugc_reaction|expert|demo_result|null"
    }
  ],
  "ctas": [
    {
      "timestamp": 21.4,
      "text_on_screen": "string or null",
      "spoken_text": "string or null",
      "cta_type": "shop_now|learn_more|link_in_bio|app_install|store_visit|dm_us|subscribe|null",
      "urgency": "none|low|medium|high|null"
    }
  ],
  "offers": [
    {
      "timestamp": "number or null",
      "offer_type": "discount|bundle|free_trial|limited_time|money_back|free_shipping|null",
      "exact_text_on_screen": "string or null"
    }
  ],
  "style_guide": {
    "tone": "string",
    "text_overlay_style": "string",
    "captioning_style": "string",
    "music_mood": "string",
    "overall_pacing_notes": "string"
  },
  "reusable_patterns": [
    "Write 5-12 short rules that could be reused to generate a similar ad"
  ]
}"""


MIME_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


class ReferenceAdAnalyzer:
    def __init__(
        self,
        project: Optional[str] = None,
        location: str = "us-central1",
        gcs_bucket: Optional[str] = None,
        embedding_model: str = "text-embedding-005",
    ):
        self.project = project
        self.location = location
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location="global",
        )
        self.model = "gemini-3-flash-preview"
        self.embedding_model = embedding_model

        self.gcs_bucket = gcs_bucket or f"{project}-video-analysis"
        self.storage_client = storage.Client(project=project)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        try:
            self.storage_client.get_bucket(self.gcs_bucket)
        except Exception:
            bucket = self.storage_client.create_bucket(
                self.gcs_bucket,
                location=self.location,
            )
            print(f"Created GCS bucket: {bucket.name}")

    def analyze_reference_ad(
        self,
        video_path: Path,
        ad_id: str,
        fb_metadata: Optional[dict] = None,
        verbose: bool = False,
    ) -> ReferenceAdAnalysis:
        video_path = Path(video_path)

        if verbose:
            print(f"    Uploading to GCS: {video_path.name}")

        gcs_uri, mime_type = self._upload_to_gcs(video_path)

        if verbose:
            print(f"    GCS URI: {gcs_uri}")
            print(f"    Calling Gemini {self.model}...")

        video_metadata = types.VideoMetadata(fps=2)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part(
                    file_data=types.FileData(file_uri=gcs_uri, mime_type="video/*"),
                    video_metadata=video_metadata,
                ),
                REFERENCE_AD_PROMPT,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.3,
            ),
        )

        raw_response = response.text or ""

        if verbose:
            print(f"    Response received, parsing...")

        analysis_data = self._parse_response(raw_response)
        analysis = self._build_analysis(analysis_data, video_path, ad_id, fb_metadata, raw_response)

        if verbose:
            print(f"    Framework: {analysis.framework}")
            print(f"    Beats: {len(analysis.beats)}")
            print(f"    Duration: {analysis.total_duration}s")

        return analysis

    def generate_embeddings(self, analysis: ReferenceAdAnalysis) -> ReferenceAdAnalysis:
        texts_to_embed = []

        fingerprint_text = analysis.to_fingerprint_text()
        texts_to_embed.append(fingerprint_text)

        for beat in analysis.beats:
            beat_text = analysis.to_beat_text(beat)
            texts_to_embed.append(beat_text)

        embeddings = self._generate_embeddings(texts_to_embed)

        if embeddings and len(embeddings) > 0:
            analysis.ad_fingerprint_embedding = embeddings[0]

            for i, beat in enumerate(analysis.beats):
                if i + 1 < len(embeddings):
                    beat.embedding = embeddings[i + 1]

        return analysis

    def _upload_to_gcs(self, video_path: Path) -> tuple[str, str]:
        bucket = self.storage_client.bucket(self.gcs_bucket)

        blob_name = f"reference_ads/{uuid.uuid4().hex}_{video_path.name}"
        blob = bucket.blob(blob_name)

        mime_type = MIME_TYPES.get(video_path.suffix.lower(), "video/mp4")
        blob.upload_from_filename(str(video_path), content_type=mime_type)

        gcs_uri = f"gs://{self.gcs_bucket}/{blob_name}"
        return gcs_uri, mime_type

    def _parse_response(self, response_text: str) -> dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {}

    def _build_analysis(
        self,
        data: dict,
        source_file: Path,
        ad_id: str,
        fb_metadata: Optional[dict],
        raw_response: str,
    ) -> ReferenceAdAnalysis:
        pacing_data = data.get("pacing", {})
        pacing = ReferenceAdPacing(
            cuts_per_minute=pacing_data.get("cuts_per_minute"),
            avg_shot_length=pacing_data.get("avg_shot_length"),
            hook_duration=pacing_data.get("hook_duration"),
            first_product_reveal_time=pacing_data.get("first_product_reveal_time"),
            first_cta_time=pacing_data.get("first_cta_time"),
            cta_repetitions=pacing_data.get("cta_repetitions"),
        )

        style_data = data.get("style_guide", {})
        style_guide = ReferenceAdStyleGuide(
            tone=style_data.get("tone"),
            text_overlay_style=style_data.get("text_overlay_style"),
            captioning_style=style_data.get("captioning_style"),
            music_mood=style_data.get("music_mood"),
            overall_pacing_notes=style_data.get("overall_pacing_notes"),
        )

        beats = []
        for beat_data in data.get("beats", []):
            beat = ReferenceAdBeat(
                beat_id=beat_data.get("beat_id", f"b{len(beats):02d}"),
                start_time=float(beat_data.get("start_time", 0)),
                end_time=float(beat_data.get("end_time", 0)),
                narrative_role=beat_data.get("narrative_role", "other"),
                hook_technique=beat_data.get("hook_technique"),
                persuasion_devices=beat_data.get("persuasion_devices", []),
                visual_summary=beat_data.get("visual_summary", ""),
                primary_subject=beat_data.get("primary_subject"),
                shot_size=beat_data.get("shot_size"),
                camera_movement=beat_data.get("camera_movement"),
                editing_notes=beat_data.get("editing_notes"),
                on_screen_text=beat_data.get("on_screen_text", []),
                spoken_transcript=beat_data.get("spoken_transcript"),
                product_presence=beat_data.get("product_presence"),
                proof_element=beat_data.get("proof_element"),
            )
            beats.append(beat)

        ctas = []
        for cta_data in data.get("ctas", []):
            cta = ReferenceAdCTA(
                timestamp=float(cta_data.get("timestamp", 0)),
                text_on_screen=cta_data.get("text_on_screen"),
                spoken_text=cta_data.get("spoken_text"),
                cta_type=cta_data.get("cta_type"),
                urgency=cta_data.get("urgency"),
            )
            ctas.append(cta)

        offers = []
        for offer_data in data.get("offers", []):
            offer = ReferenceAdOffer(
                timestamp=float(offer_data["timestamp"]) if offer_data.get("timestamp") else None,
                offer_type=offer_data.get("offer_type"),
                exact_text_on_screen=offer_data.get("exact_text_on_screen"),
            )
            offers.append(offer)

        return ReferenceAdAnalysis(
            ad_id=ad_id,
            source_file=source_file,
            analyzed_at=datetime.now().isoformat(),
            total_duration=float(data.get("total_duration", 0)),
            raw_response=raw_response,
            platform="facebook",
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
            ctas=ctas,
            offers=offers,
            reusable_patterns=data.get("reusable_patterns", []),
            style_guide=style_guide,
            fb_metadata=fb_metadata,
        )

    def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=texts,
            )
            return [emb.values for emb in response.embeddings]
        except Exception as e:
            print(f"    Warning: embedding generation failed: {e}")
            return [[] for _ in texts]
