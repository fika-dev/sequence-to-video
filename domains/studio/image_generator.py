import asyncio
from io import BytesIO
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from domains.studio.models import ImageAsset
from infrastructure.cache import AssetCache
from infrastructure.metadata import MetadataManager


class ImageGenerator:
    def __init__(
        self,
        output_dir: Path | None = None,
        project: str | None = None,
        location: str = "global",
        cache: AssetCache | None = None,
        locale: str = "ko-KR",
        context: str = "",
        metadata_manager: MetadataManager | None = None,
    ):
        self.project = project
        self.location = location
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location=location,
        )
        self.output_dir = Path(output_dir) if output_dir else Path("assets/generated/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.cache = cache
        self.locale = locale
        self.context = context
        self.metadata = metadata_manager or MetadataManager()

    def generate(
        self,
        prompt: str,
        width: int = 720,
        height: int = 1280,
        model: str = "gemini-3-pro-image-preview",
        output_filename: str | None = None,
        temperature: float = 1.0,
        timeout: float = 60.0,
    ) -> ImageAsset:
        cache_params = {"prompt": prompt, "width": width, "height": height, "model": model}

        if self.cache:
            cached_path = self.cache.get("image", cache_params)
            if cached_path:
                metadata = self.cache.get_metadata("image", cache_params)
                return ImageAsset(
                    file_path=cached_path,
                    width=metadata.get("width", width) if metadata else width,
                    height=metadata.get("height", height) if metadata else height,
                    prompt=prompt,
                )

        aspect_ratio = self._get_aspect_ratio(width, height)

        image = asyncio.run(
            self._generate_gemini_image(
                prompt=prompt,
                aspect_ratio=aspect_ratio,
                model=model,
                temperature=temperature,
                timeout=timeout,
            )
        )

        if image is None:
            raise RuntimeError(f"No image generated for prompt: {prompt}")

        if output_filename:
            output_path = self.output_dir / output_filename
        else:
            output_path = self.output_dir / f"img_{hash(prompt) & 0xFFFFFFFF:08x}.png"

        image.save(output_path, format="PNG")

        if self.cache:
            self.cache.put(
                "image",
                cache_params,
                output_path,
                metadata={"width": image.width, "height": image.height},
            )

        self.metadata.save(
            asset_type="image",
            asset_path=output_path,
            prompt=prompt,
            params={
                "width": width,
                "height": height,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "locale": self.locale,
                "context": self.context,
            },
        )

        return ImageAsset(
            file_path=output_path,
            width=image.width,
            height=image.height,
            prompt=prompt,
        )

    async def _generate_gemini_image(
        self,
        prompt: str,
        aspect_ratio: str = "9:16",
        model: str = "gemini-3-pro-image-preview",
        temperature: float = 1.0,
        timeout: float = 60.0,
    ) -> Image.Image | None:
        g_client = genai.Client(
            vertexai=True,
            project=self.project,
            location=self.location,
        )

        config = types.GenerateContentConfig(
            temperature=temperature,
            response_modalities=["IMAGE"],
        )

        locale_instruction = self._get_locale_instruction()
        context_prefix = f"Context: {self.context}. " if self.context else ""
        full_prompt = f"{locale_instruction}{context_prefix}Generate a vertical portrait image (aspect ratio {aspect_ratio}). {prompt}"

        try:
            response = await asyncio.wait_for(
                g_client.aio.models.generate_content(
                    model=model,
                    contents=[full_prompt],
                    config=config,
                ),
                timeout=timeout,
            )

            if response.candidates:
                candidate = response.candidates[0]

                if hasattr(candidate, "content") and candidate.content:
                    for part in candidate.content.parts:
                        if part.inline_data:
                            return Image.open(BytesIO(part.inline_data.data))

            raise ValueError("No image data returned from Gemini API")

        except asyncio.TimeoutError:
            print(f"Image generation timeout after {timeout}s")
            return None
        except Exception as e:
            print(f"Image generation error: {e}")
            return None

    def _get_aspect_ratio(self, width: int, height: int) -> str:
        ratio = width / height
        if ratio < 0.7:
            return "9:16"
        if ratio > 1.4:
            return "16:9"
        if 0.9 < ratio < 1.1:
            return "1:1"
        if ratio < 1:
            return "3:4"
        return "4:3"

    def _get_locale_instruction(self) -> str:
        locale_map = {
            "ko-KR": "IMPORTANT: If people appear in the image, they must be Korean. If any text appears in the image, it must be in Korean language. ",
            "ko": "IMPORTANT: If people appear in the image, they must be Korean. If any text appears in the image, it must be in Korean language. ",
            "ja-JP": "IMPORTANT: If people appear in the image, they must be Japanese. If any text appears in the image, it must be in Japanese language. ",
            "ja": "IMPORTANT: If people appear in the image, they must be Japanese. If any text appears in the image, it must be in Japanese language. ",
            "zh-CN": "IMPORTANT: If people appear in the image, they must be Chinese. If any text appears in the image, it must be in Simplified Chinese. ",
            "zh-TW": "IMPORTANT: If people appear in the image, they must be Taiwanese. If any text appears in the image, it must be in Traditional Chinese. ",
            "en-US": "IMPORTANT: If any text appears in the image, it must be in English. ",
            "en": "IMPORTANT: If any text appears in the image, it must be in English. ",
        }
        return locale_map.get(self.locale, "")
