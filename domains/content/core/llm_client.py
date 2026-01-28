"""LLM Client for interacting with Google Gemini API."""

import json
import sys
import traceback
import google.generativeai as genai
from google.api_core import exceptions
from google.genai import types
from google import genai
import os
from dotenv import load_dotenv
from typing import Optional


def get_traceback_log() -> str:
    """Get the traceback of the last exception as a string."""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    exc_chain_str = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    return exc_chain_str


class LLMClient:
    """Client for interacting with Google Gemini models."""

    def __init__(self):
        load_dotenv()
        self.model_mapper = {
            'gemini-2.5-pro': 'GOOGLE',
            'gemini-1.5-flash': 'GOOGLE',
            'gemini-2.0-flash-exp': 'GOOGLE',
            'gemini-2.0-flash': 'GOOGLE',
            'gemini-2.0-flash-thinking-exp-01-21': 'GOOGLE',
            'gemini-2.5-flash': 'GOOGLE',
            'gemini-2.5-flash-preview-05-20': 'GOOGLE',
        }
        self.max_tokens = 4096

    async def generate_gemini_video(
        self,
        content: str,
        video_bytes: bytes,
        video_mime_type: str,
        system: Optional[str] = None,
        model: str = 'gemini-2.5-pro',
        temperature: float = 0.5,
        json_mode: bool = False
    ):
        """Generate content using Gemini with video input."""
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in environment variables")
        g_client: genai.Client = genai.Client(api_key=api_key)
        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else "text/plain",
            temperature=temperature,
        )

        prompt_parts = [types.Part.from_text(text=m['content']) for m in messages]

        response = await g_client.aio.models.generate_content(
            model=model,
            contents=types.Content(
                role='user',
                parts=[
                    types.Part(inline_data=types.Blob(data=video_bytes, mime_type=video_mime_type)),
                    *prompt_parts
                ]
            ),
            config=generate_content_config,
        )
        return response

    async def generate_gemini(
        self,
        content: str,
        system: Optional[str] = None,
        model: str = 'gemini-2.5-pro',
        temperature: float = 0.5,
        image_path: Optional[str] = None,
        json_mode: bool = False,
        search: bool = True
    ):
        """Generate content using Gemini model."""
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        print(f'🧪 generating with {model} model')
        api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY or GOOGLE_API_KEY must be set in environment variables")
        g_client: genai.Client = genai.Client(api_key=api_key)

        # Gemini API doesn't support tool use with JSON mode
        # Auto-disable search if json_mode is enabled
        if json_mode and search:
            print("⚠️  Warning: JSON mode and search tools cannot be used together. Disabling search.")
            search = False

        tool_config = None
        if search:
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            tool_config = [grounding_tool]

        generate_content_config = types.GenerateContentConfig(
            response_mime_type="application/json" if json_mode else "text/plain",
            temperature=temperature,
            tools=tool_config,
        )
        contents = [types.Content(role=m['role'], parts=[types.Part.from_text(text=m['content'])]) for m in messages]
        if image_path is not None:
            with open(image_path, 'rb') as image_file:
                image_bytes = image_file.read()
            contents.append(types.Content(role="user", parts=[types.Part.from_bytes(
                data=image_bytes,
                mime_type='image/png',
            ),]))
        try:
            response = await g_client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=generate_content_config,
            )
            return response
        except exceptions.ResourceExhausted as e:  # Rate limit
            print(f"Reached to Rate limit. trying with {model} model")
            return await self.generate_gemini(content, system, model, temperature, image_path, json_mode, search)
        except Exception as e:
            print(f'🧪 gemini error: {e}')
            raise e

    def generate_gemini_sync(
        self,
        content: str,
        system: Optional[str] = None,
        model: str = 'gemini-2.5-pro',
        temperature: float = 0.5,
        image_path: Optional[str] = None,
        json_mode: bool = False,
        search: bool = True
    ):
        """Synchronous wrapper for generate_gemini method."""
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(
            self.generate_gemini(content, system, model, temperature, image_path, json_mode, search)
        )

    @staticmethod
    def parse_and_get_result(response, key: str = "result") -> dict:
        """
        Parse JSON response and extract result by key.

        Args:
            response: LLM response object with text attribute
            key: Key to extract from parsed JSON (default: "result")

        Returns:
            Dictionary containing the extracted result
        """
        response_text = response.text if hasattr(response, 'text') else str(response)
        try:
            parsed = json.loads(response_text)
            if key and key in parsed:
                return parsed[key]
            return parsed
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
            import re
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
            if json_match:
                try:
                    parsed = json.loads(json_match.group(1))
                    if key and key in parsed:
                        return parsed[key]
                    return parsed
                except json.JSONDecodeError:
                    pass
            # If all parsing fails, return empty dict
            return {}
