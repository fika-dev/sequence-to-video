import json
import uuid
from datetime import datetime
from pathlib import Path

from google import genai
from google.genai import types
from google.cloud import storage

from domains.library.models import VideoClip, VideoIndex


ANALYSIS_PROMPTS = {
    "generic": """Analyze this video frame by frame.
Break down the video into distinct clips based on visual changes, scene transitions, or actions.

For each clip, provide in JSON format:
{
  "clips": [
    {
      "start_time": "MM:SS.ms",
      "end_time": "MM:SS.ms", 
      "description": "Detailed visual description for semantic search",
      "tags": ["tag1", "tag2"],
      "camera_angle": "close-up|medium|wide|etc",
      "camera_movement": "static|pan_left|pan_right|zoom_in|zoom_out|tilt|tracking|etc"
    }
  ],
  "total_duration": "MM:SS"
}

Be thorough in descriptions - include:
- People (gender, actions, emotions, clothing)
- Objects and products
- Settings and backgrounds
- Lighting and mood
- Any text visible on screen""",

    "product_ugc": """You are analyzing UGC (User Generated Content) footage for a product advertisement video.
These clips will be used to create short-form promotional videos.

{product_context}

IMPORTANT GUIDELINES:
1. Segment by MEANINGFUL SCENES, not every camera cut. Group continuous actions together.
2. Minimum clip duration should be 3-5 seconds for usability in ads.
3. Focus on what makes each segment valuable for marketing purposes.
4. Analyze how each clip relates to the PRODUCT CONTEXT above.

For each clip, provide in JSON format:
{{
  "clips": [
    {{
      "start_time": "MM:SS.ms",
      "end_time": "MM:SS.ms",
      "description": "Visual description + what's happening + why it's compelling for THIS product",
      "tags": ["searchable", "keywords", "for", "matching"],
      "camera_angle": "close-up|medium|wide|pov|overhead",
      "camera_movement": "static|pan|zoom_in|zoom_out|tracking|handheld",
      "content_type": "product_showcase|usage_demo|unboxing|before_after|testimonial|lifestyle|texture_detail|result_reveal",
      "appeal_point": "What marketing message or benefit this clip conveys, considering the product's key benefits",
      "product_focus": "What aspect of product is highlighted (e.g., 'packaging', 'texture', 'application', 'result')",
      "usage_context": "Where/when/how the product is being used (e.g., 'morning routine', 'bathroom mirror', 'first use')"
    }}
  ],
  "total_duration": "MM:SS"
}}

CONTENT TYPES explained:
- product_showcase: Product packaging, bottle, design highlights
- usage_demo: Showing how to use/apply the product
- unboxing: Opening package, first reveal
- before_after: Comparison showing results
- testimonial: Person speaking about experience
- lifestyle: Product in daily life context
- texture_detail: Close-up of product texture, consistency
- result_reveal: Showing the outcome/effect

For TAGS, include:
- Visual elements (skin, hands, face, product, packaging)
- Actions (applying, spreading, massaging, showing)
- Product-specific attributes from the context above
- Emotional tone (satisfied, excited, genuine, natural)
- Setting (bathroom, bedroom, natural light)

For APPEAL_POINT, think like a marketer for THIS specific product:
- What benefit does this moment communicate?
- How does it relate to the product's key selling points?
- What pain point does it address?
- What desire does it trigger?"""
}

CONTEXT_FILE_NAMES = ["context.txt", "product.txt", "info.txt"]

ANALYSIS_PROMPT = ANALYSIS_PROMPTS["generic"]


MIME_TYPES = {
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
    ".avi": "video/x-msvideo",
    ".mkv": "video/x-matroska",
    ".webm": "video/webm",
}


class VideoContentAnalyzer:
    def __init__(
        self,
        project: str | None = None,
        location: str = "us-central1",
        gcs_bucket: str | None = None,
        embedding_model: str = "text-embedding-005",
    ):
        self.project = project
        self.location = location
        self.client = genai.Client(
            vertexai=True,
            project=project,
            location="global",
        )
        self.model = "gemini-3-flash-preview"
        self.embedding_model = embedding_model
        
        self.gcs_bucket = gcs_bucket or f"{project}-video-analysis"
        self.storage_client = storage.Client(project=project)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        try:
            self.storage_client.get_bucket(self.gcs_bucket)
        except Exception:
            bucket = self.storage_client.create_bucket(
                self.gcs_bucket,
                location=self.location,
            )
            print(f"Created GCS bucket: {bucket.name}")

    def analyze_footage(
        self,
        video_path: str | Path,
        footage_type: str = "generic",
        product_context: str | None = None,
        verbose: bool = False,
    ) -> VideoIndex:
        video_path = Path(video_path)

        if product_context is None:
            product_context = self._load_context_file(video_path.parent)

        if verbose:
            print(f"    Uploading to GCS: {video_path.name}")
            print(f"    Footage type: {footage_type}")
            if product_context:
                print(f"    Product context: {product_context[:80]}...")

        gcs_uri, mime_type = self._upload_to_gcs(video_path)

        if verbose:
            print(f"    GCS URI: {gcs_uri}")
            print(f"    Calling Gemini {self.model}...")

        video_metadata = types.VideoMetadata(fps=1)

        prompt = self._build_prompt(footage_type, product_context)

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part(
                    file_data=types.FileData(file_uri=gcs_uri, mime_type="video/*"),
                    video_metadata=video_metadata,
                ),
                prompt,
            ],
        )

        raw_response = response.text or ""

        if verbose:
            print(f"    Response received, parsing...")

        clips_data = self._parse_response(raw_response)
        clips = self._build_clips(clips_data, video_path)

        if verbose:
            print(f"    Parsed {len(clips)} clips, duration: {clips_data.get('total_duration', 'unknown')}")

        return VideoIndex(
            source_file=video_path,
            total_duration=self._parse_duration(clips_data.get("total_duration", "0:00")),
            analyzed_at=datetime.now().isoformat(),
            clips=clips,
            raw_response=raw_response,
            footage_type=footage_type,
            product_context=product_context,
        )

    def _load_context_file(self, directory: Path) -> str | None:
        for filename in CONTEXT_FILE_NAMES:
            context_path = directory / filename
            if context_path.exists():
                return context_path.read_text(encoding="utf-8").strip()
        return None

    def _build_prompt(self, footage_type: str, product_context: str | None) -> str:
        prompt_template = ANALYSIS_PROMPTS.get(footage_type, ANALYSIS_PROMPTS["generic"])

        if footage_type == "product_ugc":
            if product_context:
                context_block = f"PRODUCT CONTEXT:\n{product_context}"
            else:
                context_block = "PRODUCT CONTEXT:\n(No specific product context provided. Analyze as general product UGC.)"
            return prompt_template.format(product_context=context_block)

        return prompt_template

    def _upload_to_gcs(self, video_path: Path) -> tuple[str, str]:
        bucket = self.storage_client.bucket(self.gcs_bucket)
        
        blob_name = f"analysis/{uuid.uuid4().hex}_{video_path.name}"
        blob = bucket.blob(blob_name)
        
        mime_type = MIME_TYPES.get(video_path.suffix.lower(), "video/mp4")
        blob.upload_from_filename(str(video_path), content_type=mime_type)
        
        gcs_uri = f"gs://{self.gcs_bucket}/{blob_name}"
        return gcs_uri, mime_type

    def _parse_response(self, response_text: str) -> dict:
        text = response_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"clips": [], "total_duration": "0:00"}

    def _build_clips(self, data: dict, source_file: Path, generate_embeddings: bool = True) -> list[VideoClip]:
        clips = []
        for i, clip_data in enumerate(data.get("clips", [])):
            clip = VideoClip(
                clip_id=f"{source_file.stem}_clip_{i:03d}",
                source_file=source_file,
                start_time=self._parse_duration(clip_data.get("start_time", "0:00")),
                end_time=self._parse_duration(clip_data.get("end_time", "0:00")),
                description=clip_data.get("description", ""),
                tags=clip_data.get("tags", []),
                camera_angle=clip_data.get("camera_angle"),
                camera_movement=clip_data.get("camera_movement"),
                content_type=clip_data.get("content_type"),
                appeal_point=clip_data.get("appeal_point"),
                product_focus=clip_data.get("product_focus"),
                usage_context=clip_data.get("usage_context"),
            )
            clips.append(clip)

        if generate_embeddings and clips:
            embeddings = self._generate_embeddings([self._clip_to_text(c) for c in clips])
            for clip, emb in zip(clips, embeddings):
                clip.embedding = emb

        return clips

    def _clip_to_text(self, clip: VideoClip) -> str:
        parts = [clip.description]
        if clip.appeal_point:
            parts.append(clip.appeal_point)
        if clip.tags:
            parts.append(" ".join(clip.tags))
        return " ".join(parts)

    def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=texts,
            )
            return [emb.values for emb in response.embeddings]
        except Exception:
            return [[] for _ in texts]

    def _parse_duration(self, time_str: str) -> float:
        parts = time_str.replace(".", ":").split(":")
        if len(parts) == 2:
            minutes, seconds = parts
            return int(minutes) * 60 + float(seconds)
        if len(parts) == 3:
            minutes, seconds, ms = parts
            return int(minutes) * 60 + int(seconds) + float(f"0.{ms}")
        return 0.0
