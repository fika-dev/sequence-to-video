"""Prompt templates for generating visual outlay mapping script to visual scenes."""


def get_visual_outlay_prompt(polished_script: str, topic: str) -> str:
    """Generate prompt for creating visual outlay that maps script sections to visual scenes."""
    return f"""
You are a professional visual content director specializing in educational short-form videos with AI-generated visual assets.

Task: Analyze the educational script and create a comprehensive visual outlay that maps each part of the script to specific visual scenes. Each scene should have subtitles (the text that will be displayed) and a well-engineered prompt for AI image/video generation.

Topic/Concept: {topic}

Polished Script:
{polished_script}

Instructions:
1. Analyze the script and break it down into logical visual segments (scenes)
2. Each scene should:
   - Have a clear scene number (sequential)
   - Describe what should be shown visually (diagrams, illustrations, examples, animations)
   - Include the exact subtitle text that will be displayed with this scene (extract from the script)
   - Provide a well-engineered, detailed prompt for AI image/video generation
   - Specify visual type (image or video)
3. Focus on educational visuals that support concept explanation:
   - Diagrams and infographics for complex concepts
   - Illustrations that match analogies used in the script
   - Visual examples that reinforce explanations
   - Animations for step-by-step processes
   - Visual representations of abstract concepts
4. Ensure scenes flow logically and support the educational narrative
5. **CRITICAL: Visual generation prompts must be well-engineered for AI image/video generation:**
   - Use clear, structured language optimized for AI understanding
   - Include specific visual elements: subject, composition, style, mood, lighting
   - Specify art style (e.g., "educational illustration style", "clean infographic", "3D render", "hand-drawn diagram")
   - Describe composition and layout (e.g., "centered composition", "split-screen layout")
   - Include color palette guidance (e.g., "vibrant educational colors", "blue and green tones")
   - Mention technical details if needed (e.g., "high detail", "4K quality", "smooth animation")
   - **DO NOT include any instructions about subtitles, text overlays, or on-screen text in the generation prompt**
   - Focus purely on the visual content that should be generated
6. **IMPORTANT: All scene descriptions and visual generation prompts must be written in Korean language**

Output format (JSON):
{{
   "scenes": [
       {{
           "scene_number": 1,
           "scene_description": "시각적 장면 설명 - 이 장면이 무엇을 보여주는지",
           "subtitles": "이 장면과 함께 표시될 자막 텍스트 (스크립트에서 추출)",
           "visual_generation_prompt": "AI 이미지/비디오 생성을 위한 잘 구조화된 프롬프트 (프롬프트 엔지니어링 스타일)",
           "visual_type": "image"
       }}
   ],
   "visual_generation_prompts": {{
       "scene_1": "장면 1을 위한 완전한 시각적 생성 프롬프트 (프롬프트 엔지니어링 스타일, 자막 지시사항 제외)",
       "scene_2": "장면 2를 위한 완전한 시각적 생성 프롬프트 (프롬프트 엔지니어링 스타일, 자막 지시사항 제외)"
   }}
}}

The scenes array should contain all visual scenes in order. The subtitles field should contain the exact text from the script that will be displayed as subtitles with this scene. The visual_generation_prompt should be a well-engineered prompt optimized for AI image/video generation, focusing only on visual content (no subtitle/text overlay instructions). All descriptions and prompts must be in Korean.
"""

