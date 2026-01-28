#!/usr/bin/env python3
"""
Ad Taxonomy Analyzer

Analyzes reference ads from assets/reference_index/ to:
1. Extract key fields with full scripts
2. Classify into archetypes based on script patterns
3. Deep-dive into each archetype's script characteristics
4. Generate a comprehensive report

Usage:
    uv run python scripts/analyze_ad_taxonomy.py -v
    uv run python scripts/analyze_ad_taxonomy.py --phase 1  # Run only phase 1
    uv run python scripts/analyze_ad_taxonomy.py --force    # Re-run all phases
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types

from infrastructure.config import load_config

# -----------------------------------------------------------------------------
# Data Models
# -----------------------------------------------------------------------------


@dataclass
class AdSummary:
    """Compact summary of an ad for analysis."""

    ad_id: str
    product_category: str | None
    brand: str | None
    framework: str
    positioning: str
    target_audience: str | None
    core_pain_point: str | None
    core_promise: str | None
    total_duration: float
    hook_duration: float | None
    first_product_reveal: float | None
    first_cta_time: float | None
    full_script: str  # The key field - concatenated spoken_transcript
    beat_flow: list[str]  # Sequence of narrative_role
    hook_technique: str | None
    persuasion_devices: list[str]
    reusable_patterns: list[str]
    tone: str | None


@dataclass
class Archetype:
    """An ad archetype/category."""

    name: str
    description: str
    key_characteristics: list[str]
    ad_ids: list[str]


@dataclass
class ArchetypeAnalysis:
    """Deep analysis of an archetype's script patterns."""

    archetype_name: str
    hook_patterns: list[str]
    transition_patterns: list[str]
    proof_patterns: list[str]
    benefit_expressions: list[str]
    urgency_expressions: list[str]
    cta_patterns: list[str]
    tone_characteristics: list[str]
    script_formula: str
    example_scripts: list[dict[str, str]]  # {ad_id, script, why_effective}


@dataclass
class TaxonomyReport:
    """Final taxonomy report."""

    generated_at: str
    total_ads_analyzed: int
    archetypes: list[Archetype]
    archetype_analyses: list[ArchetypeAnalysis]
    cross_type_insights: list[str]
    reusable_sentence_patterns: list[str]


# -----------------------------------------------------------------------------
# Phase 1: Data Extraction
# -----------------------------------------------------------------------------


def extract_ad_summaries(
    reference_index_path: Path,
    verbose: bool = False,
) -> list[AdSummary]:
    """Extract key fields from all analysis.json files."""
    summaries = []

    index_file = reference_index_path / "index.json"
    if not index_file.exists():
        raise FileNotFoundError(f"Index file not found: {index_file}")

    with open(index_file) as f:
        index_data = json.load(f)

    ad_ids = index_data.get("ads", [])
    if verbose:
        print(f"Found {len(ad_ids)} ads in index")

    for ad_id in ad_ids:
        analysis_file = reference_index_path / ad_id / "analysis.json"
        if not analysis_file.exists():
            if verbose:
                print(f"  Skipping {ad_id} - no analysis.json")
            continue

        try:
            with open(analysis_file) as f:
                data = json.load(f)

            summary = _extract_summary(data, ad_id)
            summaries.append(summary)

            if verbose:
                print(
                    f"  {ad_id}: {len(summary.full_script)} chars, {len(summary.beat_flow)} beats"
                )

        except Exception as e:
            if verbose:
                print(f"  Error processing {ad_id}: {e}")

    return summaries


def _extract_summary(data: dict, ad_id: str) -> AdSummary:
    """Extract AdSummary from analysis.json data."""
    beats = data.get("beats", [])

    # Concatenate all spoken_transcript to get full script
    full_script_parts = []
    beat_flow = []
    all_persuasion_devices = set()
    hook_technique = None

    for beat in beats:
        transcript = beat.get("spoken_transcript")
        if transcript and transcript != "null":
            full_script_parts.append(transcript)

        role = beat.get("narrative_role", "other")
        beat_flow.append(role)

        # Get hook technique from first beat
        if role == "hook" and not hook_technique:
            ht = beat.get("hook_technique")
            if ht and ht != "null":
                hook_technique = ht

        # Collect persuasion devices
        devices = beat.get("persuasion_devices", [])
        for d in devices:
            if d and d != "null":
                all_persuasion_devices.add(d)

    full_script = " ".join(full_script_parts)

    pacing = data.get("pacing", {})
    style_guide = data.get("style_guide", {})

    return AdSummary(
        ad_id=ad_id,
        product_category=data.get("product_category"),
        brand=data.get("brand_or_product_guess"),
        framework=data.get("framework", "other"),
        positioning=data.get("one_sentence_positioning", ""),
        target_audience=data.get("target_audience"),
        core_pain_point=data.get("core_pain_point"),
        core_promise=data.get("core_promise"),
        total_duration=data.get("total_duration", 0),
        hook_duration=pacing.get("hook_duration"),
        first_product_reveal=pacing.get("first_product_reveal_time"),
        first_cta_time=pacing.get("first_cta_time"),
        full_script=full_script,
        beat_flow=beat_flow,
        hook_technique=hook_technique,
        persuasion_devices=list(all_persuasion_devices),
        reusable_patterns=data.get("reusable_patterns", []),
        tone=style_guide.get("tone"),
    )


# -----------------------------------------------------------------------------
# Phase 2: Archetype Classification
# -----------------------------------------------------------------------------


CLASSIFICATION_PROMPT = """당신은 광고 카피라이팅 전문가입니다.

아래는 {ad_count}개 광고의 요약 데이터입니다. 각 광고의 **전체 스크립트(나레이션)**와 구조 정보를 분석하여,
광고들을 3-5개의 유형(Archetype)으로 분류해주세요.

## 분류 기준 (스크립트 중심으로 분석)

1. **오프닝 전략**: 첫 문장이 어떻게 시작하는가?
   - 질문형 ("~하신 분?", "왜 ~할까요?")
   - 충격형 ("큰일이다!", "이거 모르면...")
   - 공감형 ("저도 그랬어요", "다들 겪어봤죠?")
   - 정보형 ("~의 비밀", "전문가가 알려주는")
   - 비교형 ("A vs B", "~는 가짜입니다")

2. **스토리 구조**: 어떤 흐름으로 설득하는가?
   - 문제→해결 (Pain → Solution)
   - 체험담 (내가 써봤는데...)
   - 교육형 (이게 왜 효과가 있냐면...)
   - 비교/폭로형 (다른 건 이래서 안되고...)
   - 사회적 증거형 (다들 이거 쓰더라)

3. **화법/톤**: 어떤 말투인가?
   - 친근한 대화체 ("이거 진짜야", "나도 그랬거든")
   - 전문가 어조 ("생리학적으로", "연구에 따르면")
   - 긴급/강조형 ("제발", "꼭", "지금 당장")

4. **CTA 방식**: 행동 유도를 어떻게 하는가?
   - 긴급성 ("세일 기간", "한정")
   - 혜택 강조 ("3+1", "할인")
   - 동조 유도 ("같이 노려보자", "함께")

## 광고 데이터

{ad_data}

## 출력 형식 (JSON)

```json
{{
  "archetypes": [
    {{
      "name": "유형 이름 (한글, 2-4단어)",
      "description": "이 유형의 핵심 특징 설명 (1-2문장)",
      "key_characteristics": [
        "특징 1",
        "특징 2",
        "특징 3"
      ],
      "ad_ids": ["광고ID1", "광고ID2", ...]
    }}
  ]
}}
```

JSON만 출력하세요. 마크다운 펜스 없이 순수 JSON만 반환하세요."""


def classify_archetypes(
    summaries: list[AdSummary],
    client: genai.Client,
    model: str,
    verbose: bool = False,
) -> list[Archetype]:
    """Classify ads into archetypes using LLM."""
    if verbose:
        print("Phase 2: Classifying archetypes...")

    # Build ad data string for prompt
    ad_data_parts = []
    for s in summaries:
        ad_data_parts.append(
            f"""---
AD_ID: {s.ad_id}
FRAMEWORK: {s.framework}
HOOK_TECHNIQUE: {s.hook_technique or "N/A"}
BEAT_FLOW: {" → ".join(s.beat_flow)}
TONE: {s.tone or "N/A"}
POSITIONING: {s.positioning}
CORE_PAIN: {s.core_pain_point or "N/A"}
CORE_PROMISE: {s.core_promise or "N/A"}

FULL_SCRIPT:
{s.full_script}
"""
        )

    ad_data = "\n".join(ad_data_parts)
    prompt = CLASSIFICATION_PROMPT.format(ad_count=len(summaries), ad_data=ad_data)

    if verbose:
        print(f"  Prompt size: {len(prompt)} chars")
        print(f"  Calling {model}...")

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    raw_text = response.text or "{}"
    data = _parse_json_response(raw_text)

    archetypes = []
    for arch_data in data.get("archetypes", []):
        archetype = Archetype(
            name=arch_data.get("name", "Unknown"),
            description=arch_data.get("description", ""),
            key_characteristics=arch_data.get("key_characteristics", []),
            ad_ids=arch_data.get("ad_ids", []),
        )
        archetypes.append(archetype)

        if verbose:
            print(f"  Archetype: {archetype.name} ({len(archetype.ad_ids)} ads)")

    return archetypes


# -----------------------------------------------------------------------------
# Phase 3: Deep Script Analysis per Archetype
# -----------------------------------------------------------------------------


DEEP_ANALYSIS_PROMPT = """당신은 광고 스크립트 분석 전문가입니다.

아래는 "{archetype_name}" 유형에 속하는 {ad_count}개 광고의 전체 스크립트입니다.
이 유형의 스크립트 패턴을 심층 분석해주세요.

## 유형 설명
{archetype_description}

## 주요 특징
{archetype_characteristics}

## 광고 스크립트들

{scripts_data}

## 분석 항목

1. **Hook 패턴**: 첫 3초에 사용하는 문장 패턴 (실제 예시 포함)
2. **전환 패턴**: 문제→해결, 공감→제안 등으로 넘어가는 표현
3. **증거 제시 패턴**: 숫자, 권위자, 체험담을 말하는 방식
4. **혜택 표현법**: 제품 효능/가치를 전달하는 언어
5. **긴급성/희소성 표현**: 세일, 한정 등을 표현하는 방식
6. **CTA 화법**: 행동 유도 문장 패턴
7. **전체 문체/어조 특징**: 말투, 존댓말/반말, 감정 표현

## 출력 형식 (JSON)

```json
{{
  "archetype_name": "{archetype_name}",
  "hook_patterns": [
    "패턴 1: 설명 + 예시 문장",
    "패턴 2: 설명 + 예시 문장"
  ],
  "transition_patterns": [
    "패턴 1: 설명 + 예시 문장"
  ],
  "proof_patterns": [
    "패턴 1: 설명 + 예시 문장"
  ],
  "benefit_expressions": [
    "표현 1: 설명 + 예시"
  ],
  "urgency_expressions": [
    "표현 1: 설명 + 예시 (없으면 빈 배열)"
  ],
  "cta_patterns": [
    "패턴 1: 설명 + 예시"
  ],
  "tone_characteristics": [
    "특징 1",
    "특징 2"
  ],
  "script_formula": "이 유형의 스크립트를 작성할 때 따라야 할 공식/템플릿 (2-3문장)",
  "example_scripts": [
    {{
      "ad_id": "가장 효과적인 광고 ID",
      "script": "해당 스크립트 전문",
      "why_effective": "왜 이 스크립트가 효과적인지 설명"
    }}
  ]
}}
```

JSON만 출력하세요."""


def analyze_archetype_scripts(
    archetype: Archetype,
    summaries: list[AdSummary],
    client: genai.Client,
    model: str,
    verbose: bool = False,
) -> ArchetypeAnalysis:
    """Deep-dive analysis of scripts within an archetype."""
    if verbose:
        print(f"  Analyzing archetype: {archetype.name}")

    # Get summaries for this archetype
    archetype_summaries = [s for s in summaries if s.ad_id in archetype.ad_ids]

    # Build scripts data
    scripts_parts = []
    for s in archetype_summaries:
        scripts_parts.append(
            f"""---
AD_ID: {s.ad_id}
DURATION: {s.total_duration}s
BEAT_FLOW: {" → ".join(s.beat_flow)}

SCRIPT:
{s.full_script}
"""
        )

    scripts_data = "\n".join(scripts_parts)

    prompt = DEEP_ANALYSIS_PROMPT.format(
        archetype_name=archetype.name,
        archetype_description=archetype.description,
        archetype_characteristics="\n".join(f"- {c}" for c in archetype.key_characteristics),
        ad_count=len(archetype_summaries),
        scripts_data=scripts_data,
    )

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
        ),
    )

    raw_text = response.text or "{}"
    data = _parse_json_response(raw_text)

    return ArchetypeAnalysis(
        archetype_name=data.get("archetype_name", archetype.name),
        hook_patterns=data.get("hook_patterns", []),
        transition_patterns=data.get("transition_patterns", []),
        proof_patterns=data.get("proof_patterns", []),
        benefit_expressions=data.get("benefit_expressions", []),
        urgency_expressions=data.get("urgency_expressions", []),
        cta_patterns=data.get("cta_patterns", []),
        tone_characteristics=data.get("tone_characteristics", []),
        script_formula=data.get("script_formula", ""),
        example_scripts=data.get("example_scripts", []),
    )


# -----------------------------------------------------------------------------
# Phase 4: Final Report Generation
# -----------------------------------------------------------------------------


SYNTHESIS_PROMPT = """당신은 광고 전략 컨설턴트입니다.

아래는 {archetype_count}개 광고 유형에 대한 분석 결과입니다.
이를 종합하여 크로스 유형 인사이트와 재사용 가능한 문장 패턴을 도출해주세요.

## 유형별 분석 요약

{archetypes_summary}

## 요청 사항

1. **Cross-type Insights**: 유형 간 비교 분석 (어떤 상황에 어떤 유형이 효과적?)
2. **재사용 가능한 문장 패턴**: 모든 유형에서 발견되는 효과적인 표현 패턴

## 출력 형식 (JSON)

```json
{{
  "cross_type_insights": [
    "인사이트 1: 구체적 비교/분석",
    "인사이트 2: 구체적 비교/분석"
  ],
  "reusable_sentence_patterns": [
    "패턴 1: [상황] - [표현 예시]",
    "패턴 2: [상황] - [표현 예시]"
  ]
}}
```

JSON만 출력하세요."""


def generate_final_report(
    summaries: list[AdSummary],
    archetypes: list[Archetype],
    analyses: list[ArchetypeAnalysis],
    client: genai.Client,
    model: str,
    verbose: bool = False,
) -> TaxonomyReport:
    """Generate the final taxonomy report."""
    if verbose:
        print("Phase 4: Generating final report...")

    # Build archetypes summary for synthesis
    summary_parts = []
    for arch, analysis in zip(archetypes, analyses):
        summary_parts.append(
            f"""### {arch.name}
설명: {arch.description}
광고 수: {len(arch.ad_ids)}개
주요 특징: {", ".join(arch.key_characteristics[:3])}
Hook 패턴: {", ".join(analysis.hook_patterns[:2]) if analysis.hook_patterns else "N/A"}
CTA 패턴: {", ".join(analysis.cta_patterns[:2]) if analysis.cta_patterns else "N/A"}
스크립트 공식: {analysis.script_formula}
"""
        )

    archetypes_summary = "\n".join(summary_parts)

    prompt = SYNTHESIS_PROMPT.format(
        archetype_count=len(archetypes),
        archetypes_summary=archetypes_summary,
    )

    response = client.models.generate_content(
        model=model,
        contents=[prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )

    raw_text = response.text or "{}"
    data = _parse_json_response(raw_text)

    return TaxonomyReport(
        generated_at=datetime.now().isoformat(),
        total_ads_analyzed=len(summaries),
        archetypes=archetypes,
        archetype_analyses=analyses,
        cross_type_insights=data.get("cross_type_insights", []),
        reusable_sentence_patterns=data.get("reusable_sentence_patterns", []),
    )


# -----------------------------------------------------------------------------
# Utilities
# -----------------------------------------------------------------------------


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return {}


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return asdict(obj)  # type: ignore[arg-type]
    return obj


def save_checkpoint(data: Any, path: Path, verbose: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if hasattr(data, "__iter__") and not isinstance(data, (str, dict)):
        data = [_to_dict(item) for item in data]
    else:
        data = _to_dict(data)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"  Saved checkpoint: {path}")


def load_checkpoint(path: Path, verbose: bool = False) -> Any | None:
    """Load checkpoint data from JSON file."""
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if verbose:
            print(f"  Loaded checkpoint: {path}")
        return data
    except Exception:
        return None


# -----------------------------------------------------------------------------
# Main Workflow
# -----------------------------------------------------------------------------


def run_taxonomy_analysis(
    reference_index_path: Path,
    output_path: Path,
    project: str,
    model: str = "gemini-3-flash-preview",
    force: bool = False,
    phase: int | None = None,
    verbose: bool = False,
) -> TaxonomyReport:
    """Run the full taxonomy analysis workflow."""
    checkpoint_dir = output_path.parent / ".taxonomy_cache"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # Initialize Gemini client
    client = genai.Client(
        vertexai=True,
        project=project,
        location="global",
    )

    # Phase 1: Extract summaries
    summaries_checkpoint = checkpoint_dir / "phase1_summaries.json"
    summaries_data = (
        load_checkpoint(summaries_checkpoint, verbose) if not force and phase != 1 else None
    )
    if summaries_data is not None:
        summaries = [AdSummary(**s) for s in summaries_data]
        if verbose:
            print(f"Phase 1: Loaded {len(summaries)} summaries from cache")
    else:
        if verbose:
            print("Phase 1: Extracting ad summaries...")
        summaries = extract_ad_summaries(reference_index_path, verbose)
        save_checkpoint(summaries, summaries_checkpoint, verbose)
        if verbose:
            print(f"Phase 1: Extracted {len(summaries)} summaries")

    if phase == 1:
        print(f"Phase 1 complete. {len(summaries)} summaries extracted.")
        return None  # type: ignore

    # Phase 2: Classify archetypes
    archetypes_checkpoint = checkpoint_dir / "phase2_archetypes.json"
    archetypes_data = (
        load_checkpoint(archetypes_checkpoint, verbose) if not force and phase != 2 else None
    )
    if archetypes_data is not None:
        archetypes = [Archetype(**a) for a in archetypes_data]
        if verbose:
            print(f"Phase 2: Loaded {len(archetypes)} archetypes from cache")
    else:
        archetypes = classify_archetypes(summaries, client, model, verbose)
        save_checkpoint(archetypes, archetypes_checkpoint, verbose)

    if phase == 2:
        print(f"Phase 2 complete. {len(archetypes)} archetypes identified.")
        return None  # type: ignore

    # Phase 3: Deep analysis per archetype
    analyses_checkpoint = checkpoint_dir / "phase3_analyses.json"
    analyses_data = (
        load_checkpoint(analyses_checkpoint, verbose) if not force and phase != 3 else None
    )
    if analyses_data is not None:
        analyses = [ArchetypeAnalysis(**a) for a in analyses_data]
        if verbose:
            print(f"Phase 3: Loaded {len(analyses)} analyses from cache")
    else:
        if verbose:
            print("Phase 3: Deep script analysis per archetype...")
        analyses = []
        for archetype in archetypes:
            analysis = analyze_archetype_scripts(archetype, summaries, client, model, verbose)
            analyses.append(analysis)
        save_checkpoint(analyses, analyses_checkpoint, verbose)

    if phase == 3:
        print(f"Phase 3 complete. {len(analyses)} archetype analyses done.")
        return None  # type: ignore

    # Phase 4: Generate final report
    report = generate_final_report(summaries, archetypes, analyses, client, model, verbose)

    # Save final report
    save_checkpoint(report, output_path, verbose)

    if verbose:
        print(f"\nFinal report saved to: {output_path}")
        print(f"Total ads analyzed: {report.total_ads_analyzed}")
        print(f"Archetypes identified: {len(report.archetypes)}")
        for arch in report.archetypes:
            print(f"  - {arch.name}: {len(arch.ad_ids)} ads")

    return report


def main():
    parser = argparse.ArgumentParser(description="Analyze ad taxonomy from reference ads")
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("assets/reference_index"),
        help="Path to reference index directory",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("assets/reference_index/taxonomy_report.json"),
        help="Output path for taxonomy report",
    )
    parser.add_argument(
        "--model",
        default="gemini-3-flash-preview",
        help="Gemini model to use",
    )
    parser.add_argument(
        "--phase",
        type=int,
        choices=[1, 2, 3, 4],
        help="Run only specific phase (1-4)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-run all phases (ignore cache)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    args = parser.parse_args()

    config = load_config()
    project = config.api.google_project_id

    if not project:
        print("Error: GOOGLE_PROJECT_ID not set in environment")
        return 1

    try:
        report = run_taxonomy_analysis(
            reference_index_path=args.input,
            output_path=args.output,
            project=project,
            model=args.model,
            force=args.force,
            phase=args.phase,
            verbose=args.verbose,
        )

        if report:
            print("\n" + "=" * 60)
            print("TAXONOMY ANALYSIS COMPLETE")
            print("=" * 60)
            print(f"Report: {args.output}")

    except Exception as e:
        print(f"Error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
