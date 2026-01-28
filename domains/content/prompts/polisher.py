"""Prompt templates for script polishing."""


def get_script_polish_prompt(draft_script: str, topic: str) -> str:
    """Generate prompt for polishing educational script to be clear, engaging, and natural."""
    return f"""
You are an expert educational script editor specializing in making educational scripts sound natural, clear, engaging, and effective for short-form educational videos.

Task: Polish the draft educational script to make it sound more human-like, natural, and engaging while maintaining educational clarity, accuracy, and the engaging analogies/explanatory methods.

Topic/Concept: {topic}

Draft Script:
{draft_script}

Instructions:
1. Improve flow and readability to sound natural when spoken
2. Add conversational elements, natural transitions, and engaging phrases
3. Remove any awkward phrasing or overly formal language
4. **Preserve and enhance the analogies and entertaining explanatory methodologies from the draft**
5. Ensure explanations remain clear, accurate, and educational while being entertaining
6. Enhance the engaging aspects without losing educational accuracy
7. Ensure it sounds like a real educator talking (not AI-generated)
8. Keep the XML tag structure intact
9. Maintain all key information, educational structure, and analogies
10. Optimize for spoken delivery (consider pauses, emphasis, natural speech patterns)
11. Make sure analogies are clear and memorable
12. Ensure the educational value is maintained while improving engagement

Output format:
**CRITICAL: You MUST output the script with XML tags preserved. The output must include XML tags like <tag_name>content</tag_name>.**

Provide the polished script with the same XML tag structure as the draft script.

**IMPORTANT OUTPUT REQUIREMENTS:**
- The output MUST be the script with XML tags, not a description or explanation
- Each tag must be properly formatted: <tag_name>polished content here</tag_name>
- Do NOT output markdown code blocks or explanations - just output the tagged script directly
- Preserve ALL XML tags from the draft script exactly
- Only improve the content within each tag, but keep the tag structure intact

The output should be the complete polished script that sounds natural, human, highly engaging, and clearly educational while preserving all XML tags, content structure, analogies, and explanatory methods exactly as they appear in the draft.
"""

