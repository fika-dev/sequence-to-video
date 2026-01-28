EXTRACTION_PROMPT = """You are an expert video ad analyst. Extract structured information from this sequence for evaluation.

CRITICAL RULES:
- Preserve full_script EXACTLY as provided (no summarization, no paraphrasing)
- Preserve visual_description EXACTLY as provided
- Be precise about what IS present vs what is MISSING
- If something is unclear, say so rather than guessing

SEQUENCE TO ANALYZE:
{sequence_json}

TASK:
1. Extract each scene into a beat with narrative role classification
2. Analyze the FULL narrative flow by reading all scripts in sequence
3. Identify pacing markers (when things first appear)

NARRATIVE ROLES (pick one per scene):
- hook: Opens the ad, grabs attention
- problem: Establishes pain point or need
- agitate: Amplifies the problem emotionally
- solution: Introduces the product/service as answer
- proof: Evidence (testimonial, demo, stats, before/after)
- offer: Deal, discount, bundle details
- cta: Call to action
- bridge: Transition or connection between sections
- other: Doesn't fit above categories

PROOF TYPES (if scene contains evidence):
- testimonial: User/customer sharing experience
- stat: Numbers, percentages, research
- before_after: Transformation shown
- demo: Product in action
- authority: Expert endorsement, certification
- null: No proof element present

PERSUASION DEVICES (can be multiple):
- social_proof, scarcity, urgency, authority, reciprocity, liking, commitment, contrast, storytelling, fear, aspiration

FLOW ISSUES TO DETECT:
- abrupt_transition: Sudden topic change without connection
- logical_gap: Missing step in reasoning (e.g., solution before problem)
- redundant: Same point repeated without new value
- contradiction: Conflicting messages
- pacing_issue: Scene too long/short for its role

OUTPUT JSON (ExtractionResult):
{{
  "sequence_id": "string",
  "total_duration": number,
  "scene_count": number,
  "beats": [
    {{
      "scene_id": "s01",
      "full_script": "EXACT original script text",
      "visual_description": "EXACT original visual prompt",
      "narrative_role": "hook|problem|...",
      "duration": number,
      "claim_made": "string or null",
      "proof_type": "testimonial|stat|...|null",
      "persuasion_devices": ["social_proof", ...],
      "product_visible": boolean,
      "human_present": boolean,
      "text_overlay_present": boolean
    }}
  ],
  "flow": {{
    "full_narrative": "All scripts concatenated with scene markers: [s01] script1 [s02] script2 ...",
    "logical_flow": boolean,
    "flow_issues": [
      {{
        "between_scenes": ["s02", "s03"],
        "issue_type": "logical_gap",
        "description": "Solution presented before problem is established"
      }}
    ],
    "tone_consistent": boolean,
    "tone_shifts": ["s03: suddenly formal tone"],
    "core_message_clear": boolean,
    "core_message": "extracted main message or null",
    "competing_messages": ["secondary message that confuses"]
  }},
  "hook_duration": number_or_null,
  "first_product_time": number_or_null,
  "first_proof_time": number_or_null,
  "first_cta_time": number_or_null
}}"""


JUDGEMENT_PROMPT = """You are an expert video ad creative director. Review this extracted sequence analysis and provide actionable feedback.

EXTRACTION RESULT:
{extraction_json}

DETERMINISTIC CHECK RESULTS:
{deterministic_issues}

{reference_section}

TASK:
Score the sequence's persuasion effectiveness and provide specific fixes.

SCORING CRITERIA (1-10 each):
- attention: Does the hook grab attention in first 3 seconds? Pattern interrupt? Curiosity?
- branding: Is product/brand visible early and often enough?
- connection: Does it create emotional resonance? Human element? Relatable?
- direction: Is CTA clear, specific, and well-timed?
- problem_clarity: Is the pain point vivid and specific (not generic)?
- proof_strength: Is there credible evidence? Demo? Testimonials? Stats?
- pacing: Is rhythm appropriate? No dead spots? Good momentum?

VISUAL FIX APPROACH TYPES:
- replace_footage: Find different UGC/stock footage
- generate_image: Create AI image
- generate_video: Create AI video
- add_text_overlay: Add text/stats overlay
- add_motion_graphic: Add animation/graphic
- remove_scene: Delete the scene entirely
- merge_scenes: Combine with another scene

FIX SEVERITY:
- critical: Breaks persuasion, must fix
- major: Significantly weakens ad, should fix
- minor: Polish item, nice to have

FRAMEWORK OPTIONS (for alternatives):
- hook_body_cta: Simple hook -> content -> action
- aida: Attention -> Interest -> Desire -> Action
- pas: Problem -> Agitate -> Solution
- bab: Before -> After -> Bridge
- hpscpta: Hook -> Problem -> Solution -> Credibility -> Proof -> Transformation -> Action

OUTPUT JSON (SequenceReview):
{{
  "sequence_id": "string",
  "reviewed_at": "ISO timestamp",
  "persuasion_score": {{
    "overall": 1-10,
    "reasoning": "Overall assessment in 2-3 sentences",
    "attention": 1-10,
    "branding": 1-10,
    "connection": 1-10,
    "direction": 1-10,
    "problem_clarity": 1-10,
    "proof_strength": 1-10,
    "pacing": 1-10
  }},
  "visual_fixes": [
    {{
      "scene_id": "s03",
      "issue": "Claims skin improvement but shows generic product shot",
      "severity": "critical",
      "suggested_approaches": [
        {{
          "approach_type": "replace_footage",
          "description": "Use before/after UGC showing actual skin change",
          "detailed_spec": "Find UGC clip with same person, same lighting, showing skin tone improvement. Should be close-up face shot, natural daylight.",
          "confidence": "high"
        }},
        {{
          "approach_type": "generate_image",
          "description": "Generate split-screen before/after comparison",
          "detailed_spec": "Left: dull skin tone, tired look. Right: glowing, bright skin. Same Korean woman 30s, same angle, natural window light.",
          "confidence": "medium"
        }}
      ]
    }}
  ],
  "script_fixes": [
    {{
      "scene_id": "s02",
      "issue": "Generic pain point, not specific enough",
      "current_script": "example current script",
      "suggested_script": "example improved script",
      "reason": "Specific symptom is more relatable than generic concerns"
    }}
  ],
  "flow_fixes": [
    {{
      "issue": {{
        "between_scenes": ["s02", "s03"],
        "issue_type": "logical_gap",
        "description": "Solution before problem fully established"
      }},
      "suggestion": "Swap s02 and s03 order, or add a bridge scene amplifying the problem before introducing solution"
    }}
  ],
  "alternative_frameworks": [
    {{
      "framework": "pas",
      "reason": "Current sequence lacks emotional agitation. PAS would strengthen the problem to solution arc.",
      "outline": ["Hook: relatable question", "Agitate: amplify the pain", "Solution: introduce product"]
    }}
  ],
  "action_items": [
    {{
      "priority": 1,
      "category": "visual",
      "scene_id": "s03",
      "action": "Replace generic product shot with before/after UGC",
      "impact": "Adds credibility to skin improvement claim"
    }},
    {{
      "priority": 2,
      "category": "script",
      "scene_id": "s02",
      "action": "Make pain point more specific",
      "impact": "Increases relatability and hook strength"
    }}
  ],
  "deterministic_issues": ["No CTA detected", "Product appears after 10s"]
}}"""


JUDGEMENT_PROMPT_WITH_VISUAL = """You are an expert video ad creative director. Review this extracted sequence analysis and provide actionable feedback.

IMPORTANT: You are provided with a VISUAL GRID showing thumbnails of each scene. Each thumbnail is labeled with its scene ID (s01, s02, etc.). Use these actual visuals to inform your review - do not rely solely on text descriptions.

VISUAL GRID (attached image):
- 5x5 grid of scene thumbnails
- Each cell shows a frame from the middle of that scene's footage
- Gray placeholders indicate scenes without available footage
- Use these visuals to assess: lighting, framing, human presence, product visibility, visual quality, and scene-to-scene consistency

EXTRACTION RESULT:
{extraction_json}

DETERMINISTIC CHECK RESULTS:
{deterministic_issues}

{reference_section}

TASK:
Score the sequence's persuasion effectiveness based on BOTH the visual grid AND the extracted data. Provide specific fixes that reference what you actually SEE in the thumbnails.

SCORING CRITERIA (1-10 each):
- attention: Does the hook VISUALLY grab attention? Look at s01 thumbnail - is it eye-catching?
- branding: Is product/brand VISIBLE in the thumbnails? How early? How often?
- connection: Do the visuals show human elements? Relatable situations?
- direction: Can you see CTA elements in later scene thumbnails?
- problem_clarity: Do the visuals effectively communicate the problem?
- proof_strength: Are there visible proof elements (before/after, testimonials, demos)?
- pacing: Does the visual progression make sense? Scene-to-scene consistency?

VISUAL FIX APPROACH TYPES:
- replace_footage: Find different UGC/stock footage
- generate_image: Create AI image
- generate_video: Create AI video
- add_text_overlay: Add text/stats overlay
- add_motion_graphic: Add animation/graphic
- remove_scene: Delete the scene entirely
- merge_scenes: Combine with another scene

FIX SEVERITY:
- critical: Breaks persuasion, must fix
- major: Significantly weakens ad, should fix
- minor: Polish item, nice to have

When suggesting visual fixes, describe what you SEE in the current thumbnail and what would be better.

OUTPUT JSON (SequenceReview):
{{
  "sequence_id": "string",
  "reviewed_at": "ISO timestamp",
  "persuasion_score": {{
    "overall": 1-10,
    "reasoning": "Overall assessment referencing specific visual observations",
    "attention": 1-10,
    "branding": 1-10,
    "connection": 1-10,
    "direction": 1-10,
    "problem_clarity": 1-10,
    "proof_strength": 1-10,
    "pacing": 1-10
  }},
  "visual_fixes": [
    {{
      "scene_id": "s03",
      "issue": "Thumbnail shows dark, poorly lit footage that doesn't match the energetic script",
      "severity": "critical",
      "suggested_approaches": [
        {{
          "approach_type": "replace_footage",
          "description": "Replace with brighter, better-lit UGC",
          "detailed_spec": "Current frame shows dimly lit indoor scene. Need bright natural lighting, same composition but more inviting.",
          "confidence": "high"
        }}
      ]
    }}
  ],
  "script_fixes": [
    {{
      "scene_id": "s02",
      "issue": "Script and visual mismatch",
      "current_script": "example current script",
      "suggested_script": "example improved script",
      "reason": "The visual shows X but script says Y"
    }}
  ],
  "flow_fixes": [
    {{
      "issue": {{
        "between_scenes": ["s02", "s03"],
        "issue_type": "logical_gap",
        "description": "Visual jump from indoor to outdoor without transition"
      }},
      "suggestion": "Add transition or reorder scenes for visual continuity"
    }}
  ],
  "alternative_frameworks": [
    {{
      "framework": "pas",
      "reason": "Based on the visuals, a PAS structure would better utilize the available footage",
      "outline": ["Hook with s01 visual", "Agitate using s02-s03", "Solution with s04"]
    }}
  ],
  "action_items": [
    {{
      "priority": 1,
      "category": "visual",
      "scene_id": "s03",
      "action": "Replace dark footage with brighter alternative",
      "impact": "Improves visual quality and matches script energy"
    }}
  ],
  "deterministic_issues": []
}}"""


REFERENCE_BENCHMARK_SECTION = """
REFERENCE BENCHMARKS (similar successful ads):
{reference_summaries}

Compare against these references:
- Pacing: How does hook/product/CTA timing compare?
- Structure: What patterns do successful ads use that this sequence lacks?
- Do NOT copy reference content, only learn from structure/timing."""
