from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class ExtractedBeat(BaseModel):
    """Single scene extracted into evaluation-ready format."""

    scene_id: str
    full_script: str
    visual_description: str
    narrative_role: str
    duration: float
    claim_made: str | None = None
    proof_type: str | None = None
    persuasion_devices: list[str] = Field(default_factory=list)
    product_visible: bool = False
    human_present: bool = False
    text_overlay_present: bool = False


class FlowIssue(BaseModel):
    """Issue detected in narrative flow between scenes."""

    between_scenes: list[str]
    issue_type: str
    description: str


class FlowAnalysis(BaseModel):
    """Analysis of overall narrative flow across all scenes."""

    full_narrative: str
    logical_flow: bool
    flow_issues: list[FlowIssue] = Field(default_factory=list)
    tone_consistent: bool = True
    tone_shifts: list[str] = Field(default_factory=list)
    core_message_clear: bool = True
    core_message: str | None = None
    competing_messages: list[str] = Field(default_factory=list)


class ExtractionResult(BaseModel):
    """Step 1 output: Extracted beats + flow analysis."""

    sequence_id: str
    total_duration: float
    scene_count: int
    beats: list[ExtractedBeat]
    flow: FlowAnalysis
    hook_duration: float | None = None
    first_product_time: float | None = None
    first_proof_time: float | None = None
    first_cta_time: float | None = None


class PersuasionScore(BaseModel):
    """Persuasion effectiveness scores."""

    overall: int = Field(ge=1, le=10)
    reasoning: str
    attention: int = Field(ge=1, le=10)
    branding: int = Field(ge=1, le=10)
    connection: int = Field(ge=1, le=10)
    direction: int = Field(ge=1, le=10)
    problem_clarity: int = Field(ge=1, le=10)
    proof_strength: int = Field(ge=1, le=10)
    pacing: int = Field(ge=1, le=10)

    @field_validator(
        "overall", "attention", "branding", "connection", "direction",
        "problem_clarity", "proof_strength", "pacing",
        mode="before",
    )
    @classmethod
    def round_to_int(cls, v):
        if isinstance(v, float):
            return round(v)
        return v


class VisualApproach(BaseModel):
    """A suggested approach to fix a visual issue."""

    approach_type: str
    description: str
    detailed_spec: str
    confidence: str = "medium"


class VisualFix(BaseModel):
    """Visual improvement suggestion for a scene."""

    scene_id: str
    issue: str
    severity: str = "major"
    suggested_approaches: list[VisualApproach] = Field(default_factory=list)


class ScriptFix(BaseModel):
    """Script modification suggestion."""

    scene_id: str
    issue: str
    current_script: str
    suggested_script: str
    reason: str


class FlowFix(BaseModel):
    """Flow improvement suggestion."""

    issue: FlowIssue
    suggestion: str


class FrameworkSuggestion(BaseModel):
    """Alternative framework/approach suggestion."""

    framework: str
    reason: str
    outline: list[str] = Field(default_factory=list)


class ActionItem(BaseModel):
    """Prioritized action item from review."""

    priority: int
    category: str
    scene_id: str | None = None
    action: str
    impact: str


class SequenceReview(BaseModel):
    """Final review output with scores and recommendations."""

    sequence_id: str
    reviewed_at: str
    persuasion_score: PersuasionScore
    visual_fixes: list[VisualFix] = Field(default_factory=list)
    script_fixes: list[ScriptFix] = Field(default_factory=list)
    flow_fixes: list[FlowFix] = Field(default_factory=list)
    alternative_frameworks: list[FrameworkSuggestion] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)
    deterministic_issues: list[str] = Field(default_factory=list)


class DeterministicCheckResult(BaseModel):
    """Results from rule-based deterministic checks."""

    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    hook_too_long: bool = False
    no_cta: bool = False
    no_proof: bool = False
    late_product_reveal: bool = False
    late_cta: bool = False
