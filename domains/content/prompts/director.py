"""Prompt templates for injecting directing/visual instructions."""


def get_direction_injection_prompt(polished_script: str, topic: str) -> str:
    """Generate prompt for adding comprehensive editing and visual instructions for educational videos."""
    return f"""
You are a professional video director and editor specializing in educational short-form video content with AI-generated visual assets and video editing.

Task: Add detailed editing and visual instructions to the polished educational script to guide video production, including AI-generated visuals, effects, transitions, and editing techniques.

Topic/Concept: {topic}

Polished Script:
{polished_script}

Instructions:
1. **CRITICAL: The script contains XML tags (e.g., <concept_intro>...</concept_intro>, <explanation>...</explanation>). You MUST preserve ALL XML tags exactly as they appear in the script. Do NOT remove or modify any XML tags.**
2. Analyze the script content and identify key moments that need visual representation and editing guidance
3. Add comprehensive instructions covering:

   **AI-Generated Visual Assets:**
   - What visual elements should be shown (diagrams, illustrations, examples, animations)
   - How visuals should align with script explanations
   - Visual style and composition guidance
   - Detailed prompts for AI image/video generation

   **Editing Techniques:**
   - Transitions (fade, cut, zoom, wipe, dissolve, etc.)
   - Text overlays and graphics placement
   - On-screen annotations and labels for educational clarity
   - Color grading and visual themes
   - Pacing and rhythm of visual changes

   **Effects:**
   - Visual effects (highlights, emphasis, zoom effects)
   - Animation effects (text animations, object movements)
   - Sound effects suggestions (if applicable)
   - Visual emphasis techniques (blur, focus, spotlight)

3. Focus on educational visuals and editing that support concept explanation:
   - Diagrams and infographics for complex concepts
   - Illustrations that match analogies used in the script
   - Visual examples that reinforce explanations
   - Animations for step-by-step processes
   - Smooth transitions that maintain educational flow
4. Format instructions inline with the script content
5. Be specific and actionable for both AI generation and video editing
6. **IMPORTANT: All directions must be written in Korean language**

Output format (JSON):
{{
   "script_with_directions": "[Full script with XML tags preserved and inline direction markers like [DIRECTION: ...] added]",
   "direction_instructions": [
       {{
           "instruction_type": "visual_asset",
           "instruction": "개념을 설명하는 다이어그램 이미지 생성 - [구체적인 시각적 설명 및 생성 프롬프트]"
       }},
       {{
           "instruction_type": "transition",
           "instruction": "페이드 전환 효과로 다음 개념으로 부드럽게 이동"
       }},
       {{
           "instruction_type": "text_overlay",
           "instruction": "핵심 개념을 강조하는 텍스트 오버레이 추가 - [텍스트 내용 및 위치]"
       }},
       {{
           "instruction_type": "effect",
           "instruction": "중요한 부분에 줌 인 효과로 시선 집중"
       }},
       {{
           "instruction_type": "animation",
           "instruction": "단계별 설명을 위한 애니메이션 효과 적용"
       }}
   ]
}}

Instruction types can include: visual_asset, transition, text_overlay, effect, animation, color_grading, sound_effect, etc.
The script_with_directions should include inline markers like [DIRECTION: ...] at appropriate points, and direction_instructions should provide detailed, actionable guidance for video production. **MOST IMPORTANTLY: All XML tags from the original script must be preserved exactly as they are. Do not remove, modify, or alter any XML tags.** All directions and instructions must be written in Korean.
"""

