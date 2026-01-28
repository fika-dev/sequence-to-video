from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class ReferenceAdCTA(BaseModel):
    timestamp: float
    text_on_screen: str | None = None
    spoken_text: str | None = None
    cta_type: str | None = None
    urgency: str | None = None


class ReferenceAdOffer(BaseModel):
    timestamp: float | None = None
    offer_type: str | None = None
    exact_text_on_screen: str | None = None


class ReferenceAdBeat(BaseModel):
    beat_id: str
    start_time: float
    end_time: float

    narrative_role: str
    hook_technique: str | None = None
    persuasion_devices: list[str] = Field(default_factory=list)

    visual_summary: str
    primary_subject: str | None = None
    shot_size: str | None = None
    camera_movement: str | None = None
    editing_notes: str | None = None

    on_screen_text: list[str] = Field(default_factory=list)
    spoken_transcript: str | None = None
    product_presence: str | None = None
    proof_element: str | None = None

    embedding: list[float] | None = Field(default=None, exclude=True)
    embedding_path: str | None = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


class ReferenceAdPacing(BaseModel):
    cuts_per_minute: float | None = None
    avg_shot_length: float | None = None
    hook_duration: float | None = None
    first_product_reveal_time: float | None = None
    first_cta_time: float | None = None
    cta_repetitions: int | None = None


class ReferenceAdStyleGuide(BaseModel):
    tone: str | None = None
    text_overlay_style: str | None = None
    captioning_style: str | None = None
    music_mood: str | None = None
    overall_pacing_notes: str | None = None


class ReferenceAdAnalysis(BaseModel):
    ad_id: str
    source_file: Path
    analyzed_at: str
    total_duration: float
    raw_response: str | None = None

    platform: str | None = None
    locale: str | None = None
    product_category: str | None = None
    brand_or_product_guess: str | None = None

    framework: str
    one_sentence_positioning: str
    target_audience: str | None = None
    core_pain_point: str | None = None
    core_promise: str | None = None

    pacing: ReferenceAdPacing
    beats: list[ReferenceAdBeat] = Field(default_factory=list)
    ctas: list[ReferenceAdCTA] = Field(default_factory=list)
    offers: list[ReferenceAdOffer] = Field(default_factory=list)

    reusable_patterns: list[str] = Field(default_factory=list)
    style_guide: ReferenceAdStyleGuide = Field(default_factory=ReferenceAdStyleGuide)

    ad_fingerprint_embedding: list[float] | None = Field(default=None, exclude=True)
    ad_fingerprint_embedding_path: str | None = None

    fb_metadata: dict | None = None

    def to_fingerprint_text(self) -> str:
        parts = [
            self.one_sentence_positioning,
            f"framework: {self.framework}",
        ]
        if self.target_audience:
            parts.append(f"audience: {self.target_audience}")
        if self.core_pain_point:
            parts.append(f"pain: {self.core_pain_point}")
        if self.core_promise:
            parts.append(f"promise: {self.core_promise}")
        if self.style_guide.tone:
            parts.append(f"tone: {self.style_guide.tone}")
        parts.extend(self.reusable_patterns)
        return " | ".join(parts)

    def to_beat_text(self, beat: ReferenceAdBeat) -> str:
        parts = [beat.visual_summary, beat.narrative_role]
        if beat.on_screen_text:
            parts.extend(beat.on_screen_text)
        if beat.spoken_transcript:
            parts.append(beat.spoken_transcript)
        if beat.persuasion_devices:
            parts.extend(beat.persuasion_devices)
        return " ".join(parts)


class ReferenceAdsIndex(BaseModel):
    analyzed_at: str
    ads: list[ReferenceAdAnalysis] = Field(default_factory=list)
