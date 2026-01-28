"""Prompt templates for script creation/assembly."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..domain.schema_output import XmlPattern
    from ..domain.schema_data import ContentMaterial


def get_script_creation_prompt(
    skeleton_pattern: "XmlPattern",
    content_material: "ContentMaterial",
    topic: str,
    persona: str = "general",
    additional_text: str = None,
    target_duration_seconds: int = None
) -> str:
    """Generate prompt for creating educational draft script from skeleton and content material."""

    # Format skeleton pattern
    skeleton_info = f"""
Tag Sequence: {' -> '.join(skeleton_pattern.tag_sequence)}
Description: {skeleton_pattern.description or 'N/A'}
"""

    # Format content material
    material_info = f"""
Available Content Material:

Video Transcripts: {len(content_material.transcripts)} transcripts available
- Topics covered: {', '.join(set([t for transcript in content_material.transcripts[:5] for t in transcript.video_metadata.topics[:3]]))}

Community Gossip Items: {len(content_material.gossip_items)} items
- Top items: {', '.join([item.title[:50] for item in content_material.gossip_items[:3]])}

Fact-Based Items: {len(content_material.fact_items)} items
- Top items: {', '.join([item.title[:50] for item in content_material.fact_items[:3]])}
"""

    # Generate example based on actual skeleton pattern
    example_tags = "\n".join([f"<{tag}>[Content for {tag} section]</{tag}>" for tag in skeleton_pattern.tag_sequence])

    # Format additional context
    additional_context = ""
    if additional_text:
        additional_context = f"\nAdditional Context/Instructions: {additional_text}"

    # Format target duration constraint
    duration_constraint = ""
    if target_duration_seconds:
        duration_minutes = target_duration_seconds / 60.0
        duration_constraint = f"""
**CRITICAL DURATION CONSTRAINT:**
- Target video duration: {target_duration_seconds} seconds ({duration_minutes:.1f} minutes)
- The script MUST be written so that when read by TTS (Text-to-Speech) at approximately 175 words per minute, it will be close to {target_duration_seconds} seconds
- This means the script should contain approximately {int(target_duration_seconds * 175 / 60)} words
- Adjust the length and detail level of explanations to fit within this duration
- Be concise but maintain educational clarity and engaging analogies
- Prioritize the most important concepts and explanations
"""

    return f"""
You are an expert educational content scriptwriter specializing in creating clear, engaging, and entertaining explanatory videos for short-form educational content.

Task: Create an educational script that clearly explains the concept/topic using engaging analogies and entertaining explanatory methodologies, making learning both effective and enjoyable.

Topic/Concept: {topic}
Target Audience: {persona}{additional_context}{duration_constraint}

Skeleton Pattern (XML Structure):
{skeleton_info}

{material_info}

Educational Requirements (with emphasis on engagement):
1. **CRITICAL: Use ONLY the XML tags from the skeleton pattern. Do NOT add any additional tags (like hook, intro, call_to_action) unless they are explicitly in the skeleton pattern.**
2. Follow the XML tag sequence from the skeleton pattern exactly in the order specified
3. Start with a clear, engaging introduction that hooks the learner
4. Break down the concept into logical steps or components
5. **CRITICAL: Use creative, memorable analogies that make abstract concepts concrete:**
   - Find relatable comparisons from everyday life, pop culture, or familiar scenarios
   - Use analogies that are both accurate and entertaining
   - Make complex ideas accessible through surprising but apt comparisons
6. **Employ entertaining explanatory methodologies:**
   - Use storytelling to explain concepts
   - Create scenarios or examples that are both educational and engaging
   - Use surprising facts or counterintuitive comparisons
   - Make the explanation journey interesting, not just informative
7. Ensure accuracy and educational value while maintaining entertainment
8. Structure for optimal learning (introduce → explain with analogies → illustrate with examples → reinforce)
9. Balance clarity with engagement - make it both educational AND entertaining
10. Use language appropriate for the target educational level while keeping it lively
11. Fill each XML tag section with relevant content from the material
12. Ensure smooth transitions between sections
13. Make it engaging, concise, and optimized for short-form video{duration_constraint and f" (target: {target_duration_seconds} seconds)" or " (typically 15-60 seconds)"}
14. Incorporate elements from transcripts, gossip, and facts naturally

Key Principle: The script should make viewers think "That's interesting!" or "I never thought of it that way!" while still clearly explaining the concept. Use analogies and explanatory methods that stick in memory because they're both accurate and entertaining.

Output format:
**CRITICAL: You MUST output the script with XML tags. The output must include XML tags like <tag_name>content</tag_name>.**

Create a script with XML tags following the skeleton pattern exactly. Use ONLY these tags in this exact order:
{example_tags}

**IMPORTANT OUTPUT REQUIREMENTS:**
- The output MUST be the script with XML tags, not a description or explanation
- Each tag must be properly formatted: <tag_name>content here</tag_name>
- Do NOT output markdown code blocks or explanations - just output the tagged script directly
- Example of correct output format:
  <concept_intro>This is the introduction content.</concept_intro>
  <explanation>This is the explanation content.</explanation>
  <example>This is an example.</example>

Make sure each XML tag section is filled with compelling, relevant content that clearly explains the concept using engaging analogies and entertaining explanatory methods. The content should be both educational and enjoyable.
Do not add any tags that are not in the skeleton pattern.
"""

