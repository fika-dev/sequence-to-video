"""Prompt templates for generating strategy-based tag instructions."""


def get_strategy_instruction_prompt(strategy: str, system_context: str = None) -> str:
    """
    Generate prompt for creating step-by-step instructions to extract tagged script based on a strategy.

    Args:
        strategy: Strategy string containing title, instructions, and example
        system_context: Optional system context/role (default: economist analyzing real estate market)

    Returns:
        Formatted prompt string
    """
    if system_context is None:
        system_context = "You are an economist who is analyzing the current real estate market, and also Youtube creator."

    return f'''{system_context}

# Context
Every short video needs a strategy to attract viewers.
The strategy is a plan on how to structure the content in a way that grabs the viewer's attention.
We need step by step instructions to extract a tagged script like the example.

# Example
## Example Strategy
### Giving a shocking prediction
- Start with a shocking prediction that can grab the viewer's attention.
- Give a unique insight relevant to the prediction.
- Conclude the prediction with a logical conclusion.
- Tagged transcript is provided below.
<shocking_prediction>중국이 지금 60조 달러예요. 미국은 30조도 안 돼요.</shocking_prediction><unique_insight>그런데 gdp는 미국이 25조고 중국은 한 19조 정도밖에 안 돼요. 그러니까 중국 부동산 시가총액이 미국 gdp보다도 2 3배 더 높아요. 그런데 실제 중국 gdp는 미국보다 많이 낮아요. 한 70%%밖에 안 돼요 80%%. 미국 전체 부동산 가격이 중국 부동산보다 3분의 1도 안 돼요. 웃기잖아요. 말이 안 맞죠. 무슨 말이에요</unique_insight><conclusion>중국의 부동산 가격이 가격이 아니라는 거죠. 제 가격이 아니라는 거죠.</conclusion>

## Expected Output to the Example Input
1. Identify a section in the transcript that can be used as a shocking prediction.
2. Find a sentence that is appropriate for <shocking_prediction/> from the video transcript without modifying.
3. Find a section that is appropriate for <unique_insight/> relevant to the <shocking_prediction/> from the video transcript without modifying.
4. Find a sentence that can be <conclusion/> from the video transcript without modifying.

# Input
## STRATEGY:
{strategy}

# Instructions
1. Analyze the given example strategy and the expected output.
2. Provide step by step instructions to extract a tagged script for the input STRATEGY.

# Rule
- Output in JSON format without any additional text.
- Ignore the content of tagged script in the example.
- Add "without modifying" to the instructions to prevent any modification to the video transcript.

# Output Example
{{
  "result": {{
    "instructions": [
      "Identify a section in the transcript that can be used as a shocking prediction.",
      "Find a sentence that is appropriate for <shocking_prediction/> from the video transcript without modifying.",
      "Find a section that is appropriate for <unique_insight/> relevant to the <shocking_prediction/> from the video transcript without modifying.",
      "Find a sentence that can be <conclusion/> from the video transcript without modifying."
    ]
  }}
}}

# Output
'''

