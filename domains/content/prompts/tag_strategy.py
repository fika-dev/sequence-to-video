"""Prompt templates for identifying and tagging strategies in transcripts."""


def get_tag_strategy_prompt(short_transcript: str, category: str, title: str) -> dict:
    """
    Generate prompt for identifying strategy and tagging transcript.

    Args:
        short_transcript: The transcript of the short video
        category: The category/domain (e.g., "real estate", "economics")
        title: The title of the short video

    Returns:
        Dictionary with role, system, and content keys matching the template format
    """
    system_context = f"You are a specialist at {category}, and also Youtube creator."

    content = f'''{system_context}

# Context
This is an educational short-form video that explains a concept clearly.
The video uses a structured approach to help viewers understand the concept through clear explanations, analogies, and examples.
Analyze the transcript and identify the educational structure used to explain the concept.

# Input
## EXAMPLE EDUCATIONAL STRUCTURES:
### Concept Introduction → Explanation → Example → Summary
- Start by introducing the concept clearly.
- Explain the concept in detail, breaking it down into understandable parts.
- Provide a concrete example or analogy to illustrate the concept.
- Summarize the key points.
- Tagged example: <concept_intro>Photosynthesis is how plants make food.</concept_intro> <explanation>Plants use sunlight, water, and carbon dioxide to create glucose, which is their food source. This process happens in the chloroplasts of plant cells.</explanation> <example>Think of it like a factory: sunlight is the power, water and CO2 are the raw materials, and glucose is the product.</example> <summary>So photosynthesis is essentially a plant's way of making its own food using light energy.</summary>

### Hook → Concept Breakdown → Real-world Application → Key Takeaway
- Start with an engaging hook that introduces the concept.
- Break down the concept into logical steps or components.
- Show how it applies in real-world situations.
- End with a key takeaway or insight.
- Tagged example: <hook>Did you know that every breath you take comes from photosynthesis?</hook> <concept_breakdown>Photosynthesis has two main stages: light reactions and dark reactions. In light reactions, plants capture sunlight. In dark reactions, they use that energy to make glucose.</concept_breakdown> <real_world_application>This is why forests are so important - they produce the oxygen we breathe through photosynthesis.</real_world_application> <key_takeaway>Without photosynthesis, life on Earth as we know it wouldn't exist.</key_takeaway>

## SHORT VIDEO TITLE:
{title}

## SHORT VIDEO TRANSCRIPT:
{short_transcript}

# Instructions
1. Analyze the educational structure of the given SHORT VIDEO transcript.
2. Identify how the concept is being explained (introduction, explanation, examples, analogies, summary, etc.).
3. Transform the relevant parts of the transcript into a tagged format that reflects the educational structure.
4. Use educational tags such as: concept_intro, hook, explanation, concept_breakdown, analogy, example, real_world_application, key_point, summary, key_takeaway, etc.
5. Create tags that represent the logical flow of how the concept is being explained.

# Rule
- Output in JSON format without any additional text.
- Focus on educational structure, not viral engagement strategies.
- Do not alter or translate the transcript text.
- Do not forget to close double quotes at the end of the tagged_script value.

# Output Example
{{
  "result": {{
    "purpose": "To hook the viewer's attention with a shocking prediction",
    "strategy_title": "Giving a shocking prediction",
    "strategy_detail": "- Start with a shocking prediction that can grab the viewer's attention.\\n ...",
    "tagged_script": "<shocking_prediction>...</shocking_prediction> <unique_insight>...</unique_insight> <conclusion>...</conclusion>"
  }}
}}

# Output
'''

    return {
        "role": "user",
        "system": system_context,
        "content": content
    }


def get_tag_strategy_prompt_content(short_transcript: str, category: str, title: str) -> str:
    """
    Generate prompt content string (without role/system wrapper) for compatibility.

    Args:
        short_transcript: The transcript of the short video
        category: The category/domain (e.g., "real estate", "economics")
        title: The title of the short video

    Returns:
        String containing the prompt content
    """
    prompt_dict = get_tag_strategy_prompt(short_transcript, category, title)
    return prompt_dict["content"]

